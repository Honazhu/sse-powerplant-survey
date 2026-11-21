"""V2.4 provenance and strict persisted-plan/profile validation."""
from collections import Counter
import hashlib
from .matrix import DESIGN_VERSION as NUMERIC_DESIGN_VERSION, DESIGN_HASH as NUMERIC_MATRIX_HASH, BLOCKS, canonical_json
from .matrix import design_payload as numeric_design_payload

DESIGN_VERSION = TREATMENT_DESIGN_VERSION = 'V5.0'
NUMERIC_MATRIX_VERSION = NUMERIC_DESIGN_VERSION
SURVEY_VERSION = '5.0.0'

def design_payload():
    payload = numeric_design_payload()
    payload.update(design_version=DESIGN_VERSION,
                   allocation_rule='participant-seeded-three-of-four-per-facility-v5',
                   order_rule='participant-seeded-uniform-six-set-shuffle',
                   side_rule='per-facility-random-one-versus-two-near-side',
                   numeric_matrix_version=NUMERIC_MATRIX_VERSION,
                   numeric_matrix_hash=NUMERIC_MATRIX_HASH)
    return payload

DESIGN_HASH = hashlib.sha256(canonical_json(design_payload()).encode()).hexdigest()

WORDING_VERSION = '5.0.0'
FACILITY_LABELS = {'nuclear': 'Nuclear power plant', 'oil_fired': 'Oil-fired power plant'}


def validate_plan(plan):
    from .randomization import allocation_sequence, ASSIGNMENT_METHOD
    if (plan.get('design_hash') != DESIGN_HASH or
            hashlib.sha256(canonical_json(plan.get('design')).encode()).hexdigest() != DESIGN_HASH):
        raise RuntimeError('Current treatment design hash mismatch; use a new V2.4 Pilot session.')
    if (plan.get('assignment_method') != ASSIGNMENT_METHOD or
            plan.get('sequence') != allocation_sequence(len(plan['sequence']), plan['seed'])):
        raise RuntimeError('Persisted block sequence differs from its seed/rules.')


def validate_assignment(a):
    from .randomization import ASSIGNMENT_METHOD, DISPLAY_VERSION
    if any(a.get(k) != v for k, v in dict(design_version=DESIGN_VERSION, design_hash=DESIGN_HASH,
            numeric_matrix_version=NUMERIC_MATRIX_VERSION, numeric_matrix_hash=NUMERIC_MATRIX_HASH,
            treatment_design_version=TREATMENT_DESIGN_VERSION,
            assignment_method=ASSIGNMENT_METHOD, display_version=DISPLAY_VERSION).items()):
        raise ValueError('V2.4 design provenance mismatch.')
    sources = {s['choice_set_id']: s for s in design_payload()['choice_sets']}
    tasks = a['tasks']
    if (a.get('block_id') != 'stratified' or len(tasks) != 6 or
            len({t['choice_set_id'] for t in tasks}) != 6 or
            not {t['choice_set_id'] for t in tasks} <= set(sources) or
            Counter(t['facility_type'] for t in tasks) != {'nuclear': 3, 'oil_fired': 3}):
        raise ValueError('Invalid V2.4 block/set membership.')
    if a['choice_set_order'] != [t['choice_set_id'] for t in tasks] or a['side_allocation'] != [t['near_side'] for t in tasks]:
        raise ValueError('Task order/side metadata mismatch.')
    for facility in FACILITY_LABELS:
        if Counter(t['near_side'] for t in tasks if t['facility_type'] == facility) not in ({'A': 1, 'B': 2}, {'A': 2, 'B': 1}):
            raise ValueError('V2.4 requires one Near-A and one Near-B per facility.')
    for i, task in enumerate(tasks, 1):
        source = sources[task['choice_set_id']]
        if (task['task_index'] != i or task['presentation_order'] != i or
                any(task[k] != source[k] for k in ('facility_type', 'premium_sek', 'base_rent_sek')) or
                task['side_swapped'] not in (0, 1)):
            raise ValueError('Invalid task metadata.')
        for side in 'AB':
            original = ('B' if side == 'A' else 'A') if task['side_swapped'] else side
            if task[side] != source[original]:
                raise ValueError('Invalid V2.4 whole Home profile.')
        if task[task['near_side']]['distance_km'] != 10:
            raise ValueError('Near side disagrees with displayed distance.')
    if a.get('facility_assignment_seed') or a.get('facility_type_assignment') != canonical_json({t['choice_set_id']: t['facility_type'] for t in tasks}):
        raise ValueError('V2.4 facility is frozen by set, not separately randomized.')
