import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
from engine import INSERT, Calculator  # noqa: E402
from operators import CODES, GROUPS, CodeEntry  # noqa: E402

OTHER_KEYS = {"drg", "sd", "msave"}


def test_every_code_is_two_different_digits_and_a_known_key():
    assert len({key for key, _ in CODES.values()}) == len(CODES)      # no operator twice
    for code, (key, label) in CODES.items():
        assert len(code) == 2 and code.isdigit() and code[0] != code[1], code
        assert key in INSERT or key in OTHER_KEYS, key
        assert label
    assert {code[0] for code in CODES} == {tens for tens, _ in GROUPS}


def test_every_operator_of_the_engine_has_a_code():
    digits_and_dot = {str(d) for d in range(10)} | {"dot"}
    assert set(INSERT) - digits_and_dot <= {key for key, _ in CODES.values()}


def test_tens_then_units():
    entry = CodeEntry()
    assert entry.feed("1", 0.0) is None and entry.tens == "1"
    assert entry.feed("0", 1.0) == ("10", "sin", "sin")
    assert entry.tens is None
    assert entry.feed("0", 2.0) is None
    assert entry.feed("1", 3.0) == ("01", "add", "+")


def test_unknown_code_and_timeout():
    entry = CodeEntry(timeout=6.0)
    entry.feed("1", 0.0)
    assert entry.feed("1", 1.0) == ("11", None, None)                 # not a code
    entry.feed("9", 10.0)
    assert not entry.tick(15.0) and entry.tens == "9"
    assert entry.tick(16.5) and entry.tens is None                     # dropped after the timeout
    entry.feed("2", 20.0)
    entry.cancel()
    assert entry.tens is None


def test_codes_drive_the_calculator():
    calc = Calculator()

    def code(c):
        calc.press(CODES[c][0])

    code("10")                      # sin(
    calc.press("3"), calc.press("0")
    code("06")                      # )
    code("01")                      # +
    calc.press("5")
    calc.press("eq")
    assert calc.expression == "sin(30)+5" and calc.result == 5.5
    code("38")                      # M save
    assert calc.memory == 5.5
    code("40")                      # DEG -> RAD
    assert calc.angle == "RAD"
