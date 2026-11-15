"""Transform a native oTree respondent-wide CSV; never modifies the source."""
import argparse
import csv
import importlib
import sys
import types
from pathlib import Path

# Import pure helpers without executing random_matrix's oTree model module.
package = types.ModuleType('_survey_dce_export')
package.__path__ = [str(Path(__file__).resolve().parents[1] / 'random_matrix')]
sys.modules.setdefault('_survey_dce_export', package)
exports = importlib.import_module('_survey_dce_export.exports')
attitudes_package = types.ModuleType('_survey_attitudes_export')
attitudes_package.__path__ = [str(Path(__file__).resolve().parents[1] / 'attitudes')]
sys.modules.setdefault('_survey_attitudes_export', attitudes_package)
attitude_exports = importlib.import_module('_survey_attitudes_export.exports')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    with args.input.open(newline='', encoding='utf-8-sig') as handle:
        native = list(csv.DictReader(handle))
    records = list(exports.records_from_native(native))
    attitudes = attitude_exports.records_from_native(native)
    if (args.output_dir / 'attitudes_wide.csv').exists():
        raise FileExistsError('Choose a new export directory; existing exports are never overwritten.')
    result = exports.write_formats(records, args.output_dir)
    exports.write_csv(args.output_dir / 'attitudes_wide.csv', attitudes, attitude_exports.EXPORT_FIELDS)
    print(dict(result, attitude_rows=len(attitudes)))


if __name__ == '__main__':
    main()
