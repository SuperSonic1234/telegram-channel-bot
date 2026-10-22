import math

import pytest

from utils.validation import parse_finite_number, safe_html


def test_parse_finite_number():
    assert parse_finite_number("1 234,5") == 1234.5
    for value in (None, "nan", "inf", "-inf", "text"):
        with pytest.raises(ValueError):
            parse_finite_number(value)


def test_safe_html():
    assert safe_html("<b>&") == "&lt;b&gt;&amp;"
    assert math.isfinite(parse_finite_number("10"))
