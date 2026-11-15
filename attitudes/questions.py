"""V3.3 statements; display order is independent of the stable native/CSV fields."""
ATTITUDES_VERSION = 'V3.3'
TITLE = 'Part D — Attitudes'
INTRODUCTION = 'Finally, please indicate how much you agree or disagree with the following statements.'
SCORES = (-2, -1, 0, 1, 2)
LABELS = ('Strongly disagree', 'Slightly disagree', 'Neutral', 'Slightly agree', 'Strongly agree')
DK_CODE = 99  # Historical V3.0 only; never a V3.3 choice.


def question(number, field, wording):
    return dict(number=number, field=field, wording=wording,
                choices=list(zip(SCORES, LABELS)), allow_dk=False,
                score_field=field + '_score',
                dk_field=field + '_dk' if field in ('nuclear_economic', 'nuclear_climate') else None)


ECONOMIC = question('Q1', 'nuclear_economic',
    "Nuclear power has a positive effect on Sweden's economy.")
HOUSING_COST = question('Q2', 'housing_cost',
    'Keeping my monthly housing costs low is a high priority when deciding where to live.')
SUPPORT = question('Q3', 'nuclear_support',
    'I support the use of nuclear power to generate electricity in Sweden.')
CLIMATE = question('Q4', 'nuclear_climate',
    'Nuclear power helps reduce greenhouse gas emissions.')
RISK = question('Q5', 'nuclear_risk',
    'I would be concerned about safety risks if I lived near an operating nuclear power plant.')
QUESTIONS = (ECONOMIC, HOUSING_COST, SUPPORT, CLIMATE, RISK)
BY_FIELD = {q['field']: q for q in QUESTIONS}
FORM_FIELDS = [q['field'] for q in QUESTIONS]
# Preserve CSV column order and constructs across releases.
RAW_FIELDS = ['nuclear_support', 'nuclear_risk', 'nuclear_economic', 'nuclear_climate', 'housing_cost']
SCORE_FIELDS = [field + '_score' for field in RAW_FIELDS]
DK_FIELDS = ['nuclear_economic_dk', 'nuclear_climate_dk']
