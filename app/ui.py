"""The calculator window: display on top, camera view in the middle, gestures and operator codes below."""
# vision (MediaPipe) must be imported before PySide6: PySide6's import hook breaks a MediaPipe dependency
from vision import CameraThread  # isort: skip

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
                               QSizePolicy, QVBoxLayout, QWidget)

from engine import Calculator
from gestures import GUIDE, key_label
from operators import CODES, GROUPS

# the physical keyboard still works (there is no on-screen keypad)
KEYBOARD = {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
            ".": "dot", "+": "add", "-": "sub", "*": "mul", "/": "div", "(": "lp", ")": "rp", "^": "pow",
            "!": "fact", "%": "percent", "=": "eq", "Return": "eq", "Enter": "eq", "Backspace": "del",
            "Escape": "ac", "D": "drg", "F": "sd"}

STYLE = """
QMainWindow, QWidget { background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI'; }
#camera { background: #020617; border-radius: 12px; color: #64748b; }
#hint { color: #cbd5e1; font-size: 14px; }
#warning { color: #fbbf24; font-size: 12px; }
#last { color: #5eead4; font-size: 14px; }
#display { background: #d9e4d2; border-radius: 10px; }
#indicators { color: #334155; font-size: 11px; font-weight: 600; background: transparent; }
#expression { color: #0f172a; font-size: 20px; background: transparent; font-family: 'Consolas'; }
#result { color: #0f172a; font-size: 34px; font-weight: 600; background: transparent; font-family: 'Consolas'; }
#guideTitle { color: #94a3b8; font-size: 11px; font-weight: 700; }
#guide { color: #cbd5e1; font-size: 12px; }
QCheckBox { color: #cbd5e1; font-size: 13px; }
QDoubleSpinBox { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px;
                 padding: 2px 6px; font-size: 13px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, camera_index=0, use_camera=True, gesture_model=None):
        super().__init__()
        self.setWindowTitle("Gesture Calculator")
        self.setStyleSheet(STYLE)
        self.calc = Calculator()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self.build_display())
        self.build_camera(layout)
        layout.addLayout(self.build_guide())

        for text, key in KEYBOARD.items():
            QShortcut(QKeySequence(text), self, activated=lambda k=key: self.press(k))

        self.refresh()
        self.camera = None
        if use_camera:
            self.camera = CameraThread(camera_index, parent=self, gesture_model=gesture_model)
            self.camera.frame_ready.connect(self.show_frame)
            self.camera.key_entered.connect(self.gesture_key)
            self.camera.not_recognised.connect(self.gesture_unknown)
            self.camera.message.connect(self.hint.setText)
            self.camera.warning.connect(self.show_warning)
            self.camera.failed.connect(self.camera_failed)
            self.camera.start()
        else:
            self.camera_failed("Camera is off. The keyboard works.")

    # ------------------------------------------------------------ layout
    def build_display(self):
        display = QFrame()
        display.setObjectName("display")
        inner = QVBoxLayout(display)
        inner.setContentsMargins(14, 8, 14, 10)
        inner.setSpacing(2)
        self.indicators = QLabel("")
        self.indicators.setObjectName("indicators")
        self.expression = QLabel("")
        self.expression.setObjectName("expression")
        self.expression.setMinimumHeight(30)
        self.result = QLabel("")
        self.result.setObjectName("result")
        self.result.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.result.setMinimumHeight(48)
        for label in (self.indicators, self.expression, self.result):
            inner.addWidget(label)
        return display

    def build_camera(self, layout):
        self.view = QLabel("Starting the camera and loading the models...")
        self.view.setObjectName("camera")
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setMinimumSize(560, 315)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.view, 1)

        line = QHBoxLayout()
        self.hint = QLabel("")
        self.hint.setObjectName("hint")
        self.last = QLabel("")
        self.last.setObjectName("last")
        self.swap = QCheckBox("Swap hands")
        self.swap.setToolTip("Left-handed: digits with the right hand, operator codes with the left hand")
        self.swap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.swap.toggled.connect(self.set_swap)
        self.toggle = QCheckBox("Gesture input")
        self.toggle.setChecked(True)
        self.toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle.toggled.connect(self.set_gestures_enabled)
        self.pause = QDoubleSpinBox()
        self.pause.setRange(0.4, 2.0)
        self.pause.setSingleStep(0.1)
        self.pause.setDecimals(1)
        self.pause.setValue(1.0)
        self.pause.setSuffix(" s")
        self.pause.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pause.valueChanged.connect(self.set_dwell)
        pause_label = QLabel("Pause")
        pause_label.setObjectName("hint")
        line.addWidget(self.hint, 1)
        line.addWidget(self.last)
        line.addWidget(pause_label)
        line.addWidget(self.pause)
        line.addWidget(self.swap)
        line.addWidget(self.toggle)
        layout.addLayout(line)
        self.warning = QLabel("")
        self.warning.setObjectName("warning")
        self.warning.setWordWrap(True)
        self.warning.setVisible(False)
        layout.addWidget(self.warning)

    def build_guide(self):
        """Left: the gestures of the left hand. Right: the two-digit operator codes, one column per tens digit."""
        def table(rows):
            cells = "".join(f"<tr><td style='padding-right:10px'><b>{a}</b></td><td>{b}</td></tr>" for a, b in rows)
            return f"<table>{cells}</table>"

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(6)
        half = (len(GUIDE) + 1) // 2
        columns = [("LEFT HAND: HOLD A GESTURE", GUIDE[:half]), ("", GUIDE[half:])]
        for i, (tens, name) in enumerate(GROUPS):
            title = "RIGHT HAND ON THE WHITEBOARD: TWO DIGITS = ONE OPERATOR" if i == 0 else ""
            columns.append((title, [(code, label) for code, (_, label) in CODES.items() if code[0] == tens]))
        for column, (title, rows) in enumerate(columns):
            if title:
                head = QLabel(title)
                head.setObjectName("guideTitle")
                grid.addWidget(head, 0, column, 1, 2 if column == 0 else len(GROUPS))
            body = QLabel(table(rows))
            body.setObjectName("guide")
            body.setTextFormat(Qt.TextFormat.RichText)
            body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(body, 1, column)
            grid.setColumnStretch(column, 3 if column < 2 else 2)
        return grid

    # ------------------------------------------------------------ input
    def press(self, key):
        self.calc.press(key)
        self.refresh()

    def gesture_key(self, key, source, confidence):
        self.press(key)
        if source.startswith("code "):  # an operator, entered with its two-digit code
            label = CODES[source[5:]][1]
            self.last.setText(f"Entered {label} by code {source[5:]}")
        else:
            self.last.setText(f"Entered {key_label(key)} by gesture ({confidence:.0%})")

    def gesture_unknown(self, source, guess, confidence):
        if source == "code":
            self.last.setText(f"There is no operator with the code {guess}")
        else:
            self.last.setText(f"Gesture not recognised (closest: {guess}, {confidence:.0%})")

    def set_dwell(self, seconds):
        if self.camera is not None:
            self.camera.set_pause(seconds)

    def set_swap(self, on):
        if self.camera is not None:
            self.camera.swap_hands = on

    def set_gestures_enabled(self, on):
        if self.camera is not None:
            self.camera.enabled = on

    def show_warning(self, text):
        self.warning.setText(text)
        self.warning.setVisible(bool(text))

    def camera_failed(self, text):
        self.view.setText(text)
        self.hint.setText("")
        self.toggle.setEnabled(False)
        self.swap.setEnabled(False)

    # ------------------------------------------------------------ output
    def refresh(self):
        c = self.calc
        flags = [c.angle, ("M" if c.memory else "")]
        self.indicators.setText("   ".join(f for f in flags if f))
        expression = c.expression
        font = QFont("Consolas")
        font.setPixelSize(20 if len(expression) <= 48 else 15)
        self.expression.setFont(font)
        self.expression.setText(expression[-80:])
        text = c.result_text
        font = QFont("Consolas")
        font.setPixelSize(34)
        font.setWeight(QFont.Weight.DemiBold)
        self.result.setFont(font)
        self.result.setText(text)

    def show_frame(self, image):
        pixmap = QPixmap.fromImage(image).scaled(self.view.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation)
        self.view.setPixmap(pixmap)

    def closeEvent(self, event):
        if self.camera is not None:
            self.camera.stop()
        super().closeEvent(event)
