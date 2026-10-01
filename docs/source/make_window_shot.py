"""The annotated picture of the program window for the manual.

    python docs/source/make_window_shot.py     ->  docs/images/window.png

It opens the real window without a camera, puts a drawn camera picture into it (the program's own overlay over
a plain background, with two example hands), grabs the window and adds numbered markers.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "app"))

import numpy as np  # noqa: E402
import vision  # noqa: E402  (before PySide6, see ui.py)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ui import MainWindow  # noqa: E402

W, H = 1280, 720
OUT = os.path.join(ROOT, "docs", "images", "window.png")


def example_hand(x, y, pose):
    """21 landmarks of a raised hand; pose = (thumb, index, middle, ring, little), 1 = extended."""
    lm = np.zeros((21, 2), np.float32)
    lm[0] = (x, y + 110)
    for f, mcp in enumerate((5, 9, 13, 17)):
        fx = x - 36 + 24 * f
        up = pose[f + 1]
        lm[mcp] = (fx, y)
        lm[mcp + 1] = (fx, y - 44)
        lm[mcp + 2] = (fx, y - 70 if up else y - 28)
        lm[mcp + 3] = (fx, y - 94 if up else y - 10)
    lm[1], lm[2], lm[3] = (x - 52, y + 66), (x - 66, y + 34), (x - 76, y + 10)
    lm[4] = (x - 86, y - 18) if pose[0] else (x - 26, y + 16)
    return lm


def camera_picture():
    """What the camera view shows: left hand holding a gesture, right hand on the whiteboard after the tens digit."""
    cam = vision.CameraThread(0)
    x0, y0, x1, y1 = vision.board_rect(W, H)
    left = (example_hand(330, 430, (1, 1, 1, 1, 1)), None)
    right = (example_hand((x0 + x1) // 2 + 70, y1 - 150, (0, 0, 0, 0, 0)), None)
    cam.left.status.mode, cam.left.status.progress, cam.left.status.guess = "hold", 0.7, "5"
    cam.right.status.mode, cam.right.status.progress, cam.right.status.guess = "hold", 0.5, "0"
    cam.code.tens = "1"
    view = np.zeros((H, W, 3), np.uint8)
    view[:] = (92, 84, 78)
    for row in range(H):  # a soft gradient instead of a flat background
        view[row] = np.clip(view[row].astype(np.int16) + int(26 * row / H) - 13, 0, 255)
    cam.draw(view, left, right, 1.0)
    return view[:, :, ::-1].copy()  # RGB


def annotate(path):
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", int(h * 0.024))
    marks = [("1", 0.50, 0.075), ("2", 0.22, 0.44), ("3", 0.79, 0.20), ("4", 0.305, 0.761), ("5", 0.472, 0.761),
             ("6", 0.80, 0.712), ("7", 0.175, 0.794), ("8", 0.718, 0.794)]
    r = int(h * 0.021)
    for label, fx, fy in marks:
        x, y = int(w * fx), int(h * fy)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(220, 38, 38), outline="white", width=3)
        d.text((x, y), label, font=font, fill="white", anchor="mm")
    im.save(path)


def main():
    app = QApplication([])
    window = MainWindow(use_camera=False)
    window.resize(1100, 960)
    window.show()
    for key in "sin 3 0 rp add".split():
        window.press(key)
    rgb = camera_picture()
    image = QImage(rgb.data, W, H, rgb.strides[0], QImage.Format.Format_RGB888).copy()
    for widget in (window.toggle, window.swap):
        widget.setEnabled(True)
    window.hint.setText("Left hand: hold still...      Right hand: hold still...")
    window.last.setText("Entered + by code 01")

    def shoot():
        window.show_frame(image)
        app.processEvents()
        window.grab().save(OUT)
        annotate(OUT)
        print("wrote", OUT)
        app.quit()

    QTimer.singleShot(400, shoot)
    app.exec()


if __name__ == "__main__":
    main()
