from otree.api import *
from timing import ConsentTimingPage
from .questions import ATTITUDES_VERSION, QUESTIONS, FORM_FIELDS, ECONOMIC, CLIMATE, SUPPORT, RISK, HOUSING_COST

def attitude_field(question):
    return models.IntegerField(label=question['wording'], choices=question['choices'], widget=widgets.RadioSelect)

class C(BaseConstants):
    NAME_IN_URL = 'attitudes'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer):
    attitudes_version = models.StringField(blank=True)
    attitudes_completed = models.BooleanField(initial=False)
    nuclear_economic = attitude_field(ECONOMIC)
    nuclear_climate = attitude_field(CLIMATE)
    nuclear_support = attitude_field(SUPPORT)
    nuclear_risk = attitude_field(RISK)
    housing_cost = attitude_field(HOUSING_COST)

def creating_session(subsession):
    if subsession.session.config.get('attitudes_version') != ATTITUDES_VERSION:
        raise RuntimeError('Invalid Final attitudes version')
    for player in subsession.get_players():
        player.attitudes_version = ATTITUDES_VERSION

class AttitudeSurvey(ConsentTimingPage):
    form_model = 'player'
    form_fields = FORM_FIELDS
    @staticmethod
    def is_displayed(player):
        return player.participant.eligible
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.attitudes_completed = True

page_sequence = [AttitudeSurvey]
