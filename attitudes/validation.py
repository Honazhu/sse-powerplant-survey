"""Shared server/export validation. Zero is a valid ordinal category."""
from .questions import DK_CODE


def response_error(value, question):
    if type(value) is not int or value not in [code for code, _ in question['choices']]:
        return 'Please select one of the listed responses.'


def score_response(value, question):
    if value is None:
        return None, None
    if response_error(value, question):
        raise ValueError(f"Invalid response for {question['field']}.")
    return (None, 1) if value == DK_CODE else (value, 0)
