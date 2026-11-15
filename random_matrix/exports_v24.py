"""Strict V2.4 native -> task/wide/alternative/difference adapter; no database access."""
import json
from pathlib import Path
from .matrix import PROFILE_FIELDS, DESIGN_VERSION, DESIGN_HASH, canonical_json
from .facility_design import WORDING_VERSION, validate_assignment
from .legacy_v23.exports import normalized, write_csv

FACILITY_MODULE_FIELDS = ['numeric_matrix_version', 'numeric_matrix_hash', 'treatment_design_version',
                         'facility_assignment_seed', 'facility_type_assignment']
MODULE_FIELDS = [
    'participant_code', 'session_code', 'study_mode', 'data_class', 'survey_version', 'wording_version',
    'design_version', 'design_hash', 'block_id', 'task_count', 'tasks_answered',
    'module_started', 'module_completed', 'allocation_index', 'random_seed',
    'assignment_method', 'display_version', 'choice_set_order_json', 'side_allocation_json',
    'assignment_json',
] + FACILITY_MODULE_FIELDS
TASK_METADATA = ['task_index', 'choice_set_id', 'presentation_order', 'near_side', 'facility_type',
                 'premium_sek', 'base_rent_sek', 'side_swapped']
CHOSEN_FIELDS = ['chosen_facility_type', 'chosen_distance_km', 'chosen_rent_sek', 'chosen_far', 'chosen_near20']
NATIVE_TASK_FIELDS = TASK_METADATA + [f'{side}_{f}' for side in 'AB' for f in PROFILE_FIELDS] + [
    'choice', *CHOSEN_FIELDS, 'task_completed', 'task_displayed', 'task_started_at',
    'task_submitted_at', 'task_duration_s', 'task_timing_status']
ALIASES = {'set_id': 'choice_set_id', 'choice_ab': 'choice'}
for side in 'AB':
    for target, source in [('distance_km', 'distance_km'), ('rent_sek', 'rent_sek_month'), ('near20', 'near20')]:
        ALIASES[f'home_{side}_{target}'] = f'{side}_{source}'
TASK_FIELDS = NATIVE_TASK_FIELDS + list(ALIASES)
TASK_EXPORT_FIELDS = MODULE_FIELDS + TASK_FIELDS


def with_aliases(row):
    return dict(row, **{k: row[v] for k, v in ALIASES.items()})


def task_record(player):
    first = player.in_round(1)
    row = {name: first.field_maybe_none(name) for name in MODULE_FIELDS[4:]}
    row.update(participant_code=player.participant.code, session_code=player.session.code,
               study_mode=player.session.config['study_mode'], data_class=player.session.config['data_class'])
    row.update({name: player.field_maybe_none(name) for name in NATIVE_TASK_FIELDS})
    row['task_index'] = player.round_number
    if player.field_maybe_none('wording_version') != row['wording_version']:
        raise ValueError('Inconsistent wording version across participant rounds.')
    return with_aliases(row)


def records_from_native(rows):
    provenance = ('survey_version', 'wording_version', 'design_version', 'design_hash',
                  'numeric_matrix_version', 'numeric_matrix_hash', 'treatment_design_version')
    for source in rows:
        prefix = 'random_matrix.1.player.'
        module = {name: source[prefix + name] for name in MODULE_FIELDS[4:]}
        module.update(participant_code=source['participant.code'], session_code=source['session.code'],
                      study_mode=source['session.config.study_mode'], data_class=source['session.config.data_class'])
        for index in range(1, 5):
            task_prefix = f'random_matrix.{index}.player.'
            if any(source.get(task_prefix + name) != module[name] for name in provenance):
                raise ValueError('Inconsistent treatment/wording provenance across participant rounds.')
            if any(source.get(task_prefix + name) not in ('', None) for name in ('A_size_m2', 'B_size_m2', 'housing_size_m2')):
                raise ValueError('V2.4 must not contain randomized housing size.')
            if source.get(task_prefix + 'block_id', '') != module['block_id']:
                raise ValueError('Inconsistent block across participant rounds.')
            fields = {name: source[task_prefix + name] for name in NATIVE_TASK_FIELDS if name != 'task_index'}
            yield with_aliases(dict(module, **fields, task_index=index))


def reshape(records):
    participants, long, difference, seen = {}, [], [], set()
    for raw in records:
        row = normalized(raw)
        key = (row['session_code'], row['participant_code'])
        index = int(row['task_index'])
        if not all(key) or index not in range(1, 5) or (*key, index) in seen:
            raise ValueError('Duplicate or invalid participant/task key.')
        seen.add((*key, index))
        if any(row.get(k) != row[v] for k, v in ALIASES.items()):
            raise ValueError('Export alias disagrees with native field.')
        if any(row.get(k) != v for k, v in dict(survey_version=DESIGN_VERSION, wording_version=WORDING_VERSION,
                design_version=DESIGN_VERSION, design_hash=DESIGN_HASH, numeric_matrix_version=DESIGN_VERSION,
                numeric_matrix_hash=DESIGN_HASH, treatment_design_version=DESIGN_VERSION,
                study_mode='pilot', data_class='synthetic', task_count='4').items()):
            raise ValueError('Invalid V2.4 release provenance.')
        module = {name: row[name] for name in MODULE_FIELDS}
        wide = participants.setdefault(key, dict(module))
        if any(wide[name] != module[name] for name in MODULE_FIELDS):
            raise ValueError('Inconsistent participant metadata across tasks.')
        choice = row['choice']
        if choice not in ('', 'A', 'B'):
            raise ValueError('Choice must be A, B or missing.')
        if row['assignment_json']:
            assignment = json.loads(row['assignment_json'])
            validate_assignment(assignment)
            if (assignment['session_code'], assignment['participant_code']) != key:
                raise ValueError('Snapshot provenance mismatch.')
            for name in ('design_version', 'design_hash', 'block_id', 'random_seed', 'allocation_index',
                         'assignment_method', 'display_version', *FACILITY_MODULE_FIELDS):
                if row[name] != str(assignment[name]):
                    raise ValueError('Metadata differs from persisted assignment.')
            if (row['module_started'] != '1' or int(row['allocation_index']) < 1 or not row['random_seed'] or
                    json.loads(row['choice_set_order_json']) != assignment['choice_set_order'] or
                    json.loads(row['side_allocation_json']) != assignment['side_allocation']):
                raise ValueError('Invalid assignment/module metadata.')
            task = assignment['tasks'][index - 1]
            if any(row[name] != str(task[name]) for name in TASK_METADATA):
                raise ValueError('Task metadata differs from persisted display.')
            if any(row[f'{side}_{f}'] != str(task[side][f]) for side in 'AB' for f in PROFILE_FIELDS):
                raise ValueError('Export attributes differ from persisted display.')
        else:
            assigned_fields = [f for f in TASK_METADATA if f != 'task_index'] + [f'{s}_{f}' for s in 'AB' for f in PROFILE_FIELDS]
            assigned_fields += ['block_id', 'allocation_index', 'random_seed', 'assignment_method', 'display_version',
                                'choice_set_order_json', 'side_allocation_json', 'facility_assignment_seed', 'facility_type_assignment']
            if any(row[name] for name in assigned_fields) or choice or row['module_started'] != '0' or row['task_displayed'] != '0':
                raise ValueError('Unassigned task contains assignment/exposure data.')
        if row['task_completed'] != str(int(bool(choice))):
            raise ValueError('Task completion does not match response.')
        if choice:
            expected = [row[f'{choice}_facility_type'], row[f'{choice}_distance_km'], row[f'{choice}_rent_sek_month'],
                        str(int(row[f'{choice}_distance_km'] == '50')), row[f'{choice}_near20']]
            if [row[k] for k in CHOSEN_FIELDS] != expected:
                raise ValueError('Chosen profile does not match actual displayed choice.')
            if row['task_displayed'] != '1' or not row['task_submitted_at']:
                raise ValueError('Choice without displayed/submitted task.')
            if row['task_timing_status'] == 'ok':
                if not row['task_started_at'] or not row['task_duration_s']:
                    raise ValueError('Completed timing lacks start or duration.')
                elapsed = float(row['task_submitted_at']) - float(row['task_started_at'])
                if elapsed < 0 or abs(elapsed - float(row['task_duration_s'])) > 1e-5:
                    raise ValueError('Task duration disagrees with timestamps.')
            elif row['task_timing_status'] not in ('missing_start', 'clock_reversed') or row['task_duration_s']:
                raise ValueError('Invalid task timing status/duration.')
        elif any(row[k] for k in CHOSEN_FIELDS + ['task_submitted_at', 'task_duration_s']) or row['task_timing_status'] != 'not_submitted':
            raise ValueError('Missing choice must not have completed-task values.')
        wide.update({f'task{index}_{name}': row[name] for name in TASK_FIELDS})
        common = dict(module, **{name: row[name] for name in TASK_FIELDS if not name.startswith(('A_', 'B_', 'home_'))})
        for side in 'AB':
            distance = row[f'{side}_distance_km']
            long.append(dict(common, alternative_id=side, home=side,
                             chosen='' if not choice else int(choice == side),
                             far='' if not distance else int(distance == '50'),
                             **{f: row[f'{side}_{f}'] for f in PROFILE_FIELDS}))
        diff = dict(common, chose_A='' if not choice else int(choice == 'A'))
        a, b = row['A_rent_sek_month'], row['B_rent_sek_month']
        diff['delta_rent_1000'] = (int(a) - int(b)) / 1000 if a and b else ''
        diff['delta_far'] = int(row['A_distance_km'] == '50') - int(row['B_distance_km'] == '50') if a and b else ''
        diff['oil'] = int(row['facility_type'] == 'oil_fired') if row['facility_type'] else ''
        diff['delta_far_x_oil'] = diff['delta_far'] * diff['oil'] if a and b else ''
        difference.append(diff)
    for key, row in participants.items():
        if sum(s[:2] == key for s in seen) != 4:
            raise ValueError('Export requires all four task rows, including missing outcomes.')
        answered = sum(row[f'task{i}_choice'] in ('A', 'B') for i in range(1, 5))
        if answered != int(row['tasks_answered']) or row['module_completed'] != str(int(answered == 4)):
            raise ValueError('Module completion does not match saved choices.')
    return list(participants.values()), long, difference


def write_formats(records, destination):
    records = list(records)
    wide, long, difference = reshape(records)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('tasks', 'wide', 'long', 'difference'):
        if (destination / f'dce_{name}.csv').exists():
            raise FileExistsError('Choose a new export directory; existing exports are never overwritten.')
    for name, rows in [('tasks', records), ('wide', wide), ('long', long), ('difference', difference)]:
        write_csv(destination / f'dce_{name}.csv', rows)
    return dict(participants=len(wide), tasks=len(records), alternatives=len(long))
