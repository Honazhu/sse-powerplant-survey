"""Final completed-only production export; raw oTree records are operational data."""
from otree.database import dbq
from random_matrix.randomization import stored_assignment, displayed_task
from attitudes.questions import FORM_FIELDS

HOUSEHOLD = ['age_group','gender','residence_code','main_activity','rent_status_final','monthly_rent_sek','rent_missing_reason','household_income_after_tax','income_missing_reason','children_under_18','education_completed','additional_feedback']
CHOICE = ['choice_set_id','facility_type','A_distance_km','A_rent_sek_month','B_distance_km','B_rent_sek_month','choice','near_side','side_swapped','task_duration_s','task_timing_status']
FIELDS = ['survey_reference_id','survey_version','session_code','study_mode','data_class','matrix_version','treatment_design_version','numeric_matrix_hash','consent','timing_consent','completion_status','assignment_json'] + HOUSEHOLD + [x for f in FORM_FIELDS for x in (f, f + '_missing_reason')] + [f'choice_{i}_{name}' for i in range(1,7) for name in CHOICE]

def validate_complete(h):
    from eligibility import Player as E
    from attitudes import Player as A
    from random_matrix import Player as R
    pid = h.participant.id
    e = dbq(E).filter_by(participant_id=pid).one()
    a = dbq(A).filter_by(participant_id=pid).one()
    choices = dbq(R).filter_by(participant_id=pid).order_by(R.round_number).all()
    if e.field_maybe_none('adult_confirmed') is not True or e.field_maybe_none('willing_to_participate') is not True or e.field_maybe_none('cookies_allowed') not in (True, False) or not h.participant.eligible or a.field_maybe_none('attitudes_completed') is not True:
        raise ValueError('Incomplete consent or attitudes')
    if any(a.field_maybe_none(f) not in (-2,-1,0,1,2,99) for f in FORM_FIELDS): raise ValueError('Invalid attitude')
    if len(choices) != 6: raise ValueError('Incomplete choice rounds')
    assignment = stored_assignment(choices[0])
    for r in choices:
        task = displayed_task(r)
        choice = r.field_maybe_none('choice')
        if r.field_maybe_none('task_completed') is not True or choice not in ('A','B'): raise ValueError('Incomplete choice')
        chosen = task[choice]
        if (r.field_maybe_none('chosen_facility_type'), r.field_maybe_none('chosen_distance_km'), r.field_maybe_none('chosen_rent_sek')) != (chosen['facility_type'],chosen['distance_km'],chosen['rent_sek_month']): raise ValueError('Choice mismatch')
        if h.participant.cookies_allowed is not True and any(r.field_maybe_none(x) is not None for x in ('task_started_at','task_submitted_at','task_duration_s')): raise ValueError('Timing without consent')
    for f in ('age_group','gender','residence_code','main_activity','rent_status_final','children_under_18','education_completed'):
        if not h.field_maybe_none(f): raise ValueError('Incomplete household')
    for amount, reason in [('household_income_after_tax','income_missing_reason')]:
        if (h.field_maybe_none(amount) is None) == (not h.field_maybe_none(reason)): raise ValueError('Invalid income')
    if h.rent_status_final == 'yes' and ((h.field_maybe_none('monthly_rent_sek') is None) == (not h.field_maybe_none('rent_missing_reason'))): raise ValueError('Invalid housing cost')
    if h.rent_status_final != 'yes' and (h.field_maybe_none('monthly_rent_sek') is not None or h.field_maybe_none('rent_missing_reason')): raise ValueError('Invalid skipped housing cost')
    return e, a, choices

def export_completed(players):
    yield FIELDS
    seen = set()
    for h in players:
        if h.session.config.get('data_class') != 'production' or h.session.config.get('study_mode') != 'live' or not h.participant.finished or not h.field_maybe_none('household_completed'): continue
        e, a, choices = validate_complete(h)
        ref = h.participant.code
        if ref in seen: raise ValueError('Duplicate participant')
        seen.add(ref)
        first = choices[0]; c = h.session.config
        values = [ref, 'final', h.session.code, c['study_mode'], c['data_class'], c['matrix_version'], c['treatment_design_version'], first.numeric_matrix_hash, True, h.participant.cookies_allowed, 'completed', first.assignment_json]
        values += [h.field_maybe_none(f) for f in HOUSEHOLD]
        for f in FORM_FIELDS:
            value = a.field_maybe_none(f)
            values += [None if value == 99 else value, ('dont_know' if f in ('nuclear_economic','nuclear_climate') else 'prefer_not') if value == 99 else None]
        values += [r.field_maybe_none(k) for r in choices for k in CHOICE]
        yield values
