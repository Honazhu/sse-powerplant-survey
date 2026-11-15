"""Skip only tests whose excluded historical local CSV fixtures are missing."""
from pathlib import Path
import pytest

_ROOT = Path(__file__).resolve().parents[1] / 'data' / 'synthetic'
_PARAMETRIZED = {
    'test_historical_preview_never_becomes_v3_or_neutral',
    'test_historical_exports_do_not_invent_treatment_metadata',
    'test_historical_csv_missing_wording_stays_missing',
    'test_actual_versioned_exports_retain_their_version',
}
_FIXED = {
    'test_historical_v23_dispatch_and_mixed_version_refusal': 'v2_2b_browser_1794733130242432000',
    'test_export_preserves_explicit_historical_version': 'v2_1_browser_1794599108416794000',
}


def pytest_collection_modifyitems(items):
    for item in items:
        name = item.originalname
        params = getattr(getattr(item, 'callspec', None), 'params', {})
        if name in _PARAMETRIZED or name == 'test_actual_v30_exports_are_lossless_and_never_relabelled':
            release = params.get('release')
        elif name in _FIXED:
            release = _FIXED[name]
        else:
            continue
        required = ['all_apps_wide.csv']
        if name == 'test_actual_v30_exports_are_lossless_and_never_relabelled':
            required.append('attitudes_wide.csv')
        if release is None or any(not (_ROOT / release / f).is_file() for f in required):
            item.add_marker(pytest.mark.skip(reason='Historical local CSV fixtures are excluded from the release; run this case in an isolated external harness.'))
