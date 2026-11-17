from otree.api import *
from timing import ConsentTimingPage
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
        label='Allow cookies to record time spent on each page?',
        choices=[[True, 'Yes, allow cookies and page timing.'], [False, 'No, continue without page timing.']],
        widget=widgets.RadioSelect,
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
    if (config.get('study_mode'), config.get('data_class')) not in {('live', 'production'), ('qa', 'synthetic')}:
        raise RuntimeError('Use an isolated Final production or QA session.')
    from settings import APP_SEQUENCE, SURVEY_FLOW_VERSION
    if config.get('survey_flow_version') != SURVEY_FLOW_VERSION or config['app_sequence'] != APP_SEQUENCE:
        raise RuntimeError('Final requires a new session with the Final app sequence.')
    for player in subsession.get_players():
        player.survey_flow_version = SURVEY_FLOW_VERSION
        participant = player.participant
        participant.eligible = False
        participant.exit_reason = 'not_screened'
        participant.household_complete = False
        participant.finished = False
        participant.cookies_allowed = None
        participant.show_reference = False


class AgeConfirmation(ConsentTimingPage):
    form_model = 'player'
    form_fields = ['adult_confirmed']

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Passing age alone is not consent and must not expose the Reference ID.
        player.eligible = False
        player.participant.eligible = False
        player.exit_reason = 'not_screened' if player.adult_confirmed else 'under_18'
        player.participant.exit_reason = player.exit_reason
        player.participant.show_reference = player.adult_confirmed


class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.field_maybe_none('adult_confirmed') is True


class VoluntaryParticipation(ConsentTimingPage):
    @staticmethod
    def vars_for_template(player):
        return dict(show_reference=True)

    form_model = 'player'
    form_fields = ['willing_to_participate']

    @staticmethod
    def is_displayed(player):
        return player.field_maybe_none('adult_confirmed') is True

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.eligible = bool(player.field_maybe_none('adult_confirmed') and player.willing_to_participate)
        player.exit_reason = '' if player.eligible else 'declined'
        player.participant.eligible = player.eligible
        player.participant.exit_reason = player.exit_reason
        player.participant.show_reference = player.eligible
        player.participant.cookies_allowed = None


class CookiePreferences(ConsentTimingPage):
    form_model = 'player'
    form_fields = ['cookies_allowed']

    @staticmethod
    def is_displayed(player):
        return player.participant.eligible

    @staticmethod
    def error_message(player, values):
        if values['cookies_allowed'] is None:
            return {'cookies_allowed': 'Please select an option.'}

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.cookies_allowed = player.cookies_allowed
        if not player.cookies_allowed:
            player.cookie_probe_status = 'declined'



class Exit(ConsentTimingPage):
    @staticmethod
    def is_displayed(player):
        return not player.participant.eligible


page_sequence = [AgeConfirmation, VoluntaryParticipation, CookiePreferences, Exit]
