from otree.api import *
from timing import ConsentTimingPage
from .countries import COUNTRIES
from .questions_v5 import INCOME as V5_INCOME, RENT as V5_RENT, CHILDREN, EDUCATION
from .questions import AGE, RENT, INCOME, EXPOSURE
from .forms import prepare_numeric_fields
from .validation import income_in_sek


class C(BaseConstants):
    NAME_IN_URL = 'household'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Retain unused V0 columns; do not reinterpret historical blank values.
    country_of_residence = models.StringField(blank=True)
    housing_tenure = models.StringField(blank=True)
    income_range = models.StringField(blank=True)
    monthly_electricity_bill = models.FloatField(min=0, blank=True)
    previous_residence_near_nuclear = models.BooleanField(blank=True)
    placeholder_completed = models.BooleanField(initial=False)

    residence_code = models.StringField(label='In which country or region do you currently live?', choices=COUNTRIES + [('unable', 'Unable to select'), ('prefer_not', 'Prefer not to tell')])
    income_category = models.StringField(label='Approximately what is your monthly personal income after tax?', choices=V5_INCOME, widget=widgets.RadioSelect)
    rent_category = models.StringField(label='About how much does your household pay in rent or mortgage per month?', choices=V5_RENT, widget=widgets.RadioSelect, blank=True)
    children_under_18 = models.StringField(label='Do any children under 18 live in your household?', choices=CHILDREN, widget=widgets.RadioSelect)
    education_completed = models.StringField(label='What is the highest level of education you have completed?', choices=EDUCATION, widget=widgets.RadioSelect)

    age_group = models.StringField(label=AGE['wording'], choices=AGE['choices'], widget=widgets.RadioSelect)
    rent_status = models.BooleanField(label='Do you currently pay rent or a mortgage for your accommodation?', choices=RENT['choices'], widget=widgets.RadioSelect)
    monthly_rent_sek = models.IntegerField(label=RENT['amount_wording'], min=None, blank=True)
    income_thousand_sek = models.IntegerField(label=INCOME['wording'], min=None, blank=True)
    income_sek = models.IntegerField(min=None, blank=True)
    income_not_disclosed = models.BooleanField(label=INCOME['refusal'], widget=widgets.CheckboxInput, blank=True)
    previous_power_plant_exposure = models.IntegerField(
        label=EXPOSURE['wording'], choices=EXPOSURE['choices'], widget=widgets.RadioSelect,
    )


class HouseholdInformation(ConsentTimingPage):
    form_model = 'player'
    form_fields = ['age_group', 'residence_code', 'rent_status', 'rent_category',
                   'income_category', 'children_under_18', 'education_completed']

    @staticmethod
    def is_displayed(player):
        return player.participant.eligible

    @staticmethod
    def error_message(player, values):
        if values['rent_status'] is True and not values['rent_category']:
            return {'rent_category': 'Please choose an amount.'}

    @staticmethod
    def before_next_page(player, timeout_happened):
        if not player.rent_status:
            player.rent_category = None
        player.placeholder_completed = True
        player.participant.household_complete = True


page_sequence = [HouseholdInformation]
