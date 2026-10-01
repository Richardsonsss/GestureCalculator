"""Two-digit codes for the operators and functions.

The right hand shows two digits on the whiteboard, tens first; the code enters one operator. Codes with the
same digit twice (11, 22, 33) are left out, so the hand never has to show one gesture twice in a row.
"""

# code -> (key id for engine.Calculator.press, label shown in the window)
CODES = {
    # 0x  basic
    "01": ("add", "+"), "02": ("sub", "−"), "03": ("mul", "×"), "04": ("div", "÷"), "05": ("lp", "("),
    "06": ("rp", ")"), "07": ("pow", "^"), "08": ("sqrt", "√"), "09": ("percent", "%"),
    # 1x  trigonometry
    "10": ("sin", "sin"), "12": ("cos", "cos"), "13": ("tan", "tan"), "14": ("asin", "sin⁻¹"),
    "15": ("acos", "cos⁻¹"), "16": ("atan", "tan⁻¹"), "17": ("sinh", "sinh"), "18": ("cosh", "cosh"),
    "19": ("tanh", "tanh"),
    # 2x  logarithms and powers
    "20": ("log", "log"), "21": ("ln", "ln"), "23": ("pow10", "10ˣ"), "24": ("expe", "eˣ"), "25": ("sq", "x²"),
    "26": ("cube", "x³"), "27": ("inv", "x⁻¹"), "28": ("cbrt", "∛"), "29": ("fact", "x!"),
    # 3x  constants and others
    "30": ("pi", "π"), "31": ("e", "e"), "32": ("ans", "Ans"), "34": ("abs", "Abs"), "35": ("npr", "nPr"),
    "36": ("ncr", "nCr"), "37": ("exp", "×10ˣ"), "38": ("msave", "M save"), "39": ("mr", "M recall"),
    # 4x  settings
    "40": ("drg", "DEG/RAD/GRA"), "41": ("sd", "S⇔D"),
}
GROUPS = [("0", "Basic"), ("1", "Trigonometry"), ("2", "Logs and powers"), ("3", "Constants, other"),
          ("4", "Settings")]


class CodeEntry:
    """Collects the two digits. Pure logic: fed digits with their time, returns what was entered."""

    def __init__(self, timeout=6.0):
        self.timeout = timeout   # a tens digit left alone this long is dropped
        self.tens = None
        self.tens_time = None

    def tick(self, t):
        """Call every frame. Returns True when a lonely tens digit was just dropped."""
        if self.tens is not None and t - self.tens_time > self.timeout:
            self.tens = None
            return True
        return False

    def cancel(self):
        self.tens = None

    def feed(self, digit, t):
        """digit: "0".."9". Returns None after the tens digit, else (code, key or None, label or None)."""
        if self.tens is None:
            self.tens, self.tens_time = digit, t
            return None
        code, self.tens = self.tens + digit, None
        key, label = CODES.get(code, (None, None))
        return code, key, label
