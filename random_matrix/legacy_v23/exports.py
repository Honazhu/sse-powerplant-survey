"""V2 CSV transforms; standard library only, with explicit missing outcomes."""
import csv
import json
from pathlib import Path
from .facility_design import (DESIGN_HASH, NUMERIC_MATRIX_HASH, NUMERIC_MATRIX_VERSION,
                              TREATMENT_DESIGN_VERSION, SURVEY_VERSION, validate_assignment)

PROFILE_FIELDS = ('size_m2', 'distance_km', 'rent_sek_month', 'near20', 'facility_type')
FACILITY_MODULE_FIELDS = ['numeric_matrix_version', 'numeric_matrix_hash', 'treatment_design_version',
                          'facility_assignment_seed', 'facility_type_assignment']
MODULE_FIELDS = [
    'participant_code', 'session_code', 'study_mode', 'data_class', 'survey_version', 'wording_version',
    'design_version', 'design_hash', 'block_id', 'task_count', 'tasks_answered',
    'module_started', 'module_completed', 'allocation_index', 'random_seed',
    'assignment_method', 'display_version', 'choice_set_order_json', 'side_allocation_json',
    'assignment_json',
] + FACILITY_MODULE_FIELDS
TASK_FIELDS = ['task_index', 'choice_set_id', 'presentation_order', 'near_side', 'facility_type'] + [
    f'{side}_{field}' for side in ('A', 'B') for field in PROFILE_FIELDS
] + ['choice', 'chosen_near20', 'task_displayed', 'task_started_at', 'task_submitted_at',
     'task_duration_s', 'task_timing_status']
TASK_EXPORT_FIELDS = MODULE_FIELDS + TASK_FIELDS


def task_record(player):
    first = player.in_round(1)
    if (player.field_maybe_none('wording_version') or '') != (first.field_maybe_none('wording_version') or ''):
        raise ValueError('Inconsistent wording version across participant rounds.')
    row = {name: first.field_maybe_none(name) for name in MODULE_FIELDS[4:]}
    row.update(participant_code=player.participant.code, session_code=player.session.code,
               study_mode=player.session.config['study_mode'], data_class=player.session.config['data_class'])
    row.update({name: player.field_maybe_none(name) for name in TASK_FIELDS})
    row['task_index'] = player.round_number
    return row


def records_from_native(rows):
    """Read native respondent-wide exports without opening any database."""
    for source in rows:
        prefix = 'random_matrix.1.player.'
        survey = source.get(prefix + 'survey_version')
        if survey not in ('V2.0', SURVEY_VERSION):
            raise ValueError('Expected a supported four-round native export; do not mix legacy designs.')
        # Historical exports have no wording column. Missing stays missing;
        # never infer a wording version from the unchanged design version.
        module = {name: source.get(prefix + name, '') if name in ['wording_version', *FACILITY_MODULE_FIELDS] else source[prefix + name]
                  for name in MODULE_FIELDS[4:]}
        module.update(participant_code=source['participant.code'], session_code=source['session.code'],
                      study_mode=source['session.config.study_mode'], data_class=source['session.config.data_class'])
        for index in range(1, 5):
            task_prefix = f'random_matrix.{index}.player.'
            if source.get(task_prefix + 'wording_version', '') != module['wording_version']:
                raise ValueError('Inconsistent wording version across participant rounds.')
            if survey == SURVEY_VERSION:
                for name in ('numeric_matrix_version', 'numeric_matrix_hash', 'treatment_design_version', 'survey_version'):
                    if source.get(task_prefix + name) != module[name]:
                        raise ValueError('Inconsistent treatment provenance across participant rounds.')
                if task_prefix + 'facility_type' not in source:
                    raise ValueError('Current native export lacks facility_type.')
            yield dict(module, **{name: source.get(task_prefix + name, '') if name == 'facility_type' else source[task_prefix + name]
                                  for name in TASK_FIELDS if name != 'task_index'},
                       task_index=index)


def normalized(row):
    return {key: '' if value is None else str(int(value)) if isinstance(value, bool) else str(value)
            for key, value in row.items()}


def reshape(records):
    """Preserve all four planned rows, including assigned-but-unseen tasks."""
    participants, long, difference = {}, [], []
    seen = set()
    for raw in records:
        row = normalized(raw)
        row.setdefault('wording_version', '')  # Older custom task exports.
        for field in FACILITY_MODULE_FIELDS + ['facility_type']:
            row.setdefault(field, '')  # Never backfill new metadata on historical records.
        key = (row['session_code'], row['participant_code'])
        index = int(row['task_index'])
        if index not in range(1, 5) or (*key, index) in seen:
            raise ValueError('Duplicate or invalid participant/task key.')
        seen.add((*key, index))
        module = {name: row[name] for name in MODULE_FIELDS}
        wide = participants.setdefault(key, dict(module))
        if any(wide[name] != module[name] for name in MODULE_FIELDS):
            raise ValueError('Inconsistent participant metadata across tasks.')
        choice = row['choice']
        if choice not in ('', 'A', 'B'):
            raise ValueError('Choice must be A, B or missing.')
        if row['assignment_json']:
            assignment = json.loads(row['assignment_json'])
            if (assignment['session_code'], assignment['participant_code']) != key:
                raise ValueError('Snapshot provenance mismatch.')
            task = assignment['tasks'][index - 1]
            if row['survey_version'] == SURVEY_VERSION:
                validate_assignment(assignment)
                for field in ['design_version', 'design_hash', *FACILITY_MODULE_FIELDS]:
                    if row[field] != str(assignment[field]):
                        raise ValueError('Treatment metadata differs from persisted assignment.')
                if row['facility_type'] != task['facility_type']:
                    raise ValueError('Task facility differs from persisted assignment.')
            elif row['facility_type'] or any(row[f] for f in FACILITY_MODULE_FIELDS):
                raise ValueError('Historical export has unsupported new treatment metadata.')
            for name in ('choice_set_id', 'presentation_order', 'near_side'):
                if row[name] != str(task[name]):
                    raise ValueError('Task metadata differs from persisted display.')
            for side in ('A', 'B'):
                for name in PROFILE_FIELDS:
                    if row[f'{side}_{name}'] != str(task[side][name]):
                        raise ValueError('Export attributes differ from persisted display.')
        elif row['choice_set_id'] or choice:
            raise ValueError('Task/choice without an assignment.')
        if row['survey_version'] == SURVEY_VERSION:
            if (row['numeric_matrix_version'], row['numeric_matrix_hash'], row['treatment_design_version']) != (
                    NUMERIC_MATRIX_VERSION, NUMERIC_MATRIX_HASH, TREATMENT_DESIGN_VERSION):
                raise ValueError('Current export has missing or invalid treatment provenance.')
            if not row['assignment_json'] and (row['facility_type'] or row['facility_assignment_seed'] or row['facility_type_assignment']):
                raise ValueError('Unassigned task has facility assignment data.')
        if choice:
            if row['task_displayed'] != '1' or not row['task_submitted_at']:
                raise ValueError('Choice without a displayed/submitted task.')
            if row['chosen_near20'] != row[f'{choice}_near20']:
                raise ValueError('Chosen proximity does not match choice.')
        elif row['chosen_near20'] or row['task_submitted_at'] or row['task_duration_s']:
            raise ValueError('Missing choice must not have completed-task values.')
        wide.update({f'task{index}_{name}': row[name] for name in TASK_FIELDS})
        common = dict(module, **{name: row[name] for name in TASK_FIELDS if not name.startswith(('A_', 'B_'))})
        for side in ('A', 'B'):
            long.append(dict(common, apartment=side, chosen='' if not choice else int(choice == side),
                             **{name: row[f'{side}_{name}'] for name in PROFILE_FIELDS}))
        diff = dict(common, chose_A='' if not choice else int(choice == 'A'))
        for field, name, scale in [('rent_sek_month', 'delta_rent_1000', 1000),
                                    ('size_m2', 'delta_size_m2', 1), ('near20', 'delta_near20', 1)]:
            a, b = row[f'A_{field}'], row[f'B_{field}']
            diff[name] = (int(a) - int(b)) / scale if a != '' and b != '' else ''
        diff['coal'] = int(row['facility_type'] == 'coal') if row['facility_type'] in ('nuclear', 'coal') else ''
        diff['delta_near20_coal'] = diff['delta_near20'] * diff['coal'] if diff['coal'] != '' and diff['delta_near20'] != '' else ''
        difference.append(diff)
    for key, row in participants.items():
        if sum(s[:2] == key for s in seen) != 4:
            raise ValueError('Export requires all four task rows per participant, including missing outcomes.')
        answered = sum(row[f'task{i}_choice'] in ('A', 'B') for i in range(1, 5))
        if answered != int(row['tasks_answered']) or (row['module_completed'] == '1') != (answered == 4):
            raise ValueError('Module completion does not match saved choices.')
    return list(participants.values()), long, difference


def write_csv(path, rows, fields=None):
    rows = list(rows)
    if not rows and not fields:
        raise ValueError('Cannot infer columns from an empty export.')
    with Path(path).open('x', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_formats(records, destination):
    records = list(records)
    wide, long, difference = reshape(records)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('dce_tasks.csv', 'dce_wide.csv', 'dce_long.csv', 'dce_difference.csv'):
        if (destination / name).exists():
            raise FileExistsError('Choose a new export directory; existing exports are never overwritten.')
    for name, rows in [('tasks', records), ('wide', wide), ('long', long), ('difference', difference)]:
        write_csv(destination / f'dce_{name}.csv', rows)
    return dict(participants=len(wide), tasks=len(records), alternatives=len(long))
