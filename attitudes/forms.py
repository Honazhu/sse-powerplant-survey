"""Reject ambiguous/invalid payloads before native oTree form population."""
from .questions import RAW_FIELDS, SCORES


def prepare_attitude_fields(form):
    allowed = {str(value) for value in SCORES}
    for name in RAW_FIELDS:
        field = getattr(form, name)
        raw = field.raw_data or []
        if len(raw) != 1 or raw[0] not in allowed:
            field.process_errors = ['Please choose one of the five responses.']
