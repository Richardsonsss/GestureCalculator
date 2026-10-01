import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
from engine import MATH_ERROR, SYNTAX_ERROR, Calculator, format_fraction, format_number  # noqa: E402


def run(keys, angle="DEG"):
    calc = Calculator()
    calc.angle = angle
    for key in keys.split():
        calc.press(key)
    return calc


def value(keys, angle="DEG"):
    calc = run(keys + " eq", angle)
    assert not calc.error, calc.error
    return calc.result


@pytest.mark.parametrize("keys, expected", [
    ("1 2 add 5", 17),
    ("2 add 3 mul 4", 14),
    ("lp 2 add 3 rp mul 4", 20),
    ("1 0 div 4", 2.5),
    ("2 pow 3 pow 2", 512),                # right associative
    ("sub 2 sq", -4),                      # unary minus binds weaker than a power
    ("lp sub 2 rp sq", 4),
    ("2 pow sub 1", 0.5),
    ("2 pi", 2 * math.pi),                 # implicit multiplication
    ("3 lp 4 add 1 rp", 15),
    ("2 sin 3 0 rp", 1),
    ("sin 3 0", 0.5),                      # missing ')' at the end is allowed
    ("cos 6 0 rp", 0.5),
    ("tan 4 5 rp", 1),
    ("sin 1 8 0 rp", 0),
    ("asin dot 5 rp", 30),
    ("sqrt 1 6 rp add cbrt 2 7 rp", 7),
    ("cbrt sub 8 rp", -2),
    ("log 1 0 0 0 rp", 3),
    ("ln e rp", 1),
    ("pow10 3 rp", 1000),
    ("expe 0 rp", 1),
    ("5 fact", 120),
    ("0 fact", 1),
    ("5 0 percent", 0.5),
    ("4 inv", 0.25),
    ("3 cube", 27),
    ("abs sub 7 rp", 7),
    ("5 npr 2", 20),
    ("5 ncr 2", 10),
    ("1 dot 5 exp 3", 1500),
    ("2 exp sub 2", 0.02),
    ("sinh 0 rp add cosh 0 rp", 1),
])
def test_values(keys, expected):
    assert value(keys) == pytest.approx(expected, abs=1e-12)


def test_angle_modes():
    assert value("sin pi div 2 rp", "RAD") == pytest.approx(1)
    assert value("sin 1 0 0 rp", "GRA") == pytest.approx(1)
    assert value("acos 0 rp", "RAD") == pytest.approx(math.pi / 2)


@pytest.mark.parametrize("keys, error", [
    ("1 div 0", MATH_ERROR),
    ("sqrt sub 1 rp", MATH_ERROR),
    ("log 0 rp", MATH_ERROR),
    ("tan 9 0 rp", MATH_ERROR),
    ("asin 2 rp", MATH_ERROR),
    ("7 0 fact", MATH_ERROR),
    ("2 dot 5 fact", MATH_ERROR),
    ("3 ncr 5", MATH_ERROR),
    ("9 exp 9 9 mul 9 exp 9 9", MATH_ERROR),
    ("1 add", SYNTAX_ERROR),
    ("mul 3", SYNTAX_ERROR),
    ("rp 3", SYNTAX_ERROR),
    ("1 dot 2 dot 3", SYNTAX_ERROR),
    ("lp rp", SYNTAX_ERROR),
])
def test_errors(keys, error):
    assert run(keys + " eq").error == error


def test_answer_and_continuation():
    calc = run("6 mul 7 eq")
    assert calc.result == 42
    calc.press("add")           # an operator continues from the answer
    calc.press("8")
    assert calc.expression == "Ans+8"
    calc.press("eq")
    assert calc.result == 50
    calc.press("3")             # a digit starts a new expression
    assert calc.expression == "3"
    for key in "mul ans eq".split():
        calc.press(key)
    assert calc.result == 150


def test_delete_and_clear():
    calc = run("1 2 sin del del")
    assert calc.expression == "1"
    calc = run("1 div 0 eq")
    assert calc.error == MATH_ERROR
    calc.press("del")           # back to editing
    assert calc.error == "" and calc.expression == "1÷0"
    calc.press("ac")
    assert calc.expression == "" and calc.result_text == ""


def test_memory():
    calc = run("5 mplus ac 3 mminus ac mr eq")
    assert calc.result == 2
    calc.press("mc")
    assert calc.memory == 0


def test_fraction_toggle_and_formatting():
    calc = run("3 div 4 eq")
    assert calc.result_text == "0.75"
    calc.press("sd")
    assert calc.result_text == "3/4"
    assert format_fraction(math.pi) is None
    assert format_number(1 / 3) == "0.3333333333"
    assert format_number(-2.5) == "−2.5"
    assert format_number(1e12) == "1×10^12"
    assert format_number(1.5e-12) == "1.5×10^−12"
    assert format_number(12345678901234) == "1.23456789×10^13"
    assert format_number(0.1 + 0.2) == "0.3"


def test_shift_is_one_shot_and_drg_cycles():
    calc = Calculator()
    calc.press("shift")
    assert calc.shift
    calc.press("1")
    assert not calc.shift
    calc.press("drg")
    assert calc.angle == "RAD"
    calc.press("drg")
    calc.press("drg")
    assert calc.angle == "DEG"


def test_memory_save_and_recall():
    calc = run("6 mul 7 eq msave")           # after a result: save it
    assert calc.memory == 42 and calc.result == 42
    calc = run("6 mul 7 msave")              # an unfinished expression is worked out first
    assert calc.memory == 42 and calc.result == 42
    calc = run("6 mul 7 eq msave 1 0 add mr eq")
    assert calc.expression == "10+M" and calc.result == 52
    calc = run("1 div 0 msave")              # an error saves nothing
    assert calc.memory == 0
