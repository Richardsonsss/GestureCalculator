"""Gesture Calculator - a scientific calculator operated with hand gestures in front of a webcam.

The left hand shows the digits; the right hand, on the whiteboard, shows two digits that select an operator.

    python app/main.py                 start with the default webcam
    python app/main.py --camera 1      use another webcam
    python app/main.py --no-camera     keyboard only

Runs entirely on this computer; it never connects to the internet.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import MainWindow  # noqa: E402  (first: it loads MediaPipe before PySide6)

from PySide6.QtWidgets import QApplication  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", type=int, default=0, help="webcam index")
    ap.add_argument("--no-camera", action="store_true")
    ap.add_argument("--gesture-model", choices=["resnet152", "vit_b16"],
                    help="static-gesture network (default: the best one found in models/)")
    args = ap.parse_args()
    app = QApplication(sys.argv[:1])
    window = MainWindow(camera_index=args.camera, use_camera=not args.no_camera, gesture_model=args.gesture_model)
    window.resize(1100, 960)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
