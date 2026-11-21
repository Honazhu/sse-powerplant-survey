# V4 → V5 schema and wording changes

The formal V5 custom export is a new respondent-wide schema; it is never appended to V4 headers. `survey_version=5.0.0`, housing wording 5.0.0, treatment V5.0, numeric matrix V2.4, and attitudes V3.3 are separate provenance concepts. A complete row has six sets of `choice_1_…` through `choice_6_…` and the full validated randomized `assignment_json`. See `docs/V5_DATA_DICTIONARY.md` and the local source for every allowed code.

| V4 field / wording | V5 | Type / notes |
|---|---|---|
| Separate age and Welcome pages | Combined Welcome + `adult_confirmed` | Boolean; old pages and historical values are not migrated |
| Optional browser cookie probe | `cookies_allowed` | Boolean true/false, unanswered defaults false after participation consent; timing now controlled independently of participation |
| Four V2.4 questions, A/B block | Six stratified 3 nuclear + 3 oil | V2.4 profiles unchanged; V5 treatment and wording version; choice positions 1–6 |
| `age_group` | same | Six ordered adult categories |
| No active residence question | `residence_code` | Frozen ISO alpha-2 plus unable/prefer_not; local mapping `household/countries.py` |
| `income_thousand_sek`, `income_sek`, `income_not_disclosed` | `income_category` | **Net monthly personal income** scope preserved; ordered ranges plus dont_know/prefer_not; no midpoint or zero inference |
| `rent_status`, numeric `monthly_rent_sek` | `rent_status`, `rent_category` | Yes/No question now includes mortgage; six ranges; null when No |
| No children question | `children_under_18` | yes/no/prefer_not |
| No education question | `education_completed` | Ordered primary/lower_secondary/upper_secondary/bachelor/master/doctorate; prefer_not |
| `previous_power_plant_exposure` | no longer asked/exported in V5 | Historical DB field retained; hypothetical experimental distance remains |
| Five V3.3 attitudes | unchanged | Integer -2…2, with zero a valid answer |

Original historical numerical and exposure model columns remain in code to avoid redefining their prior meaning; this does not establish in-place DB compatibility. V4 formal exports must be produced using V4 software and kept separate. V5 uses a fresh database, not NULL padding to simulate a conversion. Original V4 had no active gender question in the inspected flow; none was removed.
