"""Question-specific numeric rules, independent of HTML and oTree."""
import re

NUMBER_ERROR = 'Please enter a valid number.'
# Storage safety only; not an economic eligibility limit or income band.
MAX_INTEGER = 2**63 - 1


def integer_error(raw, minimum, maximum=MAX_INTEGER):
    if not isinstance(raw, str) or not re.fullmatch(r'[0-9]+', raw):
        return NUMBER_ERROR
    # Bound length before int conversion (also handles maliciously large inputs).
    digits = raw.lstrip('0') or '0'
    if len(digits) > len(str(maximum)):
        return NUMBER_ERROR
    value = int(digits)
    if not minimum <= value <= maximum:
        return NUMBER_ERROR


def rent_error(raw, rent_status):
    if rent_status is True:
        return integer_error(raw, minimum=1)


def income_error(raw, not_disclosed):
    if not not_disclosed:
        return integer_error(raw, minimum=0, maximum=MAX_INTEGER // 1000)


def income_in_sek(thousands):
    return None if thousands is None else thousands * 1000
