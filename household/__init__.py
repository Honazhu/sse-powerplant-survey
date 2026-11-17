from otree.api import *
from timing import ConsentTimingPage, export_page_durations
from .countries import COUNTRIES
from .questions_v5 import CHILDREN, EDUCATION

class C(BaseConstants):
    NAME_IN_URL = 'household'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
class Subsession(BaseSubsession): pass
class Group(BaseGroup): pass
class Player(BasePlayer):
    age_group = models.StringField(label='Which age group do you belong to?', choices=[('18_25','18–25'),('26_35','26–35'),('36_45','36–45'),('46_55','46–55'),('56_65','56–65'),('66_plus','66+'),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect)
    gender = models.StringField(label='What is your gender?', choices=[('male','Male'),('female','Female'),('non_binary','Non-binary'),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect)
    residence_code = models.StringField(label='In which country or region do you currently live?', choices=COUNTRIES + [('unable','Unable to select'),('prefer_not','Prefer not to say')])
    main_activity = models.StringField(label='Which of the following best describes your main activity?', choices=[('student','Student'),('employed','Employed'),('self_employed','Self-employed'),('unemployed','Unemployed'),('retired','Retired'),('caregiver','Homemaker or caregiver'),('other','Other'),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect)
    rent_status_final = models.StringField(label='Do you currently pay rent or a mortgage for your accommodation?', choices=[('yes','Yes'),('no','No'),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect)
    monthly_rent_sek = models.IntegerField(label='Amount (SEK per month)', min=0, max=100000000, blank=True)
    rent_missing_reason = models.StringField(label='Or select one option', choices=[('dont_know',"Don't know"),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect, blank=True)
    household_income_after_tax = models.IntegerField(label='Amount (SEK per month)', min=0, max=100000000, blank=True)
    income_missing_reason = models.StringField(label='Or select one option', choices=[('dont_know',"Don't know"),('prefer_not','Prefer not to say')], widget=widgets.RadioSelect, blank=True)
    children_under_18 = models.StringField(label='Do any children under 18 live in your household?', choices=CHILDREN, widget=widgets.RadioSelect)
    education_completed = models.StringField(label='What is the highest level of education you have completed?', choices=[(k, 'Prefer not to say' if k == 'prefer_not' else v) for k,v in EDUCATION], widget=widgets.RadioSelect)
    additional_feedback = models.LongStringField(label='Is there any additional information, remarks, or feedback you would like to share?', blank=True)
    household_completed = models.BooleanField(initial=False)

class HouseholdInformation(ConsentTimingPage):
    form_model = 'player'
    form_fields = ['age_group','gender','residence_code','main_activity','rent_status_final','monthly_rent_sek','rent_missing_reason','household_income_after_tax','income_missing_reason','children_under_18','education_completed','additional_feedback']
    @staticmethod
    def is_displayed(player):
        return player.participant.eligible
    @staticmethod
    def error_message(player, values):
        errors = {}
        for amount, reason in [('household_income_after_tax','income_missing_reason')]:
            if (values[amount] is None) == (not values[reason]):
                errors[reason] = 'Enter an amount or choose one option, but not both.'
        if values['rent_status_final'] == 'yes' and ((values['monthly_rent_sek'] is None) == (not values['rent_missing_reason'])):
            errors['rent_missing_reason'] = 'Enter an amount or choose one option, but not both.'
        if values.get('additional_feedback') and len(values['additional_feedback']) > 1500:
            errors['additional_feedback'] = 'Please use at most 1,500 characters.'
        return errors or None
    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.rent_status_final != 'yes':
            player.monthly_rent_sek = None
            player.rent_missing_reason = None
        from completion_final import validate_complete
        validate_complete(player)
        player.household_completed = True
        player.participant.household_complete = True
        player.participant.finished = True

class Completion(ConsentTimingPage):
    @staticmethod
    def is_displayed(player):
        return player.participant.eligible and player.participant.finished and player.household_completed
page_sequence = [HouseholdInformation, Completion]

def custom_export(players):
    from completion_final import export_completed
    yield from export_completed(players)

def custom_export_timing(players):
    from completion_final import validate_complete
    eligible = []
    for p in players:
        if p.session.config.get('data_class') == 'production' and p.participant.finished and p.participant.cookies_allowed is True:
            validate_complete(p)
            eligible.append(p)
    yield from export_page_durations(eligible)
