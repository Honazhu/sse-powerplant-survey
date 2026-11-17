> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# Current questionnaire — V3.3

Native sequence: `eligibility → random_matrix → household → attitudes`. English wording and household coding from the prior questionnaire below remain authoritative except for the explicitly replaced Part D.

**Part A — Eligibility & Data Protection:** AgeConfirmation (18+) → research Introduction → VoluntaryParticipation with unchanged privacy/GDPR notice, consent and Cookie Preferences on the same page. Under 18 and participation refusal go to Exit. Cookie refusal/blocked cookies/no JavaScript do not exclude consenting adults. The same `participant.code` first appears after successful Part A, on Housing Instructions, and stays visible through Completion.

**Part B — Housing Choice:** ScenarioInstructions → Choice 1 → Choice 2 → Choice 3 → Choice 4. Exact V2.4 scenario, budget reminder, choice question and attributes are unchanged: eight sets, A/B blocks, two Nuclear/two Oil-fired, 10/50 km, 6500 SEK base and 0/500/1000/2000 premiums. Household remains unanswered during this part.

**Part C — Household Information:** HouseholdInformation follows Choice 4. Preserve Age Group, Rent Status and Monthly Rent in SEK, Net Monthly Personal Income after tax (raw thousands ×1000), and Previous Power Plant Exposure. Question text, code/validation/conditional missingness are unchanged. The exposure question's existing “I don't know” option is retained; removal of DK in this release applies only to Attitudes.

**Part D — Attitudes:** One AttitudeSurvey follows successful Household submission. Heading: **Part D — Attitudes**. Exact introduction:

> Finally, please indicate how much you agree or disagree with the following statements.

| Question | Existing variable | Exact statement |
| --- | --- | --- |
| Q1 | `nuclear_economic` | Nuclear power has a positive effect on Sweden's economy. |
| Q2 | `housing_cost` | Keeping my monthly housing costs low is a high priority when deciding where to live. |
| Q3 | `nuclear_support` | I support the use of nuclear power to generate electricity in Sweden. |
| Q4 | `nuclear_climate` | Nuclear power helps reduce greenhouse gas emissions. |
| Q5 | `nuclear_risk` | I would be concerned about safety risks if I lived near an operating nuclear power plant. |

| Raw / scored value | Exact label |
| ---: | --- |
| -2 | Strongly disagree |
| -1 | Slightly disagree |
| 0 | Neutral |
| +1 | Slightly agree |
| +2 | Strongly agree |

Five independent, genuinely draggable discrete sliders. No default answer, no DK 99, no Oppose/Support/Helps/Hinders or positive/negative option wording in the active attitude scale. All five fields are required. The same codes save with no JavaScript through native radio fallback. Error responses retain other choices; fresh GET/reload requires unsubmitted answers again. Zero only means actively chosen Neutral.

One Submit and Continue saves the complete page and opens existing Completion, with the same Reference ID. Completed DCE followed by Household dropout retains all four tasks and leaves Household/Attitudes missing. `SURVEY_FLOW_VERSION="V3.3"`, `ATTITUDES_VERSION="V3.3"`; `HOUSING_DESIGN_VERSION="V2.4"`. Housing canonical SHA-256 remains `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`.

Historical wording below describes the earlier order/Part D only. [Current scale rules](ATTITUDE_SCALE.md), [CSV integrity](CSV_INTEGRATION.md).

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# Questionnaire — V2.4 Housing / preserved V3.0 attitudes

**Power Plant Proximity & Housing Preferences Survey**  
Subtitle: **Stockholm School of Economics · Course 5327**.

English UI; local synthetic Pilot only. Part C presents two Nuclear and two Oil-fired contexts per participant. Q2–Q5 retain their V1.1 wording and share one HouseholdInformation page and one native page-duration observation.

## Part A — participation and reference

Introduction explains the neutral purpose: housing preferences in relation to power plant proximity, household circumstances and perspectives. Age screening comes first. Adults then see the short purpose/overview and the combined initial consent/privacy/cookie page before Household. Its exact consent question is: **Having read the participation and privacy information, do you voluntarily agree to take part?** Options: **Yes, I agree to participate.** (`True`), **No, I do not wish to participate.** (`False`). Field `willing_to_participate`; required Boolean radio. No skips all downstream questionnaires and shows Exit; age has already been confirmed. The consent page also explains voluntary stopping, completed-page timing, and the synthetic-only limitation.

### Privacy & Data Use — exact participant wording

Your participation in this survey is voluntary.

Your responses will be used for a university assignment at the Stockholm School of Economics and shared with the course instructor for assessment.

We do not ask for your name, email address, or exact home address. Your answers are linked to a Survey Reference ID.

If you wish to request the deletion of your survey response, please email:

**43086@student.hhs.se**

Please include your Survey Reference ID so that we can locate the relevant response.

Deletion requests will be reviewed in accordance with applicable data protection requirements.

### Q1a — Age confirmation

- Exact wording: **Q1a. Are you 18 years of age or older?**
- Options/codes: **Yes, I am 18 or older.** = True; **No, I am under 18.** = False.
- Field: `eligibility.Player.adult_confirmed`.
- Type/required: Boolean radio; required on the first page, before consent.
- Logic: Yes proceeds to Introduction then the combined consent/cookie page; eligibility remains False until participation is accepted. No goes directly to terminal Exit.
- Validation: native required/choice validation; no birth date or exact age.
- Tests: native adult/under-18/decline bots; forged Exit POST and browser direct Household URL.

Under-18 Exit wording:

**Thank you for your interest!**

Unfortunately, this survey is open only to participants aged 18 or above.

Thank you for your time and understanding.

### Q1b — Survey Reference ID (information only)

- Exact label: **Survey Reference ID**; displayed value: built-in `participant.code`.
- Control: **Copy ID** button; success **Copied**; selectable text/manual fallback if clipboard fails.
- No answer, required flag or new database field.
- Display condition: `participant.eligible` set only after consent and adult confirmation. First visible on Household, then Matrix, Attitudes and Completion. No badge on Introduction, Consent, Age or excluded Exit.
- First-display hint: **Please keep your Survey Reference ID if you may wish to request the deletion of your responses later.**
- Never derived from answers or treatment, never regenerated in the browser, no third-party transmission.
- Tests: eligibility bots; real browser clipboard/fallback, all-app consistency, reload and CSV join.

The combined VoluntaryParticipation page keeps the original optional cookie capability probe, choices, hidden status and script. A cookie choice is required only if participation is accepted; a participation refusal does not require one. Refusal, blocked cookies and no JavaScript do not exclude the participant. No extra consent/acknowledgement page is added.

## Part B — Household

All monetary amounts in this survey are expressed in Swedish kronor (SEK).

If you pay rent or receive income in another currency, please enter an approximate equivalent in SEK.

### Q2 — Age group

- Exact wording: **Q2. Which age group do you belong to?**
- Options/codes: 18–25=`18_25`; 26–35=`26_35`; 36–45=`36_45`; 46–55=`46_55`; 56–65=`56_65`; 66 or above=`66_plus`.
- Field: `age_group` (existing StringField, now required choices).
- Input/required: single radio; Yes.
- Conditional logic: Household only for eligible participants; all choices are adult categories.
- Validation: native required/allowed-choice checks. No exact date of birth.
- Module: `Q2_AgeGroup.html`, `questions.AGE`; native bot and CSV checks cover all six categories and missing/invalid choices.

### Q3 — Rent

- Q3a exact wording: **Q3a. Do you currently pay rent for your accommodation?**
- Options/codes: Yes=True, No=False.
- Field: `rent_status`; required Boolean radio.
- Description: **This includes renting an apartment, a room, or student accommodation.**
- Q3b exact wording: **Q3b. Approximately how much rent do you personally pay per month?**
- Field/input: `monthly_rent_sek`, IntegerField; numeric-keyboard text input labelled **SEK/month**.
- Instruction: **Please enter your monthly rent in SEK.**
- Required/conditional: required only if Q3a=True; otherwise hidden/disabled with JavaScript, ignored/cleared server-side and stored NULL, never zero.
- Validation: ASCII decimal digits representing a positive integer; no negative, decimal, sign, exponent, letter or whitespace-only input. Exact error: **Please enter a valid number.**
- Module: `Q3_HousingRent.html`, `questions.RENT`, `validation.rent_error`. Tests include missing, invalid, positive, zero rejection and stale valid/malformed clearing.

### Q4 — Net Monthly Personal Income — After Tax

- Exact wording: **Q4. Approximately what is your monthly personal income after tax?**
- Exact instruction: **Please enter your net monthly income, rounded to the nearest thousand SEK.**
- Fields: `income_thousand_sek` (raw integer input in thousands), `income_sek` (derived integer SEK), `income_not_disclosed` (Boolean checkbox).
- Input: numeric-keyboard text input, **× 1,000 SEK/month**.
- Examples: 15=15,000 SEK/month; 25=25,000; 40=40,000.
- Optionality: numeric answer required unless **Prefer not to say** is selected; no checkbox is preselected.
- Validation: nonnegative integer, including 0; same lexical restrictions/error as Q3. Refusal clears both numeric fields to NULL, flag=True. Actual zero gives both numbers=0 and flag=False.
- Conversion: `income_sek = income_thousand_sek * 1000`, only after successful server validation. No gross-income variable or automatic FX conversion.
- Module: `Q4_NetMonthlyIncome.html`, `questions.INCOME`, `validation.income_error` and `income_in_sek`; pure tests, native bots, browser and CSV checks.

### Q5 — Previous power plant exposure

- Exact wording: **Q5. Have you ever lived within approximately 20 kilometres of a power plant of any type?**
- Exact description: **This includes nuclear, coal, gas, or other electricity-generating power plants.**
- Options/codes: Yes=1; No=0; I don't know=2.
- Field: `previous_power_plant_exposure`, IntegerField with choices.
- Input/required: single radio; Yes.
- Conditional logic: eligible Household participants only.
- Validation: native required/choice checks. Unknown is kept distinct from No.
- No plant name, precise address, coordinates or location request.
- Module: `Q5_PowerPlantExposure.html`, `questions.EXPOSURE`; bots/CSV verify all three codes and reject missing/invalid choices.

## Part C — Housing Choice Experiment (V2.4)

One **Choosing a Rental Home** Instructions page follows Household, using the exact [scenario and budget wording](SCENARIO_FRAMING.md). It precedes four required choices and adds no new response. Instructions do not fix facility type, distance or A/B side.

Each Choice asks **Which home would you prefer to rent?**, with **Home A / Home B** cards and **Choose Home A / Choose Home B** radios, saved as A/B. The three card rows are **Power Plant Type**, **Distance to Power Plant**, **Monthly Rent**. Both cards show the full **Nuclear power plant** or **Oil-fired power plant** label. Size is held identical in the scenario and is not an attribute.

Each eligible entrant receives Block A or B, four unique frozen sets, two per facility and premiums 0/500/1000/2000. Distances are 10/50 km, near rent 6500 and far rent 6500+premium. Actual sides/order are randomized and persisted; all chosen properties come from the displayed profile. [Matrix](CHOICE_SET_MATRIX.md), [randomization](RANDOMIZATION_PLAN.md), [data dictionary](DATA_DICTIONARY.md).

No default response, opt-out attribute or new attitude question is introduced. Empty/invalid A/B submissions cannot advance. Refresh/replayed requests retain assignment and saved choices. Historical Part C wording is in the [pre-V2.4 source archive](history/pre_v2_4_source.zip).

## Part D — Nuclear & Economic Attitudes

One native **AttitudeSurvey** page follows the fourth Housing Choice. `ATTITUDES_VERSION=V3.0` is stored independently from all preserved Housing versions. The old preview template/1–10 fields remain historical; they are inactive in new sessions.

> We would now like to ask a few questions about your views on nuclear energy and housing costs. There are no right or wrong answers. Please select the response that best reflects your opinion.

**D1. Overall, how supportive are you of nuclear power as a source of electricity in Sweden?**

-2 = Strongly oppose; -1 = Somewhat oppose; 0 = Neither support nor oppose; +1 = Somewhat support; +2 = Strongly support.

**D2. I would be concerned about safety risks if I lived near an operating nuclear power plant.**

-2 = Strongly disagree; -1 = Somewhat disagree; 0 = Neither agree nor disagree; +1 = Somewhat agree; +2 = Strongly agree.

**D3. Overall, how do you think nuclear power affects Sweden's economy?**

-2 = Very negatively; -1 = Somewhat negatively; 0 = Neither positively nor negatively; +1 = Somewhat positively; +2 = Very positively; 99 = I don't know.

**D4. In your view, does nuclear power help or hinder efforts to reduce greenhouse gas emissions?**

-2 = Strongly hinders; -1 = Somewhat hinders; 0 = Neither helps nor hinders; +1 = Somewhat helps; +2 = Strongly helps; 99 = I don't know.

**D5. Keeping my monthly housing costs low is a high priority when deciding where to live.**

-2 = Strongly disagree; -1 = Somewhat disagree; 0 = Neither agree nor disagree; +1 = Somewhat agree; +2 = Strongly agree.

All five are required, with no default answer. D3/D4 can be answered “I don't know” (raw 99, score missing, DK=1); it is outside the ordered scale and its code is not shown to participants. Neutral 0 stays 0. Missing/unsubmitted values remain missing. Scores are ordinal, not assumed equally spaced. See [ATTITUDE_SCALE](ATTITUDE_SCALE.md) for full labels, coding and post-choice priming limitations.

A single **Submit and Continue** button saves the five valid native answers together. Completion heading: **Completion**; introduction: **Thank you for completing the questionnaire.** Panel: **Your responses have been saved** / **You have completed the housing choices and attitude questions. Thank you. You may close this window.** Note: **This was a synthetic Pilot of a student course project, using invented responses.** There is no further submit button. The same Survey Reference ID remains visible.

## Remaining research decisions

Researcher decision: implemented Q4 is personal after-tax income. The handover mentions a research-report recommendation for household after-tax income plus household size. The report file was not present, and neither the implemented question nor its interpretation was changed. Household size, residence country and housing familiarity were not added.

No real data collection is enabled. Privacy notice approval, controller/legal basis, retention and hosting arrangements are still pending; the new wording is not a declaration of GDPR compliance.
