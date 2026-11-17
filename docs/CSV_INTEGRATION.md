> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# V3.3 CSV integration and partial-response integrity

The same pipeline and composite string keys are retained: `(session_code, participant_code)`. All matching uses codes, never module position, row number or demographics.

Native wide → existing version-dispatched DCE adapter → DCE difference (task base) → **left join Household/status** → **left join version-aware Attitudes wide** → analysis_merged. Both joins validate many-to-one cardinality. Unique keys, complete native-source agreement, A−B differences, input hash audit and output overwrite refusal remain mandatory.

| File | Grain | V3.3 behavior |
| --- | --- | --- |
| all_apps_wide / per-app native | Participant/session; native DCE per-app has four rounds | Housing fields stay V2.4; flow session/eligibility values V3.3; attitude raw/version V3.3 |
| dce_wide |1/participant/session | Four actual/planned task slots, independent of missing Household |
| dce_tasks / dce_difference |4/participant/session | Block, set, type, profiles, chosen fields and all missing outcomes retained |
| dce_long |8/participant/session | Two alternatives/task, chosen missing for unanswered tasks |
| attitudes_wide |1/participant/session | Original column order/schema retained; version-specific raw/score/DK validation |
| analysis_merged |Same task rows as difference | Household may be submitted later or remain missing; no expansion/filtering |

`SURVEY_FLOW_VERSION="V3.3"`, `ATTITUDES_VERSION="V3.3"`; `HOUSING_DESIGN_VERSION="V2.4"`. Housing canonical SHA-256 remains `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`. New native flow provenance is checked against session config, and V3.3 attitudes requires V3.3 flow. Historical absent flow remains blank. Existing Housing survey_version continues to mean V2.4, not the overall questionnaire release. New merged aliases dce_completed and household_completed expose existing completion sources without changing the original columns.

V3.3 Q1 economic→nuclear_economic, Q2 housing_cost→housing_cost, Q3 support→nuclear_support, Q4 climate→nuclear_climate, Q5 risk→nuclear_risk. Allowed raw codes−2…2 map identically to scores.99 is invalid for any V3.3 field. Historical V3.0 economic/climate raw 99 is retained, score Missing, DK 1; it is never0. The same adapter reads frozen V3.0 definitions. Missing historical versions/fields are not filled from current scores. Unknown explicit versions fail.

Dropout immediately after DCE: four saved choices/block/set/facility remain; dce_completed1, household_completed0, attitudes_completed0, all Household/Attitude answers Missing. For1–3 choices, completed choices remain, future choices Missing and dce_completed0. All four assigned tasks survive. A missing attitude export row is still permitted and flagged missing_export_row; a known unsubmitted row remains not_submitted. These cases are distinct from neutral0 and historical DK.

CLI commands below remain current and refuse old output paths. [V3.3 handover](V3_3_COMPLETION.md) links native, wide, tasks, long, difference, attitudes and merged examples and source hashes. No formal WTP regression is run.

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# V2.4 Housing CSV integration

Native oTree wide export remains one row per participant. `scripts/export_dce.py` dispatches by saved housing survey version: V2.4 → `exports_v24.py`; V2.0/V2.2b (including design V2.3) → frozen `legacy_v23/exports.py`. Mixed V2.4/historical files are rejected. Existing source and output CSVs are never overwritten. Historical Coal/size/10–30km values and missing attributes retain their meaning.

V2.4 emits one-row-per-person dce_wide; four-row-per-person dce_tasks/dce_difference; eight-row-per-person dce_long. All four planned tasks survive partial completion. Native `choice_set_id`, `choice`, `A_distance_km`, `A_rent_sek_month`, `A_near20` are retained; aliases are `set_id`, `choice_ab`, `home_A_distance_km`, `home_A_rent_sek`, `home_A_near20` (likewise B). Chosen facility/distance/rent/far are independently saved from displayed choice and validated against A/B before export. Completion and duration distinguish missing outcomes from real zeros. Long alternative_id=A/B and chosen indicators are both blank when unanswered, exactly one 1 after response.

V2.4 model columns: chose_A, delta_rent_1000, delta_far, delta_far_x_oil, plus oil/type/set/index/codes/versions. All differences use A−B. No delta_size_m2 or Coal variable is emitted. Block ID is a string A/B in new native/derived data. The validated V3 attitude merge supports this schema and keeps historical schema separate; no attitude question or score mapping changed. [Dictionary](DATA_DICTIONARY.md), [model](V2_4_DESIGN_SPECIFICATION.md), [actual native](../data/synthetic/v2_4_browser_1794762133050201000/all_apps_wide.csv), [tasks](../data/synthetic/v2_4_browser_1794762133050201000/dce_tasks.csv), [difference](../data/synthetic/v2_4_browser_1794762133050201000/dce_difference.csv).

[UI_TESTING](UI_TESTING.md) records native/custom equality, all analysis-format consistency, joins and history/overwrite rejection. Existing CLI commands below remain valid with a new V2.4 native source and a new output directory.

---

# Historical V3 integration notes (pre-V2.4 Housing)

The following DCE references to Coal, numerical block IDs and size describe the earlier version only; V3 attitude definitions remain current.

# V3.0 CSV integration

This pipeline only validates, reshapes and joins data. It does not estimate coefficients, impute attitudes, score an overall index or calculate WTP. Keep untouched native CSVs and generated audit JSON together. Examples under `data/synthetic/` are invented Pilot data only.

## Sources, keys and grain

| Dataset | Grain / key | Role |
| --- | --- | --- |
| all_apps_wide.csv | One slot per (`session.code`, `participant.code`) | Native raw Household, four DCE rounds, attitude responses, versions and survey status |
| eligibility.csv / household.csv / attitudes.csv | Native app Player row | Standard oTree per-app exports; attitude raw fields also here |
| random_matrix.csv | Native task Player row | Four rounds per participant |
| random_matrix_custom.csv | Participant × task | Existing normalized task export, unchanged |
| attitudes_custom.csv | Participant × completed page | **Existing whole-survey timing export**, unchanged; not attitude-wide data |
| dce_wide.csv | (`session_code`, `participant_code`) | Existing participant DCE layout, unchanged |
| dce_tasks.csv / dce_difference.csv | (`session_code`, `participant_code`, `task_index`) | Four rows per slot, including unassigned/unanswered tasks |
| dce_long.csv | Task key plus `apartment` | Two alternatives per task, eight rows per slot; unchanged |
| attitudes_wide.csv | (`session_code`, `participant_code`) | New unique raw/scored attitude table, one row per native slot |
| analysis_merged.csv | DCE difference task key | Task-left-join of validated Household/status and attitudes |
| merge_audit.json | One pipeline invocation | Input hashes, versions, counts, key checks, unmatched participants and missing scores |

Both codes are **strings**, preserved exactly, including leading zeros and literal `NA`. The CLI reads with `dtype=str, keep_default_na=False, na_filter=False`, rejects duplicate CSV headers and rejects empty or whitespace-altered join keys. IDs are never regenerated, derived from answers/seeds, or matched by row order. The same simulated participant code in two different sessions remains two distinct keys.

## Export commands

From the source project with the existing venv active, after downloading native `all_apps_wide.csv` from an isolated synthetic Pilot:

```sh
python scripts/export_dce.py --input /path/all_apps_wide.csv --output-dir /path/new_exports
python analysis/merge_attitudes.py \
  --native /path/all_apps_wide.csv \
  --dce-difference /path/new_exports/dce_difference.csv \
  --attitudes /path/new_exports/attitudes_wide.csv \
  --output-dir /path/new_merged
```

The first command reuses the unchanged DCE transformer and adds `attitudes_wide.csv` alongside its four existing outputs. The second reuses both pure export adapters, validates source agreement and writes `analysis_merged.csv` plus `merge_audit.json`. Both refuse existing output filenames. Neither imports oTree models, opens a database, modifies input CSVs or drops incomplete DCE tasks. No external analysis service is used. Installed Pandas 2.3.3 supplies many-to-one validation; no dependency was upgraded.

## Attitudes-wide schema

| Columns | Type / interpretation |
| --- | --- |
| session_code, participant_code | Nonempty strings, unique pair |
| study_mode, data_class | Native session provenance; current Pilot is pilot/synthetic |
| attitudes_version | V3.0 for new sessions; historical absent remains blank |
| attitudes_completed | 1 only on valid submission; 0 for current unsubmitted; historical unknown blank |
| attitudes_submitted_at | Positive finite Unix seconds on successful submission, otherwise blank |
| attitudes_status | submitted / not_submitted / historical_unavailable |
| nuclear_support, nuclear_risk, nuclear_economic, nuclear_climate, housing_cost | Native raw integer response; D3/D4 allow 99; unanswered blank |
| nuclear_support_score, nuclear_risk_score, nuclear_economic_score, nuclear_climate_score, housing_cost_score | −2/−1/0/1/2 or blank; **never 99** |
| nuclear_economic_dk, nuclear_climate_dk | 1=DK, 0=submitted ordinal answer, blank=unanswered/unknown |

Native prefixes are `attitudes.1.player.<field>`; per-app uses `player.<field>`. Score, DK and status columns are reproducibly derived, not duplicate database fields. All raw values and completion metadata remain available in Native CSV. Neutral 0 is a response, not False or Missing. [ATTITUDE_SCALE](ATTITUDE_SCALE.md) documents exact labels, directions and ordinal interpretation.

## Merge procedure and strict validation

1. Validate nonempty string keys and uniqueness: native one per slot, attitudes one per slot, differences one per participant×task. Duplicate inputs fail before joining; no Cartesian expansion is allowed.
2. Recreate expected DCE differences from the supplied native export using the existing snapshot-aware transformer. Compare keys, all fields, versions and row counts with the supplied difference file. A mismatched export, facility, rent, choice or snapshot fails. This interface expects the complete canonical difference export, not a previously filtered analysis subset.
3. Validate attitude raw codes, permitted DK codes, version, completion and submission timestamp; derive scores/status and compare with supplied values. Current V3 session metadata cannot silently fall back to “historical.” Submitted attitudes also require native eligibility, Household completion, four DCE answers and survey completion. Old preview completion alone is insufficient.
4. Compare each supplied attitude row to the native source under the full key. Conflicting versions/answers or an attitude key absent from the native source fail. Missing attitude rows are allowed and explicitly reported.
5. Left-join Household/status and then attitudes to the DCE task base, each with `validate='many_to_one'`, explicit composite keys and merge indicators. Assert unchanged row count and unique output task keys. Preserve all DCE task rows, including missing choices and exclusions.
6. Convert integer responses/flags to nullable `Int64`, numerical differences/durations to nullable `Float64`; retain identifiers, versions, labels and JSON snapshots as strings. Integer SEK values are parsed without a float intermediary. Empty missing cells stay empty in CSV. Raw attitude codes may contain 99, but score columns cannot.
7. Write audit counts, input SHA-256 hashes, zero-duplicate/zero-invalid-code checks, unmatched keys, version lists, and missing-score counts at both task and participant levels. Validation failures stop the command before writing new outputs; Python errors explain the violated condition.

A missing attitude export row yields `attitudes_match=left_only`, `attitudes_status=missing_export_row` and missing scores/completion, rather than an inferred zero or false. A known current participant who did not submit has a matched row with `attitudes_completed=0` and blank scores. These cases remain distinguishable. A fully submitted DK response is matched/completed with its DK indicator=1 and score missing.

Native and difference inputs are expected to refer to the same complete set of participant slots. An unmatched Household/native key therefore fails the source-agreement check; it is not silently joined to another session. Missing attitudes are the allowed unmatched case. The audit includes both match indicators and unmatched lists; an empty list records a successful check rather than proving all attitudes were completed.

## Merged schema

All original difference fields are retained, including `choice`, `chose_A`, `choice_set_id`, `task_index`, `facility_type`, `delta_rent_1000`, `delta_size_m2`, `delta_near20`, `coal`, `delta_near20_coal`, block, saved assignment/seed, DCE completion, timing and every Housing version/hash.

Added Household fields: `age_group`, `rent_status`, `monthly_rent_sek`, `income_thousand_sek`, `income_sek`, `income_not_disclosed`, `previous_power_plant_exposure`. Income is **net monthly personal income**, not household income. Added native statuses: `eligible`, `exit_reason`, `household_complete`, `survey_completed`. Added attitude fields are the wide schema above, with shared session/data-class columns retained once from DCE. `household_match` and `attitudes_match` record join status.

Native `survey_version` in Random Matrix remains **V2.2b**, as do its session config and DCE export meaning; V3 is recorded independently by `attitudes_version=V3.0`. Numeric version/hash, treatment V2.3/hash and Housing wording V2.2b are untouched. Historical V2.0–V2.2b exports have no V3 attitude provenance: generated attitude raw/score/DK/completion cells remain blank and status is historical_unavailable. No older 1–10 fields are inferred or recoded. Unsupported explicit attitude versions fail rather than being guessed.

## Integrity tests and analysis limits

`tests/test_attitudes.py` covers all five scores, zero vs missing, DK, invalid form and CSV codes, duplicate IDs/tasks, cross-session same-code identity, leading-zero/NA-like strings, corrupt scores/versions/context, historical CSVs, read-only old-schema refusal, reload/replayed submissions/restart, and CLI overwrite refusal. The HTTP fixture includes completed responses, DCE-complete/attitude-unsubmitted, two-choice dropout, under-age, refusal and unstarted slots. Existing DCE matrix, concurrent allocation, export and Live guard tests remain active. Browser and native bots test real submitted fields and timing.

No row is excluded from the merged file automatically. Researchers must separately decide which submitted tasks enter later models and account for repeated choices. Attitudes are post-choice measurements and repeat four times per participant; neither those repetitions nor alternative-long rows increase the number of respondents. No WTP regression is included.

Implementation references: [oTree native form saving/validation](https://otree.readthedocs.io/en/latest/forms.html), [Pandas merge key/cardinality and null-key behavior](https://pandas.pydata.org/docs/reference/api/pandas.merge.html). Runtime behavior was checked with the installed pinned versions and synthetic tests.
