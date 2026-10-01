"""Scientific calculator engine: a token list, a recursive-descent evaluator and Casio-style key handling.

The engine knows nothing about cameras or windows. Both the on-screen keypad and the gesture controller
drive it through Calculator.press(key).
"""
import math
from fractions import Fraction

SYNTAX_ERROR = "Syntax ERROR"
MATH_ERROR = "Math ERROR"

# key id -> token appended to the expression
INSERT = {
    **{str(d): str(d) for d in range(10)},
    "dot": ".", "add": "+", "sub": "−", "mul": "×", "div": "÷", "lp": "(", "rp": ")", "pow": "^",
    "sq": "²", "cube": "³", "inv": "⁻¹", "fact": "!", "percent": "%", "exp": "ᴇ",
    "sqrt": "√(", "cbrt": "∛(", "sin": "sin(", "cos": "cos(", "tan": "tan(",
    "asin": "sin⁻¹(", "acos": "cos⁻¹(", "atan": "tan⁻¹(", "sinh": "sinh(", "cosh": "cosh(", "tanh": "tanh(",
    "log": "log(", "ln": "ln(", "abs": "Abs(", "pow10": "10^(", "expe": "e^(",
    "pi": "π", "e": "e", "ans": "Ans", "mr": "M", "npr": "P", "ncr": "C",
}
DIGITS = set("0123456789")
FUNCTIONS = {"√(", "∛(", "sin(", "cos(", "tan(", "sin⁻¹(", "cos⁻¹(", "tan⁻¹(", "sinh(", "cosh(", "tanh(",
             "log(", "ln(", "Abs(", "10^(", "e^("}
POSTFIX = {"²", "³", "⁻¹", "!", "%"}
# after "=", these continue from the previous answer ("Ans + ...") instead of starting a new expression
CONTINUE_WITH_ANS = {"+", "−", "×", "÷", "^", "²", "³", "⁻¹", "!", "%", "P", "C"}
ANGLE_MODES = ("DEG", "RAD", "GRA")


class CalcError(Exception):
    pass


class Evaluator:
    """expr := term (('+'|'−') term)*
    term   := perm (('×'|'÷') perm | perm)*          (a missing operator means multiplication: 2π, 3sin(30))
    perm   := unary (('P'|'C') unary)*
    unary  := '−' unary | power
    power  := postfix ('^' unary)?
    postfix:= primary ('²'|'³'|'⁻¹'|'!'|'%')*
    primary:= number | constant | function expr ')'? | '(' expr ')'?   (missing ')' at the end is allowed)
    """

    def __init__(self, tokens, angle="DEG", ans=0.0, memory=0.0):
        self.tokens, self.pos, self.angle, self.ans, self.memory = tokens, 0, angle, ans, memory

    # ------------------------------------------------------------ helpers
    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def to_radians(self, x):
        return {"DEG": math.radians(x), "RAD": x, "GRA": x * math.pi / 200}[self.angle]

    def from_radians(self, x):
        return {"DEG": math.degrees(x), "RAD": x, "GRA": x * 200 / math.pi}[self.angle]

    # ------------------------------------------------------------ grammar
    def evaluate(self):
        if not self.tokens:
            raise CalcError(SYNTAX_ERROR)
        value = self.expr()
        if self.peek() is not None:
            raise CalcError(SYNTAX_ERROR)
        return check(value)

    def expr(self):
        value = self.term()
        while self.peek() in ("+", "−"):
            op = self.take()
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def starts_primary(self, tok):
        return tok is not None and (tok in DIGITS or tok in (".", "(", "π", "e", "Ans", "M") or tok in FUNCTIONS)

    def term(self):
        value = self.perm()
        while True:
            tok = self.peek()
            if tok in ("×", "÷"):
                self.take()
                rhs = self.perm()
                if tok == "÷":
                    if rhs == 0:
                        raise CalcError(MATH_ERROR)
                    value = value / rhs
                else:
                    value = value * rhs
            elif self.starts_primary(tok):
                value = value * self.perm()
            else:
                return value

    def perm(self):
        value = self.unary()
        while self.peek() in ("P", "C"):
            op = self.take()
            value = combinatorial(value, self.unary(), op)
        return value

    def unary(self):
        if self.peek() == "−":
            self.take()
            return -self.unary()
        if self.peek() == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        base = self.postfix()
        if self.peek() == "^":
            self.take()
            return power(base, self.unary())
        return base

    def postfix(self):
        value = self.primary()
        while self.peek() in POSTFIX:
            op = self.take()
            if op == "²":
                value = power(value, 2)
            elif op == "³":
                value = power(value, 3)
            elif op == "⁻¹":
                if value == 0:
                    raise CalcError(MATH_ERROR)
                value = 1 / value
            elif op == "!":
                value = factorial(value)
            else:
                value = value / 100
        return value

    def primary(self):
        tok = self.peek()
        if tok is None:
            raise CalcError(SYNTAX_ERROR)
        if tok in DIGITS or tok == ".":
            return self.number()
        self.take()
        if tok == "π":
            return math.pi
        if tok == "e":
            return math.e
        if tok == "Ans":
            return self.ans
        if tok == "M":
            return self.memory
        if tok == "(":
            value = self.expr()
            self.close()
            return value
        if tok in FUNCTIONS:
            arg = self.expr()
            self.close()
            return self.call(tok, arg)
        raise CalcError(SYNTAX_ERROR)

    def close(self):
        if self.peek() == ")":
            self.take()
        elif self.peek() is not None:
            raise CalcError(SYNTAX_ERROR)

    def number(self):
        text = ""
        while self.peek() is not None and (self.peek() in DIGITS or self.peek() == "."):
            text += self.take()
        if self.peek() == "ᴇ":  # ×10^ exponent entry: 1.5ᴇ−3
            self.take()
            exponent = ""
            if self.peek() in ("−", "+"):
                exponent = "-" if self.take() == "−" else ""
            digits = ""
            while self.peek() is not None and self.peek() in DIGITS:
                digits += self.take()
            if not digits:
                raise CalcError(SYNTAX_ERROR)
            text += "e" + exponent + digits
        try:
            return float(text)
        except ValueError:
            raise CalcError(SYNTAX_ERROR) from None

    def call(self, name, x):
        try:
            if name == "√(":
                return math.sqrt(x)
            if name == "∛(":
                return math.copysign(abs(x) ** (1 / 3), x)
            if name == "sin(":
                return snap(math.sin(self.to_radians(x)))
            if name == "cos(":
                return snap(math.cos(self.to_radians(x)))
            if name == "tan(":
                r = self.to_radians(x)
                if abs(snap(math.cos(r))) == 0:
                    raise CalcError(MATH_ERROR)
                return snap(math.tan(r))
            if name == "sin⁻¹(":
                return self.from_radians(math.asin(x))
            if name == "cos⁻¹(":
                return self.from_radians(math.acos(x))
            if name == "tan⁻¹(":
                return self.from_radians(math.atan(x))
            if name == "sinh(":
                return math.sinh(x)
            if name == "cosh(":
                return math.cosh(x)
            if name == "tanh(":
                return math.tanh(x)
            if name == "log(":
                return math.log10(x)
            if name == "ln(":
                return math.log(x)
            if name == "Abs(":
                return abs(x)
            if name == "10^(":
                return power(10, x)
            if name == "e^(":
                return math.exp(x)
        except (ValueError, OverflowError):
            raise CalcError(MATH_ERROR) from None
        raise CalcError(SYNTAX_ERROR)


def snap(x):
    """Remove floating-point noise so that sin(180 deg) is 0 and cos(60 deg) is 0.5."""
    r = round(x, 14)
    return 0.0 if r == 0 else r


def check(x):
    if isinstance(x, complex) or math.isnan(x) or math.isinf(x) or abs(x) >= 1e100:
        raise CalcError(MATH_ERROR)
    return float(x)


def power(base, exponent):
    try:
        if base == 0 and exponent <= 0:
            raise CalcError(MATH_ERROR)
        if base < 0 and exponent != int(exponent):
            # odd roots of negative numbers, e.g. (−8)^(1/3), are real; other fractional powers are not
            f = Fraction(exponent).limit_denominator(1000)
            if abs(float(f) - exponent) < 1e-12 and f.denominator % 2 == 1:
                value = abs(base) ** exponent
                return -value if f.numerator % 2 else value
            raise CalcError(MATH_ERROR)
        return check(base ** exponent)
    except (OverflowError, ZeroDivisionError):
        raise CalcError(MATH_ERROR) from None


def as_count(x):
    if x < 0 or abs(x - round(x)) > 1e-9:
        raise CalcError(MATH_ERROR)
    return int(round(x))


def factorial(x):
    n = as_count(x)
    if n > 69:  # 70! exceeds the display range (1e100)
        raise CalcError(MATH_ERROR)
    return float(math.factorial(n))


def combinatorial(n, r, op):
    n, r = as_count(n), as_count(r)
    if r > n:
        raise CalcError(MATH_ERROR)
    return check(float(math.perm(n, r) if op == "P" else math.comb(n, r)))


def format_number(x):
    """10 significant digits; scientific notation outside 1e-9 .. 1e10, like a pocket calculator."""
    if x == 0:
        return "0"
    if abs(x) >= 1e10 or abs(x) < 1e-9:
        mantissa, exponent = f"{x:.9e}".split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}×10^{int(exponent)}".replace("-", "−")
    text = f"{x:.10g}"
    if "e" in text:
        text = f"{x:.10f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace("-", "−")


def format_fraction(x):
    """'3/4' when x is a simple fraction, otherwise None."""
    if abs(x) >= 1e7 or x == int(x):
        return None
    f = Fraction(x).limit_denominator(9999)
    if abs(float(f) - x) > 1e-11 * max(1.0, abs(x)):
        return None
    return f"{f.numerator}/{f.denominator}".replace("-", "−")


class Calculator:
    def __init__(self):
        self.tokens = []
        self.result = None  # float after "=", else None
        self.error = ""
        self.ans = 0.0
        self.memory = 0.0
        self.angle = "DEG"
        self.shift = False
        self.as_fraction = False
        self.history = []  # (expression text, result text), newest last

    # ------------------------------------------------------------ display
    @property
    def expression(self):
        return "".join(self.tokens)

    @property
    def result_text(self):
        if self.error:
            return self.error
        if self.result is None:
            return ""
        if self.as_fraction:
            fraction = format_fraction(self.result)
            if fraction:
                return fraction
        return format_number(self.result)

    # ------------------------------------------------------------ keys
    def press(self, key):
        """Handle one key id (see INSERT plus eq, del, ac, shift, drg, sd, neg, msave, mplus, mminus, mc)."""
        if key == "shift":
            self.shift = not self.shift
            return
        self.shift = False
        if key == "ac":
            self.tokens, self.result, self.error, self.as_fraction = [], None, "", False
        elif key == "del":
            if self.error or self.result is not None:
                self.result, self.error = None, ""  # back to editing the expression
            elif self.tokens:
                self.tokens.pop()
        elif key == "eq":
            self.equals()
        elif key == "drg":
            self.angle = ANGLE_MODES[(ANGLE_MODES.index(self.angle) + 1) % len(ANGLE_MODES)]
            if self.result is not None and not self.error:
                self.equals(store=False)
        elif key == "sd":
            if self.result is not None:
                self.as_fraction = not self.as_fraction
        elif key in ("msave", "mplus", "mminus"):
            if self.result is None and self.tokens:
                self.equals()
            if self.result is not None and not self.error:
                self.memory = {"msave": self.result, "mplus": self.memory + self.result,
                               "mminus": self.memory - self.result}[key]
        elif key == "mc":
            self.memory = 0.0
        elif key == "neg":
            self.insert("−")
        elif key in INSERT:
            self.insert(INSERT[key])

    def insert(self, token):
        if self.error:
            self.tokens, self.error = [], ""
        if self.result is not None:  # a finished calculation: continue from Ans or start again
            self.tokens = ["Ans"] if token in CONTINUE_WITH_ANS else []
            self.result, self.as_fraction = None, False
        self.tokens.append(token)

    def equals(self, store=True):
        if not self.tokens:
            return
        try:
            value = Evaluator(self.tokens, self.angle, self.ans, self.memory).evaluate()
        except CalcError as exc:
            self.error, self.result = str(exc), None
            return
        except RecursionError:
            self.error, self.result = SYNTAX_ERROR, None
            return
        self.result, self.error = value, ""
        if store:
            self.ans = value
            self.history.append((self.expression, format_number(value)))
            del self.history[:-20]
