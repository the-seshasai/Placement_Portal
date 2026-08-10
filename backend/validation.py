"""Small shared backend validation helpers (used by auth now, by the
company/student write endpoints in later steps too)."""

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CURRENT_YEAR_SPAN = (2000, 2100)


def is_valid_email(email):
    return bool(email) and bool(EMAIL_RE.match(email))


def is_valid_password(password):
    return bool(password) and len(password) >= 8


def is_valid_cgpa(cgpa):
    try:
        cgpa = float(cgpa)
    except (TypeError, ValueError):
        return False
    return 0 <= cgpa <= 10


def is_valid_grad_year(year):
    try:
        year = int(year)
    except (TypeError, ValueError):
        return False
    return CURRENT_YEAR_SPAN[0] <= year <= CURRENT_YEAR_SPAN[1]
