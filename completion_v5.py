"""V5 completion validation and versioned wide export.

Only the final attitudes submission can set finished. Intermediate oTree data
remain operational records; native oTree exports are NOT the research export.
"""
from otree.database import dbq
from random_matrix.randomization import stored_assignment, displayed_task
from attitudes.questions import FORM_FIELDS
from household.questions_v5 import INCOME, RENT, CHILDREN, EDUCATION
from household.countries import COUNTRIES

HOUSEHOLD = ['age_group', 'residence_code', 'rent_status', 'rent_category',
             'income_category', 'children_under_18', 'education_completed']
CHOICE = ['choice_set_id', 'facility_type', 'A_distance_km', 'A_rent_sek_month',
          'B_distance_km', 'B_rent_sek_month', 'choice', 'near_side', 'side_swapped',
          'task_duration_s', 'task_timing_status']
FIELDS = ['survey_reference_id', 'survey_version', 'session_code', 'wording_version',
          'treatment_design_version', 'numeric_matrix_hash', 'cookies_allowed',
          'assignment_json', *HOUSEHOLD, *FORM_FIELDS] + [
          f'choice_{i}_{name}' for i in range(1, 7) for name in CHOICE]

def related(player):
    from eligibility import Player as E
    from household import Player as H
    from random_matrix import Player as R
    pid = player.participant.id
    return (dbq(E).filter_by(participant_id=pid).one(),
            dbq(H).filter_by(participant_id=pid).one(),
            dbq(R).filter_by(participant_id=pid).order_by(R.round_number).all())

def validate_complete(player):
    e, h, choices = related(player)
    if (e.field_maybe_none('adult_confirmed') is not True or
        e.field_maybe_none('willing_to_participate') is not True or
        not player.participant.eligible or not player.participant.household_complete or
        not h.placeholder_completed or len(choices) != 6):
        raise ValueError('Incomplete eligibility, consent, household, or choices.')
    assignment = stored_assignment(choices[0])
    if len({x['choice_set_id'] for x in assignment['tasks']}) != 6:
        raise ValueError('Choice sets are not distinct.')
    for r in choices:
        task = displayed_task(r)
        choice = r.field_maybe_none('choice')
        if r.field_maybe_none('task_completed') is not True or choice not in ('A', 'B'):
            raise ValueError('Incomplete choice.')
        chosen = task[choice]
        if (r.field_maybe_none('chosen_facility_type'), r.field_maybe_none('chosen_distance_km'),
            r.field_maybe_none('chosen_rent_sek')) != (chosen['facility_type'], chosen['distance_km'], chosen['rent_sek_month']):
            raise ValueError('Selected profile mismatch.')
        if player.participant.cookies_allowed is not True and any(r.field_maybe_none(x) is not None for x in ('task_started_at', 'task_submitted_at', 'task_duration_s')):
            raise ValueError('Timing without consent.')
    if (h.field_maybe_none('age_group') not in ('18_25','26_35','36_45','46_55','56_65','66_plus') or
        h.field_maybe_none('residence_code') not in dict(COUNTRIES + [('unable',''), ('prefer_not','')]) or
        h.field_maybe_none('income_category') not in dict(INCOME) or
        h.field_maybe_none('children_under_18') not in dict(CHILDREN) or
        h.field_maybe_none('education_completed') not in dict(EDUCATION) or
        h.field_maybe_none('rent_status') not in (True, False) or
        (h.rent_status and h.field_maybe_none('rent_category') not in dict(RENT)) or
        (not h.rent_status and h.field_maybe_none('rent_category') is not None)):
        raise ValueError('Invalid household response.')
    if any(type(player.field_maybe_none(k)) is not int or player.field_maybe_none(k) not in range(-2,3) for k in FORM_FIELDS):
        raise ValueError('Invalid attitudes.')
    return e, h, choices

def export_completed(players):
    yield FIELDS
    seen = set()
    for player in players:
        if not (player.participant.finished and player.field_maybe_none('attitudes_completed') is True):
            continue
        e, h, choices = validate_complete(player)
        ref = player.participant.code
        if ref in seen:
            raise ValueError('Duplicate reference ID in export.')
        seen.add(ref)
        first = choices[0]
        values = [ref, '5.0.0', player.session.code, first.wording_version,
                  first.treatment_design_version, first.numeric_matrix_hash,
                  player.participant.cookies_allowed is True, first.assignment_json]
        values += [h.field_maybe_none(k) for k in HOUSEHOLD]
        values += [player.field_maybe_none(k) for k in FORM_FIELDS]
        values += [r.field_maybe_none(k) for r in choices for k in CHOICE]
        yield values
