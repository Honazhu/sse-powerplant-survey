"""Pure question-level rules, imported without initializing oTree's database."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('household_validation', Path(__file__).resolve().parents[1] / 'household/validation.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


@pytest.mark.parametrize('raw', ['', ' ', 'abc', '-3', '1.1', '1e3', '+4', ' 4', '4 ', '１', '1_000', '9' * 10000])
def test_q3_q4_reject_non_integer_lexemes(raw):
    assert v.rent_error(raw, True) == v.NUMBER_ERROR
    assert v.income_error(raw, False) == v.NUMBER_ERROR


def test_q3_positive_only_and_inactive_ignored():
    assert v.rent_error('6500', True) is None
    assert v.rent_error('0', True) == v.NUMBER_ERROR
    assert v.rent_error('stale answer', False) is None


def test_q4_zero_refusal_and_after_tax_conversion():
    assert v.income_error('0', False) is None
    assert v.income_in_sek(0) == 0
    assert v.income_in_sek(25) == 25000
    assert v.income_error('stale answer', True) is None
    assert v.income_in_sek(None) is None


def test_storage_boundary_not_research_threshold():
    assert v.rent_error(str(v.MAX_INTEGER), True) is None
    assert v.rent_error(str(v.MAX_INTEGER + 1), True) == v.NUMBER_ERROR
    assert v.income_error(str(v.MAX_INTEGER // 1000), False) is None
    assert v.income_error(str(v.MAX_INTEGER // 1000 + 1), False) == v.NUMBER_ERROR
