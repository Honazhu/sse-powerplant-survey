"""V1 wording and stable codes. Change one question without redefining model fields."""
AGE = dict(wording='Q2. Which age group do you belong to?', choices=[
    ['18_25', '18–25'], ['26_35', '26–35'], ['36_45', '36–45'],
    ['46_55', '46–55'], ['56_65', '56–65'], ['66_plus', '66 or above'],
])
RENT = dict(
    wording='Q3a. Do you currently pay rent for your accommodation?',
    choices=[[True, 'Yes'], [False, 'No']],
    amount_wording='Q3b. Approximately how much rent do you personally pay per month?',
    description='This includes renting an apartment, a room, or student accommodation.',
    instruction='Please enter your monthly rent in SEK.',
)
INCOME = dict(
    wording='Q4. Approximately what is your monthly personal income after tax?',
    instruction='Please enter your net monthly income, rounded to the nearest thousand SEK.',
    refusal='Prefer not to say',
)
EXPOSURE = dict(
    wording='Q5. Have you ever lived within approximately 20 kilometres of a power plant of any type?',
    description='This includes nuclear, coal, gas, or other electricity-generating power plants.',
    choices=[[1, 'Yes'], [0, 'No'], [2, "I don't know"]],
)
