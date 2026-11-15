"""V2.3 task-level treatment overlay; the V2.0 numeric source remains immutable."""
from collections import Counter
import hashlib
import random

from .matrix import DESIGN_HASH as NUMERIC_MATRIX_HASH, DESIGN_VERSION as NUMERIC_MATRIX_VERSION
from .matrix import canonical_json, design_payload as numeric_payload

DESIGN_VERSION = 'V2.3'
TREATMENT_DESIGN_VERSION = DESIGN_VERSION
SURVEY_VERSION = 'V2.2b'
FACILITY_LABELS = {'nuclear': 'Nuclear power plant', 'coal': 'Coal power plant'}
FACILITY_METHOD = 'within-block-complementary-pairs-v1'


def design_payload():
    return dict(design_version=DESIGN_VERSION,
                numeric_matrix_version=NUMERIC_MATRIX_VERSION, numeric_matrix_hash=NUMERIC_MATRIX_HASH,
                choice_sets=numeric_payload()['choice_sets'],
                facility_rules=dict(method=FACILITY_METHOD, scope='same-facility-for-both-alternatives-in-task',
                                    facilities=['nuclear', 'coal'], tasks_per_facility=2,
                                    pair_order='zero-based-entrant-ordinal-within-block',
                                    pair_seed='sha256(facility-pairs-v1|session_seed|block_id|pair_index)',
                                    first='seeded-uniform-two-of-four-set-IDs-for-coal', second='complement',
                                    source_profile_type='legacy-nuclear-replaced-by-persisted-task-context'),
                block_rule='permuted-triplets-atomic-entry-v1',
                presentation_rule='participant-seeded-set-shuffle-then-independent-AABB-near-side-shuffle',
                allocation_point='first-eligible-Choice-render', demographic_inputs=False)


DESIGN_HASH = hashlib.sha256(canonical_json(design_payload()).encode()).hexdigest()


def facility_schedule(blocks, seed):
    """Precompute a persisted schedule: each within-block pair balances every set."""
    occurrences = Counter()
    out = []
    for block in blocks:
        ordinal = occurrences[block]
        pair_seed = hashlib.sha256(f'facility-pairs-v1|{seed}|{block}|{ordinal // 2}'.encode()).hexdigest()
        ids = [s['choice_set_id'] for s in numeric_payload()['choice_sets'] if s['block_id'] == block]
        selected = set(random.Random(pair_seed).sample(ids, 2))
        coal = selected if ordinal % 2 == 0 else set(ids) - selected
        out.append(dict(seed=pair_seed, block_ordinal=ordinal + 1, coal_set_ids=sorted(coal)))
        occurrences[block] += 1
    return out


def validate_plan(plan):
    if (plan['design_hash'] != DESIGN_HASH or
            hashlib.sha256(canonical_json(plan['design']).encode()).hexdigest() != DESIGN_HASH):
        raise RuntimeError('Current treatment design hash mismatch; use a new Pilot session.')
    if plan['facility_schedule'] != facility_schedule(plan['sequence'], plan['seed']):
        raise RuntimeError('Persisted facility schedule differs from its seed/sequence.')


def validate_assignment(assignment):
    if (assignment['design_version'], assignment['design_hash'], assignment['treatment_design_version'],
            assignment['numeric_matrix_version'], assignment['numeric_matrix_hash']) != (
            DESIGN_VERSION, DESIGN_HASH, TREATMENT_DESIGN_VERSION, NUMERIC_MATRIX_VERSION, NUMERIC_MATRIX_HASH):
        raise ValueError('Treatment/numeric design provenance mismatch.')
    tasks = assignment['tasks']
    sources = {s['choice_set_id']: s for s in numeric_payload()['choice_sets'] if s['block_id'] == assignment['block_id']}
    if (len(tasks) != 4 or {t['choice_set_id'] for t in tasks} != set(sources)
            or Counter(t['facility_type'] for t in tasks) != {'nuclear': 2, 'coal': 2}
            or Counter(t['near_side'] for t in tasks) != {'A': 2, 'B': 2}):
        raise ValueError('Invalid four-task facility/block/side assignment.')
    expected_map = {t['choice_set_id']: t['facility_type'] for t in tasks}
    if assignment['facility_type_assignment'] != canonical_json(expected_map) or not assignment['facility_assignment_seed']:
        raise ValueError('Facility assignment map/seed mismatch.')
    if assignment['choice_set_order'] != [t['choice_set_id'] for t in tasks] or assignment['side_allocation'] != [t['near_side'] for t in tasks]:
        raise ValueError('Task order/side metadata mismatch.')
    for index, task in enumerate(tasks, 1):
        if task['task_index'] != index or task['presentation_order'] != index:
            raise ValueError('Invalid task index.')
        source = sources[task['choice_set_id']]
        for side in ('A', 'B'):
            expected = dict(source['N' if side == task['near_side'] else 'F'], facility_type=task['facility_type'])
            if task[side] != expected:
                raise ValueError('Invalid numeric profile or same-task facility context.')
