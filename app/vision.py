"""Camera thread: webcam -> hand landmarks -> gestures of both hands -> key events for the window.

    left hand                   digit, '.', '=', DEL, AC
    right hand on the board     two digits (tens, then units) = the code of an operator

Everything runs on this computer: OpenCV reads the webcam, MediaPipe tracks both hands, and one ONNX model
classifies the gesture of each hand. No frame leaves the process.
"""
import os
import queue
import sys
import threading
import time
import types

import cv2

# MediaPipe imports matplotlib only for a 3-D plotting helper that this program never calls. Loading the real
# matplotlib clashes with PySide6's import hook (inside the packaged exe as well), so an empty stand-in is
# registered first; matplotlib is then not needed at all and is left out of the exe.
if "matplotlib" not in sys.modules:
    _stub = types.ModuleType("matplotlib")
    _stub.pyplot = types.ModuleType("matplotlib.pyplot")
    sys.modules["matplotlib"], sys.modules["matplotlib.pyplot"] = _stub, _stub.pyplot

import mediapipe as mp  # noqa: E402
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from controller import GestureInput, Settings, hand_size, right_hand_settings
from gestures import key_label
from operators import CodeEntry
from paths import resource

BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]
PALM = [0, 5, 9, 13, 17]
TEAL, AMBER, WHITE, RED, GREY = (166, 184, 20), (11, 158, 245), (255, 255, 255), (68, 68, 239), (160, 150, 140)  # BGR
# The whiteboard: top right of the mirrored picture, where the right hand is. Fractions of width and height.
BOARD = (0.60, 0.04, 0.98, 0.56)
DIGITS = {str(d) for d in range(10)}
LEFT_HINTS = {"idle": "show a gesture", "moving": "hold still", "hold": "hold still...",
              "wait": "entered - change the gesture for the next one"}
RIGHT_HINTS = {"idle": "two digits on the whiteboard = one operator", "moving": "hold still",
               "hold": "hold still...", "wait": "entered - show the next digit"}
ASCII = {"−": "-", "×": "x", "÷": "/", "√": "sqrt", "π": "pi", "∛": "cbrt", "sin⁻¹": "asin", "cos⁻¹": "acos",
         "tan⁻¹": "atan", "10ˣ": "10^x", "eˣ": "e^x", "x²": "x^2", "x³": "x^3", "x⁻¹": "1/x", "×10ˣ": "x10^x",
         "S⇔D": "S<>D"}


def board_rect(width, height):
    """The whiteboard in pixels: (x0, y0, x1, y1)."""
    return (int(BOARD[0] * width), int(BOARD[1] * height), int(BOARD[2] * width), int(BOARD[3] * height))


class GestureWorker(threading.Thread):
    """Runs the gesture network on the newest frame only; older frames are dropped so it never falls behind."""

    def __init__(self, model):
        super().__init__(daemon=True)
        self.model = model
        self.inbox = queue.Queue(maxsize=1)
        self.results = queue.Queue()
        self.busy = False

    def submit(self, t, frame):
        if self.busy or self.inbox.full():
            return
        self.inbox.put((t, frame))

    def run(self):
        while True:
            item = self.inbox.get()
            if item is None:
                return
            self.busy = True
            t, frame = item
            try:
                self.results.put((t, self.model.predict(frame)))
            finally:
                self.busy = False

    def stop(self):
        try:
            self.inbox.put_nowait(None)
        except queue.Full:
            pass


class CameraThread(QThread):
    frame_ready = Signal(QImage)
    key_entered = Signal(str, str, float)     # key id, how ("gesture" or "code 10"), confidence
    not_recognised = Signal(str, str, float)  # what ("gesture" | "code"), closest guess, its confidence
    message = Signal(str)                     # status line under the camera view
    warning = Signal(str)                     # something is missing, but the calculator still works
    failed = Signal(str)                      # the camera or a model could not be opened

    def __init__(self, camera_index=0, settings=None, parent=None, gesture_model=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.gesture_model = gesture_model    # "resnet152" | "vit_b16" | None = the best one installed
        self.settings = settings or Settings()
        self.left = GestureInput(self.settings)                                    # digits, '.', '=', DEL, AC
        self.right = GestureInput(right_hand_settings(self.settings), allowed=DIGITS)  # code digits, faster
        self.code = CodeEntry()
        self.running = True
        self.enabled = True       # gesture input on / off (the picture keeps running)
        self.swap_hands = False   # left-handed: digits with the right hand, operator codes with the left
        self.flash = ("", 0.0)    # what the left hand just entered
        self.shown = None         # the code just completed on the board: (tens, units, label or None, time)

    def set_pause(self, seconds):
        """The left hand's pause; the right hand always answers in half that time."""
        self.settings.dwell = seconds
        self.right.s.dwell = seconds / 2

    def stop(self):
        self.running = False
        self.wait(3000)

    # ------------------------------------------------------------ setup
    def load_models(self):
        """Returns (hand tracker, (left worker, right worker) or None, list of problems)."""
        from models import GestureNet, available_gesture_models

        problems = []
        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=resource("models", "hand_landmarker.task")),
            running_mode=mp_vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=0.5, min_tracking_confidence=0.5)
        tracker = mp_vision.HandLandmarker.create_from_options(options)
        workers = None
        installed = available_gesture_models()
        arch = self.gesture_model if self.gesture_model in installed else (installed[0] if installed else None)
        if arch is not None:
            model = GestureNet(arch)  # one network, shared: each hand has its own queue
            workers = (GestureWorker(model), GestureWorker(model))
            for worker in workers:
                worker.start()
        else:
            problems.append("gesture model missing (models/gesture_resnet152.onnx): gestures are off")
        return tracker, workers, problems

    # ------------------------------------------------------------ main loop
    def run(self):
        try:
            tracker, workers, problems = self.load_models()
        except Exception as exc:  # a broken model file must not take the calculator down
            self.failed.emit(f"Could not load the models: {exc}")
            return
        capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not capture.isOpened():
            self.failed.emit("No webcam found. The keyboard still works.")
            return
        if problems:
            self.warning.emit("\n".join(problems))
        start = time.perf_counter()
        last_hint = ""
        misses = 0
        try:
            while self.running:
                ok, frame = capture.read()
                if not ok:
                    misses += 1
                    if misses > 60:
                        self.failed.emit("The webcam stopped sending pictures.")
                        return
                    time.sleep(0.02)
                    continue
                misses = 0
                t = time.perf_counter() - start
                view = cv2.flip(frame, 1)  # mirror: the right hand is on the right
                left, right = self.track(tracker, view, t)
                if self.enabled and workers is not None:
                    self.step(t, frame, view, left, right, workers)
                else:
                    self.left.reset()
                    self.right.reset()
                    self.code.cancel()
                self.draw(view, left, right, t)
                hint = (f"Left hand: {LEFT_HINTS[self.left.status.mode]}      "
                        f"Right hand: {RIGHT_HINTS[self.right.status.mode]}") if self.enabled else "Input is paused"
                if hint != last_hint:
                    self.message.emit(hint)
                    last_hint = hint
                rgb = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
                image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
                self.frame_ready.emit(image.copy())
        finally:
            capture.release()
            tracker.close()
            for worker in workers or ():
                worker.stop()

    def track(self, tracker, view, t):
        """(left hand, right hand); each is (landmarks [21, 2] in pixels, 3-D world landmarks or None) or None.

        MediaPipe names the hands for a mirrored picture, which is what it is given here.
        """
        rgb = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
        result = tracker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(t * 1000))
        h, w = view.shape[:2]
        rect = board_rect(w, h)
        left = right = None
        for i, hand in enumerate(result.hand_landmarks or []):
            lm = np.array([(p.x * w, p.y * h) for p in hand], np.float32)
            world = None
            if result.hand_world_landmarks and len(result.hand_world_landmarks) > i:
                world = np.array([(p.x, p.y, p.z) for p in result.hand_world_landmarks[i]], np.float32)
            name = result.handedness[i][0].category_name if result.handedness else "Left"
            is_left = (name == "Left") != self.swap_hands
            area = float(np.ptp(lm[:, 0]) * np.ptp(lm[:, 1]))
            if is_left:
                if left is None or area > left[2]:
                    left = (lm, world, area)
            else:
                score = area + (1e9 if self.on_board(lm, rect) else 0)  # of two "right" hands: the one on the board
                if right is None or score > right[2]:
                    right = (lm, world, score)
        return (left[:2] if left else None), (right[:2] if right else None)

    @staticmethod
    def on_board(landmarks, rect, margin=0):
        """Is the palm of this hand on the whiteboard?"""
        x, y = landmarks[PALM].mean(axis=0)
        x0, y0, x1, y1 = rect
        return x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin

    def step(self, t, frame, view, left, right, workers):
        h, w = view.shape[:2]
        rect = board_rect(w, h)
        if right is not None and not self.on_board(right[0], rect):
            away = right  # a right hand outside the board enters nothing
            right = None
        else:
            away = None
        left_worker, right_worker = workers
        for hand_input, worker in ((self.left, left_worker), (self.right, right_worker)):
            while not worker.results.empty():
                rt, probs = worker.results.get()
                hand_input.add_gesture_probs(rt, probs, worker.model.labels)

        # left hand: digits, '.', '=', DEL, AC
        for event in self.left.update(t, left[0] if left else None, left[1] if left else None):
            if event["type"] == "key":
                self.flash = (key_label(event["key"]), t)
                self.key_entered.emit(event["key"], "gesture", event["confidence"])
            elif not event.get("weak"):  # a resting hand is not reported
                self.flash = ("?", t)
                self.not_recognised.emit("gesture", key_label(event["guess"]), event["confidence"])
        if left is not None and self.left.wants_gesture:
            # the network looks at the whole picture: paint over the hand that is busy on the whiteboard
            left_worker.submit(t, self.hide_hand(frame, right[0] if right else None))

        # right hand on the whiteboard: two digits make the code of an operator
        self.code.tick(t)  # drops a tens digit that was left alone too long
        for event in self.right.update(t, right[0] if right else None, right[1] if right else None):
            if event["type"] != "key":
                if not event.get("weak"):
                    self.not_recognised.emit("gesture", key_label(event["guess"]), event["confidence"])
                continue
            tens = self.code.tens
            done = self.code.feed(event["key"], t)
            if done is None:
                self.shown = None  # a new code starts: the left half shows its tens digit
                continue
            code, key, label = done
            self.shown = (tens, event["key"], label, t)
            if key is None:
                self.not_recognised.emit("code", code, event["confidence"])
            else:
                self.key_entered.emit(key, f"code {code}", event["confidence"])
        if right is not None and self.right.wants_gesture:
            other = left or away
            right_worker.submit(t, self.hide_hand(frame, other[0] if other else None))

    @staticmethod
    def hide_hand(frame, landmarks):
        """The camera frame with one hand painted over, so the gesture network sees the other hand only.

        landmarks are in the mirrored picture; the frame is not mirrored.
        """
        if landmarks is None:
            return frame
        h, w = frame.shape[:2]
        xs, ys = w - landmarks[:, 0], landmarks[:, 1]
        pad = 0.3 * max(float(np.ptp(xs)), float(np.ptp(ys)))
        a, b = max(int(xs.min() - pad), 0), min(int(xs.max() + pad), w)
        c, d = max(int(ys.min() - pad), 0), min(int(ys.max() + pad), h)
        masked = frame.copy()
        masked[c:d, a:b] = 144  # the grey the network was trained with as padding
        return masked

    # ------------------------------------------------------------ overlay
    @staticmethod
    def big_text(view, text, center, scale, color):
        text = ASCII.get(text, text)
        thickness = max(int(scale * 2.5), 2)
        size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0]
        origin = (int(center[0] - size[0] / 2), int(center[1] + size[1] / 2))
        cv2.putText(view, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 6, cv2.LINE_AA)
        cv2.putText(view, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def draw(self, view, left, right, t):
        h, w = view.shape[:2]
        x0, y0, x1, y1 = board_rect(w, h)
        middle = (x0 + x1) // 2
        # the whiteboard: a translucent white panel in two halves, tens digit on the left, units on the right
        panel = view[y0:y1, x0:x1]
        cv2.addWeighted(panel, 0.4, np.full_like(panel, 255), 0.6, 0, panel)
        cv2.rectangle(view, (x0, y0), (x1, y1), GREY, 3)
        cv2.line(view, (middle, y0), (middle, y1), GREY, 2)

        for hand, color in ((left, TEAL), (right, AMBER)):
            if hand is None:
                continue
            pts = hand[0].astype(int)
            for a, b in BONES:
                cv2.line(view, tuple(pts[a]), tuple(pts[b]), color, 2, cv2.LINE_AA)
            for p in pts:
                cv2.circle(view, tuple(p), 3, WHITE, -1, cv2.LINE_AA)

        if self.enabled:
            for hand, hand_input, color in ((left, self.left, TEAL), (right, self.right, AMBER)):
                status = hand_input.status
                if hand is None or status.mode != "hold" or status.progress <= 0.05:
                    continue
                if hand_input is self.right and not self.on_board(hand[0], (x0, y0, x1, y1)):
                    continue
                center = tuple(hand[0][PALM].mean(axis=0).astype(int))
                radius = int(max(hand_size(hand[0]) * 0.9, 30))
                cv2.ellipse(view, center, (radius, radius), -90, 0, 360 * status.progress, color, 6, cv2.LINE_AA)
                if status.guess:
                    self.big_text(view, key_label(status.guess), (center[0], center[1] - radius - 30), 1.4, color)

            # the digits of the code, one in each half of the board
            tens = units = label = None
            if self.shown is not None and t - self.shown[3] < 1.5:
                tens, units, label, _ = self.shown
            elif self.code.tens is not None:
                tens = self.code.tens
            row = y0 + int((y1 - y0) * 0.42)
            if tens is not None:
                self.big_text(view, tens, ((x0 + middle) // 2, row), 4.0, AMBER)
            if units is not None:
                self.big_text(view, units, ((middle + x1) // 2, row), 4.0, AMBER)
                if label is None:
                    self.big_text(view, "no such code", (middle, y1 - 40), 1.2, RED)
                else:
                    self.big_text(view, label, (middle, y1 - 40), 1.6, WHITE)

        text, since = self.flash
        if text and t - since < 1.5:  # what the left hand just entered, large, for a moment
            self.big_text(view, text, (int(w * 0.3), 90), 3.2, RED if text == "?" else WHITE)
