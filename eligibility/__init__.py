from otree.api import *
from .questions import AGE_WORDING, AGE_CHOICES, CONSENT_WORDING, CONSENT_CHOICES


class C(BaseConstants):
    NAME_IN_URL = 'eligibility'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Only fresh sessions receive this release; no historical default/backfill.
    survey_flow_version = models.StringField(blank=True)
    willing_to_participate = models.BooleanField(
        label=CONSENT_WORDING,
        choices=CONSENT_CHOICES,
    )
    adult_confirmed = models.BooleanField(
        label=AGE_WORDING,
        choices=AGE_CHOICES,
    )
    cookies_allowed = models.BooleanField(
        label='DEMO: Allow a temporary cookie to test browser support?',
        choices=[[True, 'Allow the test'], [False, 'Do not allow the test']],
        blank=True,  # A participation refusal must not require a cookie choice.
    )
    cookie_probe_status = models.StringField(
        initial='not_tested',
        choices=['not_tested', 'supported', 'blocked', 'declined'],
    )
    eligible = models.BooleanField(initial=False)
    exit_reason = models.StringField(initial='not_screened')


def creating_session(subsession):
    config = subsession.session.config
    if config['study_mode'] != 'pilot' or config['data_class'] != 'synthetic':
        raise RuntimeError('V0 blocks live sessions. Only synthetic pilot sessions are allowed.')
    from settings import APP_SEQUENCE, SURVEY_FLOW_VERSION
    if config.get('survey_flow_version') != SURVEY_FLOW_VERSION or config['app_sequence'] != APP_SEQUENCE:
        raise RuntimeError('V3.3 requires a new Pilot with the current native app sequence.')
    for player in subsession.get_players():
        player.survey_flow_version = SURVEY_FLOW_VERSION
        participant = player.participant
        participant.eligible = False
        participant.exit_reason = 'not_screened'
        participant.household_complete = False
        participant.finished = False
        participant.cookies_allowed = None


class AgeConfirmation(Page):
    form_model = 'player'
    form_fields = ['adult_confirmed']

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Passing age alone is not consent and must not expose the Reference ID.
        player.eligible = False
        player.participant.eligible = False
        player.exit_reason = 'not_screened' if player.adult_confirmed else 'under_18'
        player.participant.exit_reason = player.exit_reason


class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.field_maybe_none('adult_confirmed') is True


class VoluntaryParticipation(Page):
    form_model = 'player'
    form_fields = ['willing_to_participate', 'cookies_allowed', 'cookie_probe_status']

    @staticmethod
    def is_displayed(player):
        return player.field_maybe_none('adult_confirmed') is True

    @staticmethod
    def error_message(player, values):
        if values['willing_to_participate']:
            if values['cookies_allowed'] is None:
                return {'cookies_allowed': 'Please choose whether to allow the optional cookie test.'}
            if values['cookies_allowed'] and values['cookie_probe_status'] == 'declined':
                return {'cookies_allowed': 'The browser test status conflicts with your selection. Please select again.'}

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.eligible = bool(player.field_maybe_none('adult_confirmed') and player.willing_to_participate)
        player.exit_reason = '' if player.eligible else 'declined'
        player.participant.eligible = player.eligible
        player.participant.exit_reason = player.exit_reason
        if player.eligible:
            player.participant.cookies_allowed = player.cookies_allowed
            if not player.cookies_allowed:
                player.cookie_probe_status = 'declined'
        else:
            player.cookies_allowed = None
            player.cookie_probe_status = 'not_tested'
            player.participant.cookies_allowed = None


class Exit(Page):
    @staticmethod
    def is_displayed(player):
        return not player.participant.eligible


# Historical template retained; this page is no longer in the active sequence.
class CookiePreferences(Page):
    @staticmethod
    def is_displayed(player):
        return False


page_sequence = [AgeConfirmation, Introduction, VoluntaryParticipation, Exit]
