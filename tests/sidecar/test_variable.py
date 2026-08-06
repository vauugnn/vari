"""Variable name validation (PHASE-1 section 2)."""
import pytest

from sidecar.data.variable import NameError_, validate_name


def test_accepts_normal():
    assert validate_name("age") == "age"
    assert validate_name("Q1_total") == "Q1_total"


def test_rejects_leading_digit():
    with pytest.raises(NameError_):
        validate_name("1var")


def test_rejects_reserved():
    for kw in ("ALL", "and", "By", "with", "TO"):
        with pytest.raises(NameError_):
            validate_name(kw)


def test_rejects_duplicate_case_insensitive():
    with pytest.raises(NameError_):
        validate_name("Age", existing={"age"})


def test_rejects_over_64_bytes():
    with pytest.raises(NameError_):
        validate_name("a" * 65)


def test_rejects_trailing_period():
    with pytest.raises(NameError_):
        validate_name("var.")


def test_case_preserved():
    assert validate_name("MyVar", existing={"other"}) == "MyVar"
