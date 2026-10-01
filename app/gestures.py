"""Static hand gestures (HaGRID classes) -> calculator keys.

The left hand may enter all of them; the right hand, on the whiteboard, only the digits (operators.py).
"""

# HaGRID class -> key id (see engine.INSERT). Classes that are not listed are ignored.
GESTURE_KEYS = {
    "fist": "0",
    "one": "1", "point": "1", "mute": "1",  # mute = index finger in front of the mouth: the same hand shape
    "peace": "2", "peace_inverted": "2", "two_up": "2", "two_up_inverted": "2",
    "three": "3", "three3": "3",
    "four": "4",
    "palm": "5", "stop": "5", "stop_inverted": "5",
    "call": "6",
    "three2": "7", "three_gun": "7",
    "thumb_index": "8",
    "ok": "9",
    "little_finger": "dot",
    "like": "eq",
    "dislike": "del",
    "xsign": "ac",  # both forearms crossed, away from the whiteboard
}

# for the on-screen guide: (what it enters, how to show it)
GUIDE = [
    ("0", "Fist"),
    ("1", "Index finger up"),
    ("2", "Index + middle (V)"),
    ("3", "Index + middle + ring"),
    ("4", "Four fingers, thumb folded"),
    ("5", "Open palm"),
    ("6", "Thumb + little finger"),
    ("7", "Thumb + index + middle"),
    ("8", "Thumb + index (L shape)"),
    ("9", "OK sign"),
    (".", "Little finger up"),
    ("=", "Thumb up"),
    ("DEL", "Thumb down"),
    ("AC", "Both arms crossed (X)"),
]

KEY_LABELS = {"dot": ".", "eq": "=", "del": "DEL", "ac": "AC"}


def key_label(key):
    return KEY_LABELS.get(key, key)
