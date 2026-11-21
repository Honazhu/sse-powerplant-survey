ATTITUDES_VERSION = 'final'
TITLE = 'Attitudes'
INTRODUCTION = 'Please choose one answer for each question.'

def question(field, wording, labels, missing):
    return dict(field=field, wording=wording, choices=list(zip([2, 1, 0, -1, -2, 99], labels + [missing])), missing=missing)

ECONOMIC = question('nuclear_economic', "What effect, if any, does nuclear power have on Sweden's economy?", ['Very positive', 'Somewhat positive', 'No effect', 'Somewhat negative', 'Very negative'], "Don't know")
CLIMATE = question('nuclear_climate', 'How much, if at all, does nuclear power reduce greenhouse gas emissions compared with fossil fuels?', ['A great deal', 'A lot', 'A moderate amount', 'A little', 'Not at all'], "Don't know")
SUPPORT = question('nuclear_support', 'How much do you support or oppose using nuclear power to generate electricity in Sweden?', ['Strongly support', 'Somewhat support', 'Neither support nor oppose', 'Somewhat oppose', 'Strongly oppose'], 'Prefer not to say')
RISK = question('nuclear_risk', 'How concerned would you be about safety if you lived near an operating nuclear power plant?', ['Extremely concerned', 'Very concerned', 'Somewhat concerned', 'Slightly concerned', 'Not at all concerned'], 'Prefer not to say')
HOUSING_COST = question('housing_cost', 'When choosing where to live, how important is keeping your monthly housing cost low?', ['Extremely important', 'Very important', 'Somewhat important', 'Slightly important', 'Not at all important'], 'Prefer not to say')
QUESTIONS = (ECONOMIC, CLIMATE, SUPPORT, RISK, HOUSING_COST)
BY_FIELD = {q['field']: q for q in QUESTIONS}
FORM_FIELDS = [q['field'] for q in QUESTIONS]
