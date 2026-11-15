"""Validate and left-join DCE tasks, Household and V3 attitudes by native codes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

import pandas as pd

# Reuse the existing pure export adapters; never initialize an oTree database.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.export_dce import exports as dce_exports, attitude_exports

KEYS = attitude_exports.KEYS
TASK_KEYS = KEYS + ['task_index']
HOUSEHOLD_FIELDS = ['age_group', 'rent_status', 'monthly_rent_sek', 'income_thousand_sek',
                    'income_sek', 'income_not_disclosed', 'previous_power_plant_exposure']
PARTICIPANT_FIELDS = {'participant.eligible': 'eligible', 'participant.exit_reason': 'exit_reason',
                      'participant.household_complete': 'household_complete',
                      'participant.finished': 'survey_completed'}


def read_csv(path):
    # Leading zeros and literal NA-like codes are identifiers, not numbers/missing.
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        header = next(csv.reader(handle))
    if len(header) != len(set(header)):
        raise ValueError('CSV contains duplicate column names.')
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False)


def require_unique(frame, keys, label):
    if not frame.columns.is_unique or not set(keys).issubset(frame.columns):
        raise ValueError(f'{label}: missing or duplicate key columns.')
    for name in keys:
        if not frame[name].map(lambda v: isinstance(v, str) and bool(v) and v.strip() == v).all():
            raise ValueError(f'{label}: blank or non-string join key.')
    if frame.duplicated(keys).any():
        raise ValueError(f'{label}: duplicate keys would expand or misidentify rows.')


def key_list(frame, columns=KEYS):
    return frame[columns].drop_duplicates().to_dict('records')


def merge_datasets(native, difference, attitudes):
    """Return a validated task-left-join and its audit, without modifying inputs."""
    native = native.copy()
    difference = difference.copy()
    attitudes = attitudes.copy()
    require_unique(native, ['session.code', 'participant.code'], 'Native')
    require_unique(difference, TASK_KEYS, 'DCE difference')
    require_unique(attitudes, KEYS, 'Attitudes')
    native_rows = native.to_dict('records')
    canonical_attitudes = attitude_exports.records_from_native(native_rows)
    checked_attitudes = attitude_exports.validate_wide(attitudes.to_dict('records'))
    canonical_map = {attitude_exports.participant_key(row): row for row in canonical_attitudes}
    for row in checked_attitudes:
        key = attitude_exports.participant_key(row)
        if key not in canonical_map or row != canonical_map[key]:
            raise ValueError('Attitudes do not match the supplied native export/version.')

    _, _, canonical_difference = dce_exports.reshape(dce_exports.records_from_native(native_rows))
    expected = pd.DataFrame([dce_exports.normalized(row) for row in canonical_difference])
    if set(difference.columns) != set(expected.columns):
        raise ValueError('DCE difference columns differ from the validated native export.')
    actual_index = difference.set_index(TASK_KEYS).sort_index()
    expected_index = expected.set_index(TASK_KEYS).sort_index()
    if not actual_index.equals(expected_index[actual_index.columns]):
        raise ValueError('DCE differences, keys, versions or row counts disagree with native data.')

    required = ['session.code', 'participant.code', *PARTICIPANT_FIELDS,
                *['household.1.player.' + name for name in HOUSEHOLD_FIELDS]]
    if not set(required).issubset(native.columns):
        raise ValueError('Native export lacks required Household/status columns.')
    household = native[required].rename(columns={
        'session.code': 'session_code', 'participant.code': 'participant_code', **PARTICIPANT_FIELDS,
        **{'household.1.player.' + name: name for name in HOUSEHOLD_FIELDS}})
    # Flow provenance is absent for historical releases; never backfill it.
    flow = native.get('eligibility.1.player.survey_flow_version', pd.Series('', index=native.index))
    configured_flow = native.get('session.config.survey_flow_version', pd.Series('', index=native.index))
    if not flow.equals(configured_flow) or not flow.isin(['', 'V3.3']).all():
        raise ValueError('Survey flow version differs from native session provenance.')
    current_attitudes = native.get('attitudes.1.player.attitudes_version', pd.Series('', index=native.index)).eq('V3.3')
    if not current_attitudes.equals(flow.eq('V3.3')):
        raise ValueError('V3.3 attitudes require matching V3.3 survey flow provenance.')
    household['survey_flow_version'] = flow
    merged = difference.merge(household, on=KEYS, how='left', validate='many_to_one',
                              indicator='household_match', sort=False)
    attitude_fields = [f for f in attitude_exports.EXPORT_FIELDS if f not in ('study_mode', 'data_class')]
    merged = merged.merge(attitudes[attitude_fields], on=KEYS, how='left',
                          validate='many_to_one', indicator='attitudes_match', sort=False)
    if len(merged) != len(difference) or merged.duplicated(TASK_KEYS).any():
        raise ValueError('Merge changed DCE task cardinality.')
    missing = merged['attitudes_match'] == 'left_only'
    merged.loc[missing, 'attitudes_status'] = 'missing_export_row'
    task_people = difference[KEYS].drop_duplicates()
    unused = attitudes[KEYS].merge(task_people, on=KEYS, how='left', indicator=True)
    audit = dict(
        pipeline_version='V3.3', join_keys=KEYS, task_keys=TASK_KEYS,
        cardinalities={'household': 'many_to_one', 'attitudes': 'many_to_one'},
        input_rows={'native': len(native), 'dce_difference': len(difference), 'attitudes': len(attitudes)},
        output_rows=len(merged), duplicate_keys={'native': 0, 'dce_difference': 0, 'attitudes': 0, 'output': 0},
        unmatched_attitude_participants=key_list(merged[missing]),
        unmatched_household_participants=key_list(merged[merged['household_match'] == 'left_only']),
        unused_attitude_participants=key_list(unused[unused['_merge'] == 'left_only']),
        invalid_scale_values=0, native_provenance_and_difference_agreement=True,
        data_classes=sorted(set(difference['data_class'])),
        housing_wording_versions=sorted(set(difference['wording_version'])),
        treatment_design_versions=sorted(set(difference['treatment_design_version'])),
        attitudes_versions=sorted(set(attitudes['attitudes_version'])),
    )
    # Nullable integers preserve true zero and avoid converting large SEK amounts through floats.
    integer_fields = ['task_index', 'coal', 'chosen_near20', 'chose_A', 'tasks_answered',
                      'task_count', 'module_started', 'module_completed', 'task_displayed',
                      'eligible', 'household_complete', 'survey_completed', 'rent_status',
                      'monthly_rent_sek', 'income_thousand_sek', 'income_sek', 'income_not_disclosed',
                      'previous_power_plant_exposure', 'attitudes_completed',
                      *attitude_exports.RAW_FIELDS, *attitude_exports.SCORE_FIELDS, *attitude_exports.DK_FIELDS]
    if set(difference['survey_version']) == {'V2.4'}:
        integer_fields += ['oil', 'chosen_distance_km', 'chosen_rent_sek', 'chosen_far', 'premium_sek',
                           'base_rent_sek', 'side_swapped', 'task_completed', 'delta_far', 'delta_far_x_oil']
    else:
        integer_fields += ['block_id']
    for name in integer_fields:
        if name not in merged.columns:
            continue
        values = []
        for value in merged[name]:
            if pd.isna(value) or value == '':
                values.append(None)
            elif isinstance(value, str) and re.fullmatch(r'-?(0|[1-9][0-9]*)', value):
                values.append(int(value))
            else:
                raise ValueError(f'Invalid integer in {name}.')
        merged[name] = pd.array(values, dtype='Int64')
    for name in ('delta_rent_1000', 'delta_size_m2', 'delta_near20', 'delta_near20_coal',
                 'task_duration_s', 'attitudes_submitted_at'):
        if name not in merged.columns:
            continue
        merged[name] = pd.array([None if pd.isna(v) or v == '' else float(v) for v in merged[name]], dtype='Float64')
    merged['dce_completed'] = merged['module_completed']
    merged['household_completed'] = merged['household_complete']
    audit['survey_flow_versions'] = sorted(set(merged['survey_flow_version']))
    audit['missing_household_participants'] = int(merged.drop_duplicates(KEYS)['household_complete'].eq(0).sum())
    audit['missing_score_task_rows'] = {name: int(merged[name].isna().sum()) for name in attitude_exports.SCORE_FIELDS}
    people = merged.drop_duplicates(KEYS)
    audit['missing_score_participants'] = {name: int(people[name].isna().sum()) for name in attitude_exports.SCORE_FIELDS}
    audit['attitudes_status_participants'] = people['attitudes_status'].value_counts().to_dict()
    return merged, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--dce-difference', type=Path, required=True)
    parser.add_argument('--attitudes', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    sources = {'native': args.native, 'dce_difference': args.dce_difference, 'attitudes': args.attitudes}
    fingerprints = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()}
    merged, audit = merge_datasets(*[read_csv(path) for path in sources.values()])
    audit['input_sha256'] = fingerprints
    destination = args.output_dir
    destination.mkdir(parents=True, exist_ok=True)
    if any((destination / name).exists() for name in ('analysis_merged.csv', 'merge_audit.json')):
        raise FileExistsError('Choose a new output directory; merged files are never overwritten.')
    merged.to_csv(destination / 'analysis_merged.csv', index=False, mode='x', na_rep='')
    with (destination / 'merge_audit.json').open('x') as handle:
        json.dump(audit, handle, indent=2)
        handle.write('\n')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
