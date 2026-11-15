"""V3.0 question-level wording, codes and export mappings; no oTree imports."""
ATTITUDES_VERSION = 'V3.0'
TITLE = 'Part D — Nuclear & Economic Attitudes'
INTRODUCTION = ('We would now like to ask a few questions about your views on nuclear energy and housing costs. '
                'There are no right or wrong answers. Please select the response that best reflects your opinion.')
SCORES = (-2, -1, 0, 1, 2)
DK_CODE = 99


def question(number, field, wording, labels, *, allow_dk=False):
    return dict(number=number, field=field, wording=wording,
                choices=list(zip(SCORES, labels)) + ([(DK_CODE, "I don't know")] if allow_dk else []),
                allow_dk=allow_dk, score_field=field + '_score',
                dk_field=field + '_dk' if allow_dk else None)


SUPPORT = question('D1', 'nuclear_support',
    'Overall, how supportive are you of nuclear power as a source of electricity in Sweden?',
    ['Strongly oppose', 'Somewhat oppose', 'Neither support nor oppose', 'Somewhat support', 'Strongly support'])
RISK = question('D2', 'nuclear_risk',
    'I would be concerned about safety risks if I lived near an operating nuclear power plant.',
    ['Strongly disagree', 'Somewhat disagree', 'Neither agree nor disagree', 'Somewhat agree', 'Strongly agree'])
ECONOMIC = question('D3', 'nuclear_economic',
    "Overall, how do you think nuclear power affects Sweden's economy?",
    ['Very negatively', 'Somewhat negatively', 'Neither positively nor negatively', 'Somewhat positively', 'Very positively'],
    allow_dk=True)
CLIMATE = question('D4', 'nuclear_climate',
    'In your view, does nuclear power help or hinder efforts to reduce greenhouse gas emissions?',
    ['Strongly hinders', 'Somewhat hinders', 'Neither helps nor hinders', 'Somewhat helps', 'Strongly helps'],
    allow_dk=True)
HOUSING_COST = question('D5', 'housing_cost',
    'Keeping my monthly housing costs low is a high priority when deciding where to live.',
    ['Strongly disagree', 'Somewhat disagree', 'Neither agree nor disagree', 'Somewhat agree', 'Strongly agree'])
QUESTIONS = (SUPPORT, RISK, ECONOMIC, CLIMATE, HOUSING_COST)
BY_FIELD = {q['field']: q for q in QUESTIONS}
RAW_FIELDS = [q['field'] for q in QUESTIONS]
SCORE_FIELDS = [q['score_field'] for q in QUESTIONS]
DK_FIELDS = [q['dk_field'] for q in QUESTIONS if q['allow_dk']]
