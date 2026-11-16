from otree.api import *
from timing import ConsentTimingPage
import json
import time
from .randomization import assign_once, displayed_task, initialize_plan
from .facility_design import (FACILITY_LABELS, NUMERIC_MATRIX_VERSION, NUMERIC_MATRIX_HASH,
                              TREATMENT_DESIGN_VERSION, SURVEY_VERSION, validate_plan)

WORDING_VERSION = '5.0.0'


class C(BaseConstants):
    NAME_IN_URL = 'random_matrix'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 6


class Subsession(BaseSubsession):
    # Only round 1 owns the persisted plan/cursor.
    allocation_plan_json = models.LongStringField()
    allocation_cursor = models.IntegerField(initial=0)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Retain V0 columns with historical meanings; V2 never populates them.
    scenario_id = models.StringField()
    treatment_arm = models.StringField()
    nuclear_distance_km = models.FloatField()
    housing_price = models.FloatField()
    housing_size_m2 = models.FloatField()
    price_unit = models.StringField()
    alternative_attributes_json = models.LongStringField()
    matrix_version = models.StringField()
    is_demo = models.BooleanField()
    assignment_method = models.StringField()
    display_version = models.StringField()
    scenario_snapshot_json = models.LongStringField()
    scenario_displayed = models.BooleanField(initial=False)
    scenario_acknowledged = models.BooleanField(initial=False)

    survey_version = models.StringField()
    # No default/backfill: only newly created sessions receive the current wording.
    wording_version = models.StringField(blank=True)
    numeric_matrix_version = models.StringField(blank=True)
    numeric_matrix_hash = models.StringField(blank=True)
    treatment_design_version = models.StringField(blank=True)
    facility_assignment_seed = models.StringField(blank=True)
    facility_type_assignment = models.LongStringField(blank=True)
    facility_type = models.StringField(blank=True)
    design_version = models.StringField()
    design_hash = models.StringField()
    block_id = models.StringField()
    # Participant/module metadata is authoritative in round 1 only.
    task_count = models.IntegerField(initial=6)
    tasks_answered = models.IntegerField(initial=0)
    module_started = models.BooleanField(initial=False)
    module_completed = models.BooleanField(initial=False)
    assignment_claimed = models.BooleanField(initial=False)
    allocation_index = models.IntegerField()
    assignment_json = models.LongStringField()
    random_seed = models.StringField()
    choice_set_order_json = models.LongStringField()
    side_allocation_json = models.LongStringField()
    task_index = models.IntegerField()
    choice_set_id = models.StringField()
    presentation_order = models.IntegerField()
    near_side = models.StringField()
    A_size_m2 = models.IntegerField()
    A_distance_km = models.IntegerField()
    A_rent_sek_month = models.IntegerField()
    A_near20 = models.IntegerField()
    A_facility_type = models.StringField()
    B_size_m2 = models.IntegerField()
    B_distance_km = models.IntegerField()
    B_rent_sek_month = models.IntegerField()
    B_near20 = models.IntegerField()
    B_facility_type = models.StringField()
    choice = models.StringField(choices=[['A', 'Choose Home A'], ['B', 'Choose Home B']],
                                widget=widgets.RadioSelect)
    premium_sek = models.IntegerField(blank=True)
    base_rent_sek = models.IntegerField(blank=True)
    side_swapped = models.BooleanField(blank=True)
    chosen_facility_type = models.StringField(blank=True)
    chosen_distance_km = models.IntegerField(blank=True)
    chosen_rent_sek = models.IntegerField(blank=True)
    chosen_far = models.IntegerField(blank=True)
    task_completed = models.BooleanField(blank=True)
    chosen_near20 = models.IntegerField()
    task_displayed = models.BooleanField(initial=False)
    task_started_at = models.FloatField()
    task_submitted_at = models.FloatField()
    task_duration_s = models.FloatField()
    task_timing_status = models.StringField(initial='not_submitted')


def creating_session(subsession):
    initialize_plan(subsession)
    for player in subsession.get_players():
        player.design_version = TREATMENT_DESIGN_VERSION
        player.design_hash = NUMERIC_MATRIX_HASH
        player.task_completed = False
        player.wording_version = WORDING_VERSION
        player.survey_version = SURVEY_VERSION
        player.numeric_matrix_version = NUMERIC_MATRIX_VERSION
        player.numeric_matrix_hash = NUMERIC_MATRIX_HASH
        player.treatment_design_version = TREATMENT_DESIGN_VERSION


def require_current_wording(player):
    # Do not render or accept new wording under an old/missing version label.
    if any(p.field_maybe_none('wording_version') != WORDING_VERSION
           for p in (player.in_round(1), player)):
        raise RuntimeError('Housing Choice wording is missing or belongs to another release. '
                           f'Use a new {WORDING_VERSION} Pilot session; historical records are not relabelled.')


def instruction_context(player):
    # Validate the saved treatment plan without allocating or starting task timing.
    validate_plan(json.loads(player.in_round(1).subsession.allocation_plan_json))

class ScenarioInstructions(ConsentTimingPage):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1 and player.participant.eligible

    @staticmethod
    def vars_for_template(player):
        require_current_wording(player)
        instruction_context(player)
        return dict(wording_version=player.wording_version)

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_current_wording(player)
        instruction_context(player)


class Choice(ConsentTimingPage):
    form_model = 'player'
    form_fields = ['choice']

    @staticmethod
    def is_displayed(player):
        return player.participant.eligible

    @staticmethod
    def vars_for_template(player):
        require_current_wording(player)
        assign_once(player)
        task = displayed_task(player)
        if not player.task_displayed:
            if player.participant.cookies_allowed is True:
                player.task_started_at = time.time()
            player.task_displayed = True
        # Display strings only: preserve the persisted integer attributes/export.
        return dict(task=task, power_plant_context=FACILITY_LABELS[task['facility_type']],
                    wording_version=player.wording_version, rent_labels={
            side: f"{task[side]['rent_sek_month']:,}" for side in ('A', 'B')
        })

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_current_wording(player)
        task = displayed_task(player)
        if player.choice not in ('A', 'B'):
            raise RuntimeError('A submitted task must contain exactly one A/B choice.')
        if player.field_maybe_none('task_completed') is True:
            return
        chosen = task[player.choice]
        player.chosen_near20 = chosen['near20']
        player.chosen_facility_type = chosen['facility_type']
        player.chosen_distance_km = chosen['distance_km']
        player.chosen_rent_sek = chosen['rent_sek_month']
        player.chosen_far = int(chosen['distance_km'] == 50)
        player.task_completed = True
        if player.participant.cookies_allowed is True:
            player.task_submitted_at = time.time()
            start = player.field_maybe_none('task_started_at')
            if start is None:
                player.task_timing_status = 'missing_start'
            elif player.task_submitted_at < start:
                player.task_timing_status = 'clock_reversed'
            else:
                player.task_duration_s = player.task_submitted_at - start
                player.task_timing_status = 'ok'
        else:
            player.task_started_at = None
            player.task_submitted_at = None
            player.task_duration_s = None
            player.task_timing_status = 'no_consent'
        first = player.in_round(1)
        first.tasks_answered = sum(p.field_maybe_none('task_completed') is True
                                   for p in player.in_rounds(1, 6))
        first.module_completed = first.tasks_answered == C.NUM_ROUNDS


page_sequence = [ScenarioInstructions, Choice]


def custom_export(players):
    # Official V5 data are exported by attitudes.custom_export after completion.
    yield ['notice']
    yield ['Use the V5 completed-response export from attitudes.']
