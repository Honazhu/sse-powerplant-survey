from otree.api import *
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

    age_group = models.StringField(label=AGE['wording'], choices=AGE['choices'], widget=widgets.RadioSelect)
    rent_status = models.BooleanField(label=RENT['wording'], choices=RENT['choices'])
    monthly_rent_sek = models.IntegerField(label=RENT['amount_wording'], min=None, blank=True)
    income_thousand_sek = models.IntegerField(label=INCOME['wording'], min=None, blank=True)
    income_sek = models.IntegerField(min=None, blank=True)
    income_not_disclosed = models.BooleanField(label=INCOME['refusal'], widget=widgets.CheckboxInput, blank=True)
    previous_power_plant_exposure = models.IntegerField(
        label=EXPOSURE['wording'], choices=EXPOSURE['choices'], widget=widgets.RadioSelect,
    )


class HouseholdInformation(Page):
    form_model = 'player'
    form_fields = [
        'age_group', 'rent_status', 'monthly_rent_sek',
        'income_thousand_sek', 'income_not_disclosed', 'previous_power_plant_exposure',
    ]

    @staticmethod
    def is_displayed(player):
        return player.participant.eligible

    @staticmethod
    def vars_for_template(player):
        return dict(rent_question=RENT, income_question=INCOME, exposure_question=EXPOSURE)

    # Narrow framework adapter: ordinary self here, unlike oTree page callbacks.
    def get_form(self, instance, formdata=None):
        form = super().get_form(instance, formdata=formdata)
        if formdata is not None:
            prepare_numeric_fields(form)
        return form

    @staticmethod
    def before_next_page(player, timeout_happened):
        if not player.rent_status:
            player.monthly_rent_sek = None
        if player.income_not_disclosed:
            player.income_thousand_sek = None
        player.income_sek = income_in_sek(player.field_maybe_none('income_thousand_sek'))
        player.placeholder_completed = True
        player.participant.household_complete = True


page_sequence = [HouseholdInformation]
