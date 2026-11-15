> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# V3.3 — Five-point agreement sliders

Heading: **Part D — Attitudes**. Introduction: **Finally, please indicate how much you agree or disagree with the following statements.**

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

Mapping is `Question ID → Existing variable → Raw code → Scored value`: every Q1–Q5 stores the chosen integer in its named variable and derives the identical integer in `<variable>_score`. In particular Q1 never writes nuclear_support; Q3 does. Display order differs from preserved CSV/declaration order (support, risk, economic, climate, housing_cost). Tests independently cover every question and every code, plus a native/browser submission with distinct scores across the five constructs.

All fields are required with allowed values −2, −1, 0, 1, 2. There is no unanswered default. Higher economic/support/climate indicates stronger agreement with the positive statement; higher housing_cost means priority on lower costs; higher nuclear_risk means stronger safety concern, with no reversal or composite calculation. Scores remain ordinal.

The normal UI is five native `input[type=range]` controls with min −2, max 2, step 1; mouse/touch/track/keyboard use the same discrete positions. Blank state says Not answered and has no selected thumb/label. Initialization/focus cannot select Neutral. Only explicit interaction checks one canonical native radio; ranges have no names. Without JavaScript, accessible five-option radios remain visible and required server-side. No duplicate named range/hidden field exists.

Server native choice validation plus the narrow lexical/multiplicity adapter rejects omissions, blanks, 99, −3, 3, fractions, text and duplicate field values. All five save atomically through the ordinary form; invalid submissions save none and rerender valid choices checked near the respective sliders. The corrected field error clears on interaction. Fresh GET/reload intentionally clears unsaved browser selections; submitted responses survive refresh/replay/restart. There is no local/session storage and no per-slider timing.

**Historical compatibility:** V3.3 removes DK from all five questions; V3.0 economic/climate raw 99 remains raw 99 with score blank and DK=1. V3.0 ordinal answers and V3.3 answers have DK=0 in the two retained economic/climate indicator columns. Unsubmitted raw/score/DK are all blank, never0; version/completion false alone is not exposure. Unversioned historical preview data remains historical_unavailable, with no inferred answers. The existing `attitudes/exports.py` dispatches by saved version; historical data is neither rewritten nor relabelled. The exact prior definitions remain in `legacy_questions_v30.py` and below.

`SURVEY_FLOW_VERSION="V3.3"`, `ATTITUDES_VERSION="V3.3"`; `HOUSING_DESIGN_VERSION="V2.4"`. Housing canonical SHA-256 remains `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`.

Current flow is Part A screening/consent/cookies → Part B V2.4 Nuclear/Oil-fired choices → Part C Household → Part D Attitudes → Completion. These are post-choice measures; do not infer pretreatment traits or causal attitude effects. No formal WTP estimator is added. Older Coal references below describe historical releases only.

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# V3.0 attitude scale

`ATTITUDES_VERSION = "V3.0"`. These five required questions appear together on the native AttitudeSurvey page after four Housing Choices. The section is **Part D — Nuclear & Economic Attitudes**.

> We would now like to ask a few questions about your views on nuclear energy and housing costs. There are no right or wrong answers. Please select the response that best reflects your opinion.

There is no preselected answer, free text, numeric entry or default neutral response. All five questions require a choice; D3 and D4 permit “I don't know” as a valid response to the question, outside its ordered scale. One **Submit and Continue** button saves the page and opens Completion.

## D1 — nuclear_support

**Overall, how supportive are you of nuclear power as a source of electricity in Sweden?**

| Raw code | Exact response label | Analysis score | DK indicator |
| --- | --- | --- | --- |
| -2 | Strongly oppose | -2 | Not applicable |
| -1 | Somewhat oppose | -1 | Not applicable |
| 0 | Neither support nor oppose | 0 | Not applicable |
| +1 | Somewhat support | 1 | Not applicable |
| +2 | Strongly support | 2 | Not applicable |

## D2 — nuclear_risk

**I would be concerned about safety risks if I lived near an operating nuclear power plant.**

| Raw code | Exact response label | Analysis score | DK indicator |
| --- | --- | --- | --- |
| -2 | Strongly disagree | -2 | Not applicable |
| -1 | Somewhat disagree | -1 | Not applicable |
| 0 | Neither agree nor disagree | 0 | Not applicable |
| +1 | Somewhat agree | 1 | Not applicable |
| +2 | Strongly agree | 2 | Not applicable |

## D3 — nuclear_economic

**Overall, how do you think nuclear power affects Sweden's economy?**

| Raw code | Exact response label | Analysis score | DK indicator |
| --- | --- | --- | --- |
| -2 | Very negatively | -2 | 0 |
| -1 | Somewhat negatively | -1 | 0 |
| 0 | Neither positively nor negatively | 0 | 0 |
| +1 | Somewhat positively | 1 | 0 |
| +2 | Very positively | 2 | 0 |
| 99 | I don't know | Missing | 1 |

## D4 — nuclear_climate

**In your view, does nuclear power help or hinder efforts to reduce greenhouse gas emissions?**

| Raw code | Exact response label | Analysis score | DK indicator |
| --- | --- | --- | --- |
| -2 | Strongly hinders | -2 | 0 |
| -1 | Somewhat hinders | -1 | 0 |
| 0 | Neither helps nor hinders | 0 | 0 |
| +1 | Somewhat helps | 1 | 0 |
| +2 | Strongly helps | 2 | 0 |
| 99 | I don't know | Missing | 1 |

## D5 — housing_cost

**Keeping my monthly housing costs low is a high priority when deciding where to live.**

| Raw code | Exact response label | Analysis score | DK indicator |
| --- | --- | --- | --- |
| -2 | Strongly disagree | -2 | Not applicable |
| -1 | Somewhat disagree | -1 | Not applicable |
| 0 | Neither agree nor disagree | 0 | Not applicable |
| +1 | Somewhat agree | 1 | Not applicable |
| +2 | Strongly agree | 2 | Not applicable |

## Coding, missingness and direction

The five category codes −2/−1/0/1/2 are **ordinal**. Storage as numeric scores does not establish equal psychological distances, justify automatic averaging or define a common latent scale across the five questions. No composite score, risk reversal, standardized index or WTP model is calculated.

Higher D1 indicates support, higher D2 indicates stronger agreement with safety concern, higher D3 indicates a more positive perceived economic effect, higher D4 indicates more perceived help reducing emissions, and higher D5 indicates greater priority on low housing costs. In particular, higher D2 is not a generally “more positive” attitude.

Native fields `nuclear_support`, `nuclear_risk`, `nuclear_economic`, `nuclear_climate`, `housing_cost` preserve exact raw integer choices. The old 1–10 preview fields remain unused and retain their historical meanings; they are not recoded.

| Situation | Raw field | *_score | D3/D4 *_dk | attitudes_completed / status |
| --- | --- | --- | --- | --- |
| Neutral submitted | 0 | 0 | 0 | 1 / submitted |
| Don't know submitted (D3/D4 only) | 99 | Missing | 1 | 1 / submitted |
| Other submitted category | −2/−1/1/2 | Same category | 0 | 1 / submitted |
| Current page not submitted, including selected browser radios | Missing | Missing | Missing | 0 / not_submitted |
| Historical preview with no V3 metadata | Missing | Missing | Missing | Missing / historical_unavailable |
| No matching row supplied to merge | Missing | Missing | Missing | Missing / missing_export_row |

99 is strictly a raw special response code. It never appears as a numeric score or respondent-facing label. DK flags are blank for unanswered questions, so a blank is not incorrectly interpreted as an informed ordinal response. Invalid/missing form responses prevent the whole page from saving; valid fields on an invalid submission are not counted as submitted answers. Selected but unsubmitted browser values are not autosaved. Native page timing remains the only page-exposure/completion timing mechanism; a saved submission timestamp additionally identifies final response submission.

The new nullable `attitudes_version` and completion/timestamp fields have no historical backfill. Only fresh sessions receive V3.0 and a false completion status; successful submission sets true. Legacy `attitudes.completed` mirrors successful V3 submission for current routing, while its historical true value only meant that a preview was passed. It must never be used to infer historical V3 responses.

## Modular maintenance

`attitudes/questions.py` defines each question separately: number, native field, wording, choices, DK permission and score/DK export names. `validation.py` validates against that question's permitted codes and maps raw→score/DK with explicit None handling. `__init__.py` declares five separate IntegerFields and one native form. Five question templates independently include a reusable accessible radio renderer. `exports.py` uses the same field mappings and validates completion/version/raw/score consistency. Changing a scale or wording requires a new attitude version; do not silently reinterpret older V3 records.

## Post-choice priming and treatment relationship

The section is asked **after** two Nuclear and two Coal housing tasks. The attitude questions refer to nuclear energy and housing costs generally; there is no additional Coal attitude battery or new randomization. A participant's one attitude response set repeats across that person's four task rows when merged, including both facility contexts. It is not four independent attitude observations.

Prior contexts, their order, contrast, fatigue or consistency-seeking may affect these responses. They are post-choice measures, not demonstrated pretreatment traits. Do not automatically treat them as baseline confounders, causal moderators or independent evidence of pre-existing risk perceptions; conditioning on post-treatment measures can change the interpretation of later estimates. D2 has no precise distance and must not be equated mechanically with the DCE's Near20 contrast. Preserve saved task order/type and Housing wording/treatment versions for future descriptive or separately justified sensitivity work. This release implements no attitude effects or WTP regression.

The unchanged Housing numeric matrix is V2.0, complete treatment design V2.3 and wording V2.2b. Nuclear WTP remains the main research question; adding these responses does not change the DCE estimand or establish sufficient precision. Human Pilot checks should assess label comprehension, neutral-versus-DK distinction, question length, and possible order/context salience.
