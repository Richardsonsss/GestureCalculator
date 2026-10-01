"""Diagrams for the manual.

    python docs/source/make_diagrams.py        ->  docs/images/*.png

Drawn 800 units wide (x3 for print sharpness). window.png is made separately by make_window_shot.py, because
it is a screenshot of the real program.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(os.path.dirname(HERE), "images")
S = 3
W = 800
FONT, BOLD, MONO = (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\consola.ttf")

TEAL, TEAL_BG = (15, 118, 110), (230, 244, 242)       # left hand
AMBER, AMBER_BG = (180, 83, 9), (254, 243, 224)       # right hand
BLUE, BLUE_BG = (37, 99, 235), (232, 240, 254)        # neural network
VIOLET, VIOLET_BG = (109, 40, 217), (241, 236, 254)   # calculator
GREY, GREY_BG, INK, MUTED = (100, 116, 139), (241, 245, 249), (15, 23, 42), (71, 85, 105)
LCD = (217, 228, 210)


def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else BOLD if bold else FONT, int(size * S))


def canvas(h, w=W):
    im = Image.new("RGB", (w * S, int(h * S)), "white")
    return im, ImageDraw.Draw(im)


def text(d, xy, s, size=13, bold=False, fill=INK, anchor="lm", mono=False):
    d.text((xy[0] * S, xy[1] * S), s, font=font(size, bold, mono), fill=fill, anchor=anchor)


def box(d, x, y, w, h, fg, bg, radius=10, width=2):
    d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=radius * S, fill=bg, outline=fg, width=width * S)


def label_box(d, x, y, w, h, title, sub, fg, bg, size=13):
    box(d, x, y, w, h, fg, bg)
    if sub:
        text(d, (x + w / 2, y + h / 2 - 9), title, size, True, fg, "mm")
        text(d, (x + w / 2, y + h / 2 + 10), sub, 10.5, False, MUTED, "mm")
    else:
        text(d, (x + w / 2, y + h / 2), title, size, True, fg, "mm")


def arrow(d, x1, y1, x2, y2, color=GREY, width=2.5, label="", side=1):
    d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=color, width=int(width * S))
    a = math.atan2(y2 - y1, x2 - x1)
    L = 9
    pts = [(x2, y2), (x2 - L * math.cos(a - 0.45), y2 - L * math.sin(a - 0.45)),
           (x2 - L * math.cos(a + 0.45), y2 - L * math.sin(a + 0.45))]
    d.polygon([(px * S, py * S) for px, py in pts], fill=color)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) > abs(y2 - y1):
            text(d, (mx, my - 10 * side), label, 10.5, False, MUTED, "mm")
        else:
            text(d, (mx + 8 * side, my), label, 10.5, False, MUTED, "lm" if side > 0 else "rm")


def badge(d, x, y, s, fg, r=11, size=12):
    d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fg)
    text(d, (x, y), s, size, True, "white", "mm")


# ------------------------------------------------------------------ schematic hands
def bar(d, x1, y1, x2, y2, w, fg, bg):
    """A finger: a thick rounded line with an outline."""
    for width, color in ((w + 4, fg), (w, bg)):
        d.line([x1 * S, y1 * S, x2 * S, y2 * S], fill=color, width=int(width * S))
        r = width / 2
        for cx, cy in ((x1, y1), (x2, y2)):
            d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=color)


def hand(d, cx, cy, fingers, k=1.0, fg=TEAL, bg=TEAL_BG, ok=False):
    """Front view of a raised hand. fingers = (thumb, index, middle, ring, little), 1 = extended."""
    pw, ph = 46 * k, 44 * k
    x0, y0 = cx - pw / 2, cy - ph / 2 + 16 * k
    fw = 9 * k
    xs = [x0 + pw * f for f in (0.14, 0.38, 0.62, 0.86)]
    lengths = (34, 38, 35, 28)
    for i, x in enumerate(xs):  # index .. little finger
        up = fingers[i + 1]
        if ok and i == 0:
            continue
        length = lengths[i] * k if up else 7 * k
        bar(d, x, y0 + 2 * k, x, y0 - length, fw, fg, bg)
    # thumb, on the left side
    if ok:  # thumb and index finger form a ring
        r = 11 * k
        ox, oy = x0 + 5 * k, y0 - 9 * k
        d.ellipse([(ox - r) * S, (oy - r) * S, (ox + r) * S, (oy + r) * S], outline=fg, width=int(5 * k * S))
        d.ellipse([(ox - r + 3.4 * k) * S, (oy - r + 3.4 * k) * S, (ox + r - 3.4 * k) * S, (oy + r - 3.4 * k) * S],
                  outline=bg, width=int(2.2 * k * S))
    elif fingers[0]:
        bar(d, x0 + 3 * k, y0 + ph * 0.55, x0 - 20 * k, y0 + ph * 0.1, fw, fg, bg)
    else:
        bar(d, x0 + 6 * k, y0 + ph * 0.5, x0 + 22 * k, y0 + ph * 0.36, fw, fg, bg)
    d.rounded_rectangle([x0 * S, y0 * S, (x0 + pw) * S, (y0 + ph) * S], radius=int(11 * k * S), fill=bg, outline=fg,
                        width=int(2 * S))
    if not fingers[0] and not ok:  # the folded thumb lies across the palm
        bar(d, x0 + 8 * k, y0 + ph * 0.5, x0 + 24 * k, y0 + ph * 0.36, fw - 2, fg, bg)


def thumb_fist(d, cx, cy, up=True, k=1.0, fg=TEAL, bg=TEAL_BG):
    """A fist seen from the side with the thumb pointing up or down."""
    w, h = 44 * k, 38 * k
    x0, y0 = cx - w / 2, cy - h / 2 + (8 * k if up else -8 * k)
    ty = y0 if up else y0 + h
    bar(d, x0 + 10 * k, ty, x0 + 10 * k, ty + (-28 * k if up else 28 * k), 10 * k, fg, bg)
    d.rounded_rectangle([x0 * S, y0 * S, (x0 + w) * S, (y0 + h) * S], radius=int(11 * k * S), fill=bg, outline=fg,
                        width=int(2 * S))
    for i in range(1, 4):  # the folded fingers
        y = y0 + h * i / 4
        d.line([(x0 + w * 0.42) * S, y * S, (x0 + w) * S, y * S], fill=fg, width=int(1.5 * S))


def crossed_arms(d, cx, cy, k=1.0, fg=TEAL, bg=TEAL_BG):
    for sign in (1, -1):
        bar(d, cx - 26 * k * sign, cy + 30 * k, cx + 22 * k * sign, cy - 22 * k, 13 * k, fg, bg)
        r = 10 * k
        ex, ey = cx + 24 * k * sign, cy - 25 * k
        d.ellipse([(ex - r) * S, (ey - r) * S, (ex + r) * S, (ey + r) * S], fill=bg, outline=fg, width=int(2 * S))


GESTURES = [  # key, name, kind, fingers
    ("0", "Fist", "hand", (0, 0, 0, 0, 0)),
    ("1", "Index finger", "hand", (0, 1, 0, 0, 0)),
    ("2", "Index + middle", "hand", (0, 1, 1, 0, 0)),
    ("3", "Index, middle, ring", "hand", (0, 1, 1, 1, 0)),
    ("4", "Four fingers", "hand", (0, 1, 1, 1, 1)),
    ("5", "Open palm", "hand", (1, 1, 1, 1, 1)),
    ("6", "Thumb + little", "hand", (1, 0, 0, 0, 1)),
    ("7", "Thumb, index, middle", "hand", (1, 1, 1, 0, 0)),
    ("8", "Thumb + index (L)", "hand", (1, 1, 0, 0, 0)),
    ("9", "OK sign", "ok", (0, 0, 1, 1, 1)),
    (".", "Little finger", "hand", (0, 0, 0, 0, 1)),
    ("=", "Thumb up", "up", None),
    ("DEL", "Thumb down", "down", None),
    ("AC", "Arms crossed", "arms", None),
]


def draw_gesture(d, cx, cy, kind, fingers, k=1.0, fg=TEAL, bg=TEAL_BG):
    if kind == "hand":
        hand(d, cx, cy, fingers, k, fg, bg)
    elif kind == "ok":
        hand(d, cx, cy, fingers, k, fg, bg, ok=True)
    elif kind in ("up", "down"):
        thumb_fist(d, cx, cy, kind == "up", k, fg, bg)
    else:
        crossed_arms(d, cx, cy, k, fg, bg)


def gesture_by_key(key):
    return next(g for g in GESTURES if g[0] == key)


# ------------------------------------------------------------------ figures
def overview(out):
    im, d = canvas(330)
    label_box(d, 20, 130, 100, 60, "Webcam", "picture", GREY, GREY_BG)
    label_box(d, 150, 130, 130, 60, "Hand tracking", "finds both hands", BLUE, BLUE_BG)
    arrow(d, 120, 160, 148, 160)
    # two lanes
    box(d, 310, 20, 330, 130, TEAL, "white")
    text(d, (322, 38), "LEFT HAND", 11, True, TEAL)
    hand(d, 352, 92, (0, 1, 1, 0, 0), 0.75, TEAL, TEAL_BG)
    text(d, (392, 78), "one gesture, held for 1 s", 12.5, True, INK)
    text(d, (392, 98), "enters a digit,  .  =  DEL  or  AC", 11.5, False, MUTED)
    box(d, 310, 180, 330, 130, AMBER, "white")
    text(d, (322, 198), "RIGHT HAND on the whiteboard", 11, True, AMBER)
    hand(d, 352, 252, (0, 1, 0, 0, 0), 0.75, AMBER, AMBER_BG)
    text(d, (392, 238), "two gestures, 0.5 s each", 12.5, True, INK)
    text(d, (392, 258), "tens + units = code of an operator", 11.5, False, MUTED)
    arrow(d, 280, 148, 308, 100)
    arrow(d, 280, 172, 308, 230)
    label_box(d, 670, 130, 110, 60, "Calculator", "display", VIOLET, VIOLET_BG)
    arrow(d, 640, 100, 690, 128)
    arrow(d, 640, 230, 690, 192)
    text(d, (W / 2, 322), "Everything runs on this computer. No internet connection is used.", 11, False, MUTED, "mm")
    im.save(out)


def gestures(out):
    cols, cw, ch = 7, 108, 168
    im, d = canvas(ch * 2 + 12)
    for i, (key, name, kind, fingers) in enumerate(GESTURES):
        x, y = 22 + (i % cols) * cw, 8 + (i // cols) * ch
        cx = x + (cw - 10) / 2
        box(d, x, y, cw - 10, ch - 12, (203, 213, 225), "white", radius=10, width=1)
        draw_gesture(d, cx + 4, y + 58, kind, fingers, 0.95)
        wide = len(key) > 1
        d.rounded_rectangle([(cx - (20 if wide else 13)) * S, (y + 104) * S, (cx + (20 if wide else 13)) * S,
                             (y + 130) * S], radius=13 * S, fill=TEAL)
        text(d, (cx, y + 117), key, 12 if wide else 14, True, "white", "mm")
        text(d, (cx, y + ch - 26), name, 9, False, MUTED, "mm")
    im.save(out)


def board(d, x, y, w, h, tens="", units="", label="", pen=AMBER):
    box(d, x, y, w, h, GREY, (243, 244, 246), radius=6)
    d.line([(x + w / 2) * S, y * S, (x + w / 2) * S, (y + h) * S], fill=GREY, width=int(1.5 * S))
    text(d, (x + w / 4, y + 12), "tens", 9, False, MUTED, "mm")
    text(d, (x + 3 * w / 4, y + 12), "units", 9, False, MUTED, "mm")
    if tens:
        text(d, (x + w / 4, y + h * 0.36), tens, 30, True, pen, "mm")
    if units:
        text(d, (x + 3 * w / 4, y + h * 0.36), units, 30, True, pen, "mm")
    if label:
        d.rounded_rectangle([(x + w / 2 - 30) * S, (y + h - 27) * S, (x + w / 2 + 30) * S, (y + h - 5) * S],
                            radius=11 * S, fill="white", outline=pen, width=int(1.5 * S))
        text(d, (x + w / 2, y + h - 16), label, 13, True, INK, "mm")


def whiteboard(out):
    im, d = canvas(300)
    steps = [("1", "Show the tens digit", "hold 0.5 s", "1", "", "", (0, 1, 0, 0, 0), ""),
             ("2", "Change to the units digit", "hold 0.5 s", "1", "0", "", (0, 0, 0, 0, 0), ""),
             ("3", "The operator is entered", "its name appears for a moment", "1", "0", "sin", None, "sin(")]
    pw = 240
    for i, (n, title, sub, tens, units, label, fingers, lcd) in enumerate(steps):
        x = 20 + i * (pw + 20)
        badge(d, x + 12, 18, n, AMBER)
        text(d, (x + 30, 12), title, 12.5, True, INK)
        text(d, (x + 30, 29), sub, 10.5, False, MUTED)
        # the camera picture with the whiteboard in its top right corner
        box(d, x, 46, pw, 170, GREY, (226, 232, 240), radius=8)
        text(d, (x + 12, 204), "camera picture", 9, False, MUTED)
        board(d, x + pw * 0.38, 54, pw * 0.59, 138, tens, units, label)
        if fingers is not None:  # the hand is on the board, under the digits
            hand(d, x + pw * 0.38 + pw * 0.59 * (0.25 if i == 0 else 0.75), 150, fingers, 0.55, AMBER, AMBER_BG)
        # the display
        box(d, x, 232, pw, 46, (148, 163, 184), LCD, radius=8, width=1)
        text(d, (x + 12, 255), lcd, 16, False, INK, mono=True)
        if i < 2:
            arrow(d, x + pw + 3, 130, x + pw + 17, 130, AMBER)
    text(d, (20, 290), "The right hand counts only while its palm is on the whiteboard.", 10.5, False, MUTED)
    im.save(out)


def timing(out):
    im, d = canvas(250)
    x0, x1 = 150, 760
    def lane(y, name, color, bg, segments):
        text(d, (20, y + 17), name, 12, True, color)
        d.line([x0 * S, (y + 34) * S, x1 * S, (y + 34) * S], fill=(203, 213, 225), width=S)
        for a, b, kind, label in segments:
            xa, xb = x0 + a * 200, x0 + b * 200
            if kind == "hold":
                box(d, xa, y, xb - xa, 34, color, bg, radius=6)
                text(d, ((xa + xb) / 2, y + 17), label, 10.5, True, color, "mm")
            elif kind == "change":
                box(d, xa, y, xb - xa, 34, (203, 213, 225), "white", radius=6, width=1)
                text(d, ((xa + xb) / 2, y + 17), label, 9.5, False, MUTED, "mm")
            else:  # the moment something is entered
                d.line([xa * S, (y - 8) * S, xa * S, (y + 44) * S], fill=INK, width=int(1.5 * S))
                text(d, (xa + 5, y - 10), label, 10.5, True, INK)
    lane(40, "Left hand", TEAL, TEAL_BG, [
        (0, 1.0, "hold", "gesture 3, held 1.0 s"), (1.0, 1.0, "enter", "3 entered"),
        (1.0, 1.5, "change", "change"), (1.5, 2.5, "hold", "gesture 0, held 1.0 s"), (2.5, 2.5, "enter", "0 entered")])
    lane(140, "Right hand", AMBER, AMBER_BG, [
        (0, 0.5, "hold", "tens 0.5 s"), (0.5, 0.5, "enter", "0 _"),
        (0.5, 0.9, "change", "change"), (0.9, 1.4, "hold", "units 0.5 s"), (1.4, 1.4, "enter", "0 1  =  +  entered")])
    for i in range(7):  # time axis, a tick every half second
        x = x0 + i * 100
        d.line([x * S, 206 * S, x * S, 212 * S], fill=GREY, width=S)
        text(d, (x, 222), f"{i / 2:g} s", 10, False, MUTED, "mm")
    d.line([x0 * S, 206 * S, x1 * S, 206 * S], fill=GREY, width=S)
    text(d, (20, 240), "A ring around the hand fills while the pause runs. Moving the hand restarts it.", 10.5, False, MUTED)
    im.save(out)


def example(out):
    steps = [("R", ["1", "0"], "code 10", "sin("), ("L", ["3"], "", "sin(3"), ("L", ["0"], "", "sin(30"),
             ("R", ["0", "6"], "code 06", "sin(30)"), ("R", ["0", "1"], "code 01", "sin(30)+"),
             ("L", ["5"], "", "sin(30)+5"), ("L", ["="], "", "5.5")]
    im, d = canvas(250)
    cw = (W - 40) / len(steps)
    for i, (side, keys, note, lcd) in enumerate(steps):
        fg, bg = (TEAL, TEAL_BG) if side == "L" else (AMBER, AMBER_BG)
        x = 20 + i * cw
        box(d, x + 3, 30, cw - 6, 128, fg, "white", radius=8)
        badge(d, x + cw / 2, 30, str(i + 1), fg, r=10, size=11)
        text(d, (x + cw / 2, 52), "LEFT" if side == "L" else "RIGHT", 9.5, True, fg, "mm")
        k = 0.5 if len(keys) == 2 else 0.62
        for j, key in enumerate(keys):
            _, _, kind, fingers = gesture_by_key(key)
            cx = x + cw / 2 + (j - (len(keys) - 1) / 2) * 44
            draw_gesture(d, cx + 3, 92, kind, fingers, k, fg, bg)
            text(d, (cx, 134), key, 12, True, fg, "mm")
        if note:
            text(d, (x + cw / 2, 149), note, 9, False, MUTED, "mm")
        box(d, x + 3, 172, cw - 6, 34, (148, 163, 184), LCD, radius=6, width=1)
        text(d, (x + cw / 2, 189), lcd, 10.5 if len(lcd) > 8 else 12, i == len(steps) - 1, INK, "mm", mono=True)
        if i < len(steps) - 1:
            arrow(d, x + cw - 2, 94, x + cw + 4, 94, GREY, 2)
    text(d, (20, 10), "Entering  sin(30)+5", 12.5, True, INK)
    text(d, (20, 228), "Top: the gesture shown.  Bottom: the display after the step.", 10.5, False, MUTED)
    im.save(out)


def pipeline(out):
    im, d = canvas(300)
    label_box(d, 20, 20, 130, 54, "Camera frame", "about 15-30 a second", GREY, GREY_BG)
    label_box(d, 190, 20, 170, 54, "MediaPipe hand tracker", "21 points per hand, left / right", BLUE, BLUE_BG)
    arrow(d, 150, 47, 188, 47)
    label_box(d, 400, 20, 170, 54, "Is the hand still?", "stays inside a small circle", GREY, GREY_BG)
    arrow(d, 360, 47, 398, 47)
    label_box(d, 610, 20, 170, 54, "Paint over the other hand", "one hand per look", GREY, GREY_BG)
    arrow(d, 570, 47, 608, 47, label="yes")
    arrow(d, 695, 74, 695, 116)
    label_box(d, 610, 118, 170, 54, "ResNet-152", "names 1 of 34 gestures", BLUE, BLUE_BG)
    arrow(d, 608, 145, 572, 145)
    label_box(d, 400, 118, 170, 54, "Average over the pause", "1.0 s left, 0.5 s right", GREY, GREY_BG)
    arrow(d, 398, 145, 362, 145)
    label_box(d, 190, 118, 170, 54, "Clear enough?", "else: nothing is entered", GREY, GREY_BG)
    d.line([275 * S, 172 * S, 275 * S, 196 * S], fill=GREY, width=int(2.5 * S))
    d.line([160 * S, 196 * S, 390 * S, 196 * S], fill=GREY, width=int(2.5 * S))
    text(d, (283, 184), "yes", 10.5, False, MUTED)
    arrow(d, 160, 196, 160, 214)
    arrow(d, 390, 196, 390, 214)
    label_box(d, 60, 216, 200, 60, "Left hand", "digit  .  =  DEL  AC", TEAL, TEAL_BG)
    label_box(d, 290, 216, 200, 60, "Right hand", "digit  ->  tens, units  ->  code", AMBER, AMBER_BG)
    label_box(d, 560, 216, 220, 60, "Calculator engine", "builds and works out the expression", VIOLET, VIOLET_BG)
    arrow(d, 490, 246, 558, 246)
    d.line([160 * S, 276 * S, 160 * S, 290 * S, 670 * S, 290 * S, 670 * S, 278 * S], fill=GREY, width=int(2.5 * S))
    arrow(d, 670, 290, 670, 278)
    im.save(out)


def decision(out):
    im, d = canvas(330)
    def diamond(cx, cy, w, h, s1, s2=""):
        d.polygon([(cx * S, (cy - h / 2) * S), ((cx + w / 2) * S, cy * S), (cx * S, (cy + h / 2) * S),
                   ((cx - w / 2) * S, cy * S)], fill=GREY_BG, outline=GREY)
        d.line([(cx * S, (cy - h / 2) * S), ((cx + w / 2) * S, cy * S), (cx * S, (cy + h / 2) * S),
                ((cx - w / 2) * S, cy * S), (cx * S, (cy - h / 2) * S)], fill=GREY, width=2 * S)
        text(d, (cx, cy - (7 if s2 else 0)), s1, 11, True, INK, "mm")
        if s2:
            text(d, (cx, cy + 8), s2, 9.5, False, MUTED, "mm")
    cy = 70
    xs = [110, 300, 490, 680]
    labels = [("Hand still?", ""), ("Same shape?", ""), ("Pause over?", "1.0 s / 0.5 s"), ("Network sure?", "")]
    for x, (a, b) in zip(xs, labels):
        diamond(x, cy, 150, 76, a, b)
    for a, b in zip(xs[:-1], xs[1:]):
        arrow(d, a + 75, cy, b - 75, cy, label="yes")
    text(d, (20, 20), "Checked on every camera frame, for each hand", 11, False, MUTED)
    # "no" branches
    label_box(d, 40, 150, 330, 44, "The pause starts again", "", GREY, "white", 12)
    for x in xs[:2]:
        arrow(d, x, cy + 38, x, 148, label="no")
    label_box(d, 420, 150, 140, 44, "Keep waiting", "", GREY, "white", 12)
    arrow(d, 490, cy + 38, 490, 148, label="no")
    label_box(d, 600, 150, 160, 44, "Nothing is entered", "", GREY, "white", 12)
    arrow(d, 680, cy + 38, 680, 148, label="no")
    label_box(d, 560, 236, 200, 50, "The key is entered", "", VIOLET, VIOLET_BG, 13)
    d.line([755 * S, cy * S, 786 * S, cy * S, 786 * S, 261 * S], fill=GREY, width=int(2.5 * S))
    arrow(d, 786, 261, 762, 261)
    text(d, (780, 150), "yes", 10.5, False, MUTED, "rm")
    label_box(d, 40, 236, 470, 50, "Then: wait for another shape,", "a move away, or the hand leaving the picture", GREY, "white", 12)
    arrow(d, 558, 261, 512, 261)
    text(d, (20, 312), "This is why a held gesture is entered once, and why a shape shown only in passing is ignored.",
         10.5, False, MUTED)
    im.save(out)


def files(out):
    im, d = canvas(210)
    text(d, (20, 16), "To run the program, keep these three together:", 12, True, INK)
    items = [("GestureCalculator.exe", "double-click to start", VIOLET, VIOLET_BG),
             ("_internal\\", "the program's own libraries", GREY, GREY_BG),
             ("models\\", "hand tracker + gesture network", BLUE, BLUE_BG)]
    for i, (name, sub, fg, bg) in enumerate(items):
        x = 20 + i * 256
        box(d, x, 34, 244, 56, fg, bg)
        text(d, (x + 122, 54), name, 12.5, True, fg, "mm", mono=True)
        text(d, (x + 122, 74), sub, 10.5, False, MUTED, "mm")
    text(d, (20, 116), "Source code (only needed to change or rebuild the program):", 12, True, INK)
    src = [("app\\", "calculator, gestures, operator codes, camera, window"), ("tools\\", "converts the gesture network"),
           ("tests\\", "automatic tests"), ("docs\\", "this manual")]
    for i, (name, sub) in enumerate(src):
        x = 20 + i * 192
        box(d, x, 134, 182, 56, (203, 213, 225), "white", width=1)
        text(d, (x + 91, 152), name, 12, True, INK, "mm", mono=True)
        lines = [sub] if len(sub) < 30 else [sub[:sub.rfind(",", 0, 30) + 1], sub[sub.rfind(",", 0, 30) + 2:]]
        for j, line in enumerate(lines):
            text(d, (x + 91, 169 + j * 12 - (6 if len(lines) > 1 else 0)), line, 9, False, MUTED, "mm")
    im.save(out)


def main():
    os.makedirs(IMAGES, exist_ok=True)
    for name, fn in (("overview", overview), ("gestures", gestures), ("whiteboard", whiteboard), ("timing", timing),
                     ("example", example), ("pipeline", pipeline), ("decision", decision), ("files", files)):
        fn(os.path.join(IMAGES, name + ".png"))
    print("diagrams ok:", ", ".join(sorted(f for f in os.listdir(IMAGES) if f.endswith(".png"))))


if __name__ == "__main__":
    main()
