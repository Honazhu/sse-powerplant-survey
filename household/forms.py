"""Small oTree 6.0.15 / WTForms adapter for strict conditional integer inputs.

Native IntegerField parses before Page.error_message; it accepts '+1' and
whitespace and rejects inactive malformed values too early. Retain native
model fields, form rendering, validation and population; normalize only these
two bound fields. No framework patch or extra answer-storage fields.
"""
from .validation import rent_error, income_error


def prepare_numeric_fields(form):
    rules = [
        (form.monthly_rent_sek, form.rent_status.data is True,
         lambda raw: rent_error(raw, form.rent_status.data)),
        (form.income_thousand_sek, not form.income_not_disclosed.data,
         lambda raw: income_error(raw, form.income_not_disclosed.data)),
    ]
    for field, active, validate in rules:
        raw_values = field.raw_data or []
        raw = raw_values[0] if len(raw_values) == 1 else ''
        error = validate(raw) if active else None
        # SQLAlchemy adds Optional for nullable columns; it would erase a
        # required conditional blank error. These two fields use our rules.
        field.validators = []
        field.process_errors = [error] if error else []
        if not active:
            field.data = None
            field.raw_data = []
        elif not error:
            field.data = int(raw.lstrip('0') or '0')
