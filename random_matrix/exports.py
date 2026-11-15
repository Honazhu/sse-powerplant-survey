"""Version dispatch. Never combine incompatible housing designs in one analysis file."""
from . import exports_v24 as current
from .legacy_v23 import exports as historical
from .exports_v24 import (TASK_EXPORT_FIELDS, TASK_FIELDS, MODULE_FIELDS, FACILITY_MODULE_FIELDS,
                          task_record, normalized, write_csv)


def adapter(versions):
    versions = set(versions)
    if versions == {'V2.4'}:
        return current
    if versions and versions <= {'V2.0', 'V2.2b'}:
        return historical
    raise ValueError('Unsupported or mixed housing versions; export V2.4 and historical designs separately.')


def records_from_native(rows):
    rows = list(rows)
    selected = adapter(row.get('random_matrix.1.player.survey_version') for row in rows)
    return selected.records_from_native(rows)


def reshape(records):
    records = list(records)
    return adapter(row.get('survey_version') for row in records).reshape(records)


def write_formats(records, destination):
    records = list(records)
    return adapter(row.get('survey_version') for row in records).write_formats(records, destination)
