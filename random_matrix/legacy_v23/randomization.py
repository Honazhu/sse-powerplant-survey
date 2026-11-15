"""Persisted permuted-triplet allocation, claimed atomically on module entry.

Conditional SQL updates run inside oTree's request transaction. No commit,
global counter, demographic input, or response-adaptive allocation is used here.
"""
import json
import random
import secrets

from .matrix import PROFILE_FIELDS, canonical_json
from .facility_design import (DESIGN_HASH, DESIGN_VERSION, NUMERIC_MATRIX_VERSION, NUMERIC_MATRIX_HASH,
                              TREATMENT_DESIGN_VERSION, SURVEY_VERSION, design_payload, facility_schedule,
                              validate_plan, validate_assignment)

ASSIGNMENT_METHOD = 'permuted-triplets-with-facility-pairs-v2'
DISPLAY_VERSION = 'housing-choice-v2.3'


def allocation_sequence(count, seed):
    rng = random.Random(seed)
    sequence = []
    while len(sequence) < count:
        triplet = [1, 2, 3]
        rng.shuffle(triplet)
        sequence.extend(triplet)
    return sequence[:count]


def make_assignment(plan, block_id, seed, allocation_index, participant_code, session_code):
    rng = random.Random(seed)
    sets = [s for s in plan['design']['choice_sets'] if s['block_id'] == block_id]
    rng.shuffle(sets)
    sides = ['A', 'A', 'B', 'B']
    rng.shuffle(sides)
    if plan['sequence'][allocation_index - 1] != block_id:
        raise RuntimeError('Facility schedule/block index mismatch.')
    facility = plan['facility_schedule'][allocation_index - 1]
    tasks = []
    for index, (choice_set, near_side) in enumerate(zip(sets, sides), 1):
        facility_type = 'coal' if choice_set['choice_set_id'] in facility['coal_set_ids'] else 'nuclear'
        tasks.append(dict(task_index=index, presentation_order=index, facility_type=facility_type,
                          choice_set_id=choice_set['choice_set_id'], near_side=near_side,
                          A=dict(choice_set['N' if near_side == 'A' else 'F'], facility_type=facility_type),
                          B=dict(choice_set['F' if near_side == 'A' else 'N'], facility_type=facility_type)))
    assignment = dict(participant_code=participant_code, session_code=session_code,
                design_version=plan['design']['design_version'], design_hash=plan['design_hash'],
                numeric_matrix_version=NUMERIC_MATRIX_VERSION, numeric_matrix_hash=NUMERIC_MATRIX_HASH,
                treatment_design_version=TREATMENT_DESIGN_VERSION,
                facility_assignment_seed=facility['seed'],
                facility_type_assignment=canonical_json({t['choice_set_id']: t['facility_type'] for t in tasks}),
                block_id=block_id, allocation_index=allocation_index, random_seed=seed,
                assignment_method=ASSIGNMENT_METHOD, display_version=DISPLAY_VERSION,
                choice_set_order=[t['choice_set_id'] for t in tasks],
                side_allocation=sides, tasks=tasks)
    validate_assignment(assignment)
    return assignment


def initialize_plan(subsession):
    config = subsession.session.config
    if (config['study_mode'], config['data_class'], config['matrix_version'],
            config.get('treatment_design_version'), config.get('survey_version')) != (
            'pilot', 'synthetic', NUMERIC_MATRIX_VERSION, TREATMENT_DESIGN_VERSION, SURVEY_VERSION):
        raise RuntimeError('V2.3 permits only the new synthetic Pilot configuration.')
    if subsession.round_number != 1 or subsession.field_maybe_none('allocation_plan_json'):
        return
    seed = secrets.token_hex(32)
    plan = dict(seed=seed, design=design_payload(), design_hash=DESIGN_HASH,
                sequence=allocation_sequence(subsession.session.num_participants, seed),
                study_mode=config['study_mode'], data_class=config['data_class'],
                session_code=subsession.session.code, assignment_method=ASSIGNMENT_METHOD)
    plan['facility_schedule'] = facility_schedule(plan['sequence'], seed)
    subsession.allocation_plan_json = canonical_json(plan)


def stored_assignment(player):
    first = player.in_round(1)
    serialized = first.field_maybe_none('assignment_json')
    if not serialized:
        raise RuntimeError('No persisted DCE assignment.')
    assignment = json.loads(serialized)
    if (assignment['participant_code'], assignment['session_code']) != (player.participant.code, player.session.code):
        raise RuntimeError('Assignment provenance mismatch; reassignment refused.')
    validate_assignment(assignment)
    return assignment


def assign_once(player):
    """Claim an eligible entrant and all four tasks in one request transaction.

    Compare-and-set the existing round-1 Player, then atomically increment the
    round-1 Subsession cursor. oTree commits the claim, cursor and snapshot
    together; exceptions roll back all of them. No Session.vars counter.
    """
    from otree.database import dbq

    if not (player.participant.eligible and player.participant.household_complete):
        raise RuntimeError('DCE entry requires eligibility and completed Household.')
    first = player.in_round(1)
    if first.field_maybe_none('assignment_json'):
        return stored_assignment(player)
    Player = type(first)
    claimed = dbq(Player).filter_by(id=first.id, assignment_claimed=False).update(
        {Player.assignment_claimed: True}, synchronize_session=False)
    if claimed == 0:
        dbq(Player).filter_by(id=first.id).populate_existing().one()
        return stored_assignment(player)
    first.assignment_claimed = True
    subsession = first.subsession
    Subsession = type(subsession)
    plan = json.loads(subsession.allocation_plan_json)
    if (plan['session_code'], plan['study_mode'], plan['data_class']) != (
            player.session.code, 'pilot', 'synthetic'):
        raise RuntimeError('Allocation plan/session mismatch.')
    validate_plan(plan)
    updated = dbq(Subsession).filter(Subsession.id == subsession.id,
                                    Subsession.allocation_cursor < len(plan['sequence'])).update(
        {Subsession.allocation_cursor: Subsession.allocation_cursor + 1}, synchronize_session=False)
    if updated != 1:
        raise RuntimeError('Allocation sequence exhausted; do not recycle assignments.')
    cursor = dbq(Subsession.allocation_cursor).filter_by(id=subsession.id).scalar()
    assignment = make_assignment(plan, plan['sequence'][cursor - 1], secrets.token_hex(32),
                                 cursor, player.participant.code, player.session.code)
    for task_player, task in zip(first.in_rounds(1, 4), assignment['tasks']):
        for field in ('design_version', 'design_hash', 'block_id', 'assignment_method', 'display_version'):
            setattr(task_player, field, assignment[field])
        for field in ('task_index', 'presentation_order', 'choice_set_id', 'near_side', 'facility_type'):
            setattr(task_player, field, task[field])
        for side in ('A', 'B'):
            for field in PROFILE_FIELDS:
                setattr(task_player, side + '_' + field, task[side][field])
    first.assignment_json = canonical_json(assignment)
    first.random_seed = assignment['random_seed']
    first.facility_assignment_seed = assignment['facility_assignment_seed']
    first.facility_type_assignment = assignment['facility_type_assignment']
    first.allocation_index = cursor
    first.choice_set_order_json = canonical_json(assignment['choice_set_order'])
    first.side_allocation_json = canonical_json(assignment['side_allocation'])
    first.module_started = True
    return assignment


def displayed_task(player):
    task = stored_assignment(player)['tasks'][player.round_number - 1]
    for field in ('task_index', 'presentation_order', 'choice_set_id', 'near_side', 'facility_type'):
        if getattr(player, field) != task[field]:
            raise RuntimeError('Task metadata mismatch.')
    for side in ('A', 'B'):
        for field in PROFILE_FIELDS:
            if getattr(player, side + '_' + field) != task[side][field]:
                raise RuntimeError('Stored profile mismatch; display refused.')
    return task
