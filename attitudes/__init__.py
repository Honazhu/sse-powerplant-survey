from otree.api import *
from timing import ConsentTimingPage
from timing import export_page_durations
import time
from .questions import (ATTITUDES_VERSION, TITLE, INTRODUCTION, BY_FIELD, FORM_FIELDS,
                        SUPPORT, RISK, ECONOMIC, CLIMATE, HOUSING_COST, QUESTIONS)
from .validation import response_error
from .forms import prepare_attitude_fields


def attitude_field(question):
    return models.IntegerField(label=question['wording'], choices=question['choices'],
                               min=-2, max=2, widget=widgets.RadioSelect)


class C(BaseConstants):
    NAME_IN_URL = 'attitudes'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Legacy preview columns retain their original 1–10 meanings and remain unused.
    nuclear_energy_support = models.IntegerField(min=1, max=10, blank=True)
    nuclear_risk_perception = models.IntegerField(min=1, max=10, blank=True)
    economic_impact_perception = models.IntegerField(min=1, max=10, blank=True)
    climate_impact_perception = models.IntegerField(min=1, max=10, blank=True)
    housing_cost_sensitivity = models.IntegerField(min=1, max=10, blank=True)
    completed = models.BooleanField(initial=False)
    attitudes_version = models.StringField(blank=True)
    attitudes_completed = models.BooleanField(blank=True)
    attitudes_submitted_at = models.FloatField(blank=True)
    nuclear_support = attitude_field(SUPPORT)
    nuclear_risk = attitude_field(RISK)
    nuclear_economic = attitude_field(ECONOMIC)
    nuclear_climate = attitude_field(CLIMATE)
    housing_cost = attitude_field(HOUSING_COST)


def creating_session(subsession):
    if (subsession.session.config.get('study_mode'), subsession.session.config.get('data_class'),
            subsession.session.config.get('attitudes_version')) != ('pilot', 'synthetic', ATTITUDES_VERSION):
        raise RuntimeError('V3.3 attitudes require a new synthetic Pilot session.')
    for player in subsession.get_players():
        player.attitudes_version = ATTITUDES_VERSION
        player.attitudes_completed = False


def require_current_attitudes(player):
    if player.field_maybe_none('attitudes_version') != ATTITUDES_VERSION:
        raise RuntimeError('Attitudes version is missing or historical. Use a new V3.3 Pilot; historical records are not relabelled.')


class AttitudeSurvey(ConsentTimingPage):
    form_model = 'player'
    form_fields = FORM_FIELDS

    def get_form(self, instance, formdata=None):
        form = super().get_form(instance, formdata=formdata)
        if formdata is not None:
            prepare_attitude_fields(form)
        return form

    @staticmethod
    def is_displayed(player):
        return player.participant.eligible and player.participant.household_complete

    @staticmethod
    def vars_for_template(player):
        require_current_attitudes(player)
        return dict(questions=BY_FIELD, attitude_title=TITLE, attitude_introduction=INTRODUCTION,
                    attitudes_version=player.attitudes_version)

    @staticmethod
    def error_message(player, values):
        require_current_attitudes(player)
        return {q['field']: error for q in QUESTIONS
                if (error := response_error(values[q['field']], q))} or None

    @staticmethod
    def before_next_page(player, timeout_happened):
        require_current_attitudes(player)
        if player.field_maybe_none('attitudes_submitted_at') is not None:
            return
        from completion_v5 import validate_complete
        validate_complete(player)
        player.attitudes_completed = True
        player.attitudes_submitted_at = time.time()
        player.completed = True
        player.participant.finished = True


class Completion(ConsentTimingPage):
    @staticmethod
    def is_displayed(player):
        return player.participant.eligible and player.field_maybe_none('attitudes_completed') is True

    @staticmethod
    def vars_for_template(player):
        require_current_attitudes(player)
        return {}


page_sequence = [AttitudeSurvey, Completion]


def custom_export(players):
    from completion_v5 import export_completed
    yield from export_completed(players)


def custom_export_timing(players):
    # A separate opt-in export, also restricted to completed responses.
    from completion_v5 import validate_complete
    eligible = []
    for player in players:
        if player.participant.finished and player.field_maybe_none('attitudes_completed') is True and player.participant.cookies_allowed is True:
            validate_complete(player)
            eligible.append(player)
    yield from export_page_durations(eligible)
