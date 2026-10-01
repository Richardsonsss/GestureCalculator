import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from controller import GestureInput, Settings, finger_states, right_hand_settings  # noqa: E402
from operators import CodeEntry  # noqa: E402

FPS = 15  # what the laptop webcam actually delivers indoors
LABELS = ["fist", "one", "palm", "like", "no_gesture"]
POSES = {"fist": (0, 0, 0, 0, 0), "one": (0, 1, 0, 0, 0), "palm": (1, 1, 1, 1, 1), "like": (1, 0, 0, 0, 0),
         "peace_flicker": (1, 1, 1, 0, 0)}
HAND = 100.0  # size of the fake hand in pixels


def hand(x, y, pose):
    """21 fake landmarks: wrist 100 px below the knuckles, fingers up when extended."""
    lm = np.zeros((21, 2), np.float32)
    lm[0] = (x, y + 100)
    for f, mcp in enumerate((5, 9, 13, 17)):
        fx = x - 30 + 20 * f
        up = pose[f + 1]
        lm[mcp] = (fx, y)
        lm[mcp + 1] = (fx, y - 40)
        lm[mcp + 2] = (fx, y - 60 if up else y - 25)
        lm[mcp + 3] = (fx, y - 80 if up else y - 10)
    lm[1], lm[2], lm[3] = (x - 45, y + 60), (x - 55, y + 30), (x - 62, y + 10)
    lm[4] = (x - 70, y - 15) if pose[0] else (x - 20, y + 15)
    return lm


# ------------------------------------------------------------------ one hand: gestures
class Left:
    def __init__(self):
        self.c = GestureInput()
        self.t = 0.0
        self.events = []

    def frame(self, x, y, pose_name, probs=None):
        lm = None if pose_name is None else hand(x, y, POSES[pose_name])
        self.events += self.c.update(self.t, lm)
        if pose_name is not None and self.c.wants_gesture:
            shown = "one" if pose_name == "peace_flicker" else pose_name
            self.c.add_gesture_probs(self.t, probs or [0.9 if label == shown else 0.025 for label in LABELS], LABELS)
        self.t += 1 / FPS

    def hold(self, x, y, pose_name, seconds, probs=None):
        for _ in range(int(seconds * FPS)):
            self.frame(x, y, pose_name, probs)

    def move(self, x0, y0, x1, y1, pose_name, seconds):
        n = int(seconds * FPS)
        for i in range(n):
            a = (i + 1) / n
            self.frame(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, pose_name)

    def keys(self):
        return [e["key"] for e in self.events if e["type"] == "key"]


def test_fake_hand_poses():
    assert finger_states(hand(0, 0, POSES["palm"])) == (True, True, True, True, True)
    assert finger_states(hand(0, 0, POSES["fist"])) == (False, False, False, False, False)
    assert finger_states(hand(0, 0, POSES["one"])) == (False, True, False, False, False)


def test_gesture_needs_the_full_pause():
    r = Left()
    r.hold(300, 300, "palm", 0.8)
    assert r.keys() == []
    r.hold(300, 300, "palm", 0.4)
    assert r.keys() == ["5"]
    assert r.events[-1]["source"] == "gesture"


def test_held_gesture_is_entered_once():
    r = Left()
    r.hold(300, 300, "palm", 4.0)
    assert r.keys() == ["5"]


def test_changing_the_hand_shape_enters_the_next_character():
    r = Left()
    r.hold(300, 300, "palm", 1.2)
    r.hold(300, 300, "fist", 1.3)
    r.hold(300, 300, "like", 1.3)          # only the thumb changes
    assert r.keys() == ["5", "0", "eq"]


def test_same_digit_twice_after_moving_away():
    r = Left()
    r.hold(300, 300, "palm", 1.2)
    r.move(300, 300, 380, 300, "palm", 0.3)
    r.hold(380, 300, "palm", 1.2)
    assert r.keys() == ["5", "5"]


def test_same_digit_twice_after_hiding_the_hand():
    r = Left()
    r.hold(300, 300, "fist", 1.2)
    r.hold(0, 0, None, 0.6)
    r.hold(300, 300, "fist", 1.2)
    assert r.keys() == ["0", "0"]


def test_moving_the_hand_enters_nothing_until_it_rests():
    r = Left()
    r.hold(300, 300, "one", 0.4)
    r.move(300, 300, 620, 300, "one", 0.8)   # a long move with the index finger out
    assert r.keys() == []
    r.hold(620, 300, "one", 1.3)
    assert r.keys() == ["1"]


def test_hand_tremor_does_not_restart_the_timer():
    r = Left()
    rng = np.random.default_rng(0)
    for _ in range(int(1.2 * FPS)):          # +-6 px on a 100 px hand, every frame
        dx, dy = rng.uniform(-6, 6, 2)
        r.frame(300 + dx, 300 + dy, "palm")
    assert r.keys() == ["5"]


def test_drifting_after_an_entry_does_not_enter_it_again():
    r = Left()
    r.hold(300, 300, "palm", 1.2)
    r.move(300, 300, 330, 300, "palm", 0.5)  # 0.3 hand sizes: more than tremor, less than moving away
    r.hold(330, 300, "palm", 1.5)
    assert r.keys() == ["5"]


def test_flickering_finger_states_do_not_enter_the_character_again():
    r = Left()
    r.hold(300, 300, "one", 1.3)
    assert r.keys() == ["1"]
    for i in range(int(4 * FPS)):            # the hand stays; thumb and middle finger flicker
        r.frame(300, 300, "one" if i % 5 else "peace_flicker")
    assert r.keys() == ["1"]


def test_unsure_and_resting_hands_enter_nothing():
    r = Left()
    r.hold(300, 300, "palm", 1.4, probs=[0.2, 0.2, 0.2, 0.2, 0.2])
    assert r.keys() == [] and r.events[-1]["type"] == "unknown" and r.events[-1]["weak"] is False
    assert len(r.events[-1]["detail"]["top"]) == 3
    r = Left()
    r.hold(300, 300, "palm", 1.4, probs=[0.05, 0.05, 0.05, 0.05, 0.8])   # mostly "no_gesture"
    assert r.keys() == [] and r.events[-1]["weak"] is True


def test_gesture_progress_is_reported():
    r = Left()
    r.hold(300, 300, "palm", 0.5)
    assert r.c.status.mode == "hold" and 0.3 < r.c.status.progress < 0.7


# ------------------------------------------------------------------ right hand: digits only, faster
def test_right_hand_enters_digits_only_and_in_half_the_time():
    r = Left()
    r.c = GestureInput(right_hand_settings(Settings()), allowed={str(d) for d in range(10)})
    r.hold(900, 200, "palm", 0.4)
    assert r.keys() == []
    r.hold(900, 200, "palm", 0.3)
    assert r.keys() == ["5"]                 # after about half a second
    r.hold(900, 200, "fist", 0.8)            # the next digit: a new hand shape
    assert r.keys() == ["5", "0"]
    r.hold(900, 200, "like", 1.5)            # thumb up is "=" for the left hand, nothing for the right
    assert r.keys() == ["5", "0"]
    assert r.events[-1]["type"] == "unknown" and r.events[-1]["weak"] is True


def test_two_digits_from_the_right_hand_make_a_code():
    r = Left()
    r.c = GestureInput(right_hand_settings(Settings()), allowed={str(d) for d in range(10)})
    entry = CodeEntry()
    r.hold(900, 200, "one", 0.7)
    r.hold(900, 200, "fist", 0.8)
    results = [entry.feed(e["key"], e["detail"]["hold"]) for e in r.events if e["type"] == "key"]
    assert results == [None, ("10", "sin", "sin")]


def test_a_shape_shown_in_passing_is_not_mixed_into_the_next_one():
    r = Left()
    r.c = GestureInput(right_hand_settings(Settings()), allowed={str(d) for d in range(10)})
    r.hold(900, 200, "one", 0.8)
    r.hold(900, 200, "palm", 0.4)            # passing through an open hand, too short to count
    r.hold(900, 200, "one", 0.8)
    assert r.keys() == ["1", "1"]
