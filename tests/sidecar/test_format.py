"""Format rendering, SPSS rounding, and input round trips (PHASE-1 section 1)."""
import pytest

from sidecar.data.format import Format


def test_parse():
    assert Format.parse("F8.2") == Format("F", 8, 2)
    assert Format.parse("A10") == Format("A", 10, 0)
    assert Format.parse("DOLLAR12.2") == Format("DOLLAR", 12, 2)
    assert Format.parse("date11").type == "DATE"


def test_f_keeps_leading_zero():
    # F format keeps its leading zero; suppression is output-cell-specific.
    assert Format("F", 8, 2).render(0.5) == "0.50"
    assert Format("F", 8, 2).render(-0.5) == "-0.50"


@pytest.mark.parametrize(
    "value,expected",
    [(2.5, "3"), (3.5, "4"), (-2.5, "-3"), (0.5, "1"), (1.4, "1")],
)
def test_round_half_away_from_zero(value, expected):
    assert Format("F", 8, 0).render(value) == expected


def test_comma_grouping():
    assert Format("COMMA", 12, 1).render(1234567.5) == "1,234,567.5"


def test_dot_european():
    assert Format("DOT", 10, 1).render(1234.5) == "1.234,5"


def test_dollar():
    assert Format("DOLLAR", 12, 2).render(1234.5) == "$1,234.50"


def test_pct():
    assert Format("PCT", 6, 1).render(12.5) == "12.5%"


def test_string_passthrough():
    assert Format("A", 8).render("hi") == "hi"


def test_sysmis_renders_dot():
    assert Format("F", 8, 2).render(None) == "."
    assert Format("F", 8, 2).render(float("nan")) == "."


@pytest.mark.parametrize(
    "fmt,text",
    [("F8.2", 3.14), ("COMMA12.2", 1234.5), ("DOLLAR12.2", 1234.5), ("PCT6.1", 12.5), ("DOT10.1", 1234.5)],
)
def test_input_round_trip(fmt, text):
    f = Format.parse(fmt)
    assert f.parse_input(f.render(text)) == text


def test_string_input_round_trip():
    f = Format("A", 8)
    assert f.parse_input(f.render("word")) == "word"


def test_to_spss():
    assert Format("F", 8, 2).to_spss() == "F8.2"
    assert Format("A", 10, 0).to_spss() == "A10"
