import math
from html import escape


def safe_html(value: object) -> str:
    return escape(str(value), quote=False)


def parse_finite_number(text: str | None) -> float:
    if text is None:
        raise ValueError("Text value is required")
    value = float(text.replace(",", ".").replace(" ", ""))
    if not math.isfinite(value):
        raise ValueError("Number must be finite")
    return value
