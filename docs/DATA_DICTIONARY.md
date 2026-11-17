> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# V3.3 additions and current meanings

`SURVEY_FLOW_VERSION="V3.3"`, `ATTITUDES_VERSION="V3.3"`; `HOUSING_DESIGN_VERSION="V2.4"`. Housing canonical SHA-256 remains `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`.

| Native / derived field | Current meaning |
| --- | --- |
| session.config.survey_flow_version | V3.3, persisted native app sequence release |
| eligibility.1.player.survey_flow_version | New nullable StringField, assigned V3.3 only on fresh session creation; no initial/backfill on historical rows |
| session.config.housing_design_version | Explicit V2.4 label; existing DCE design/survey/wording/numeric/treatment fields and hashes remain V2.4 |
| attitudes.1.player.attitudes_version | V3.3 on fresh slots; historical V3.0 preserved |
| attitudes_completed / attitudes_submitted_at | false / missing until successful five-answer submission; then true / positive Unix time |
| nuclear_economic, housing_cost, nuclear_support, nuclear_climate, nuclear_risk | Five existing IntegerFields, required −2…2, no default; current Q1–Q5 order below |
| each *_score | Raw integer unchanged for V3.3; Missing for unsubmitted and historical DK 99 |
| nuclear_economic_dk, nuclear_climate_dk | Historical raw 99→1; submitted ordinary score→0; unsubmitted→Missing. No V3.3 DK choice |
| merged survey_flow_version | Validated native flow provenance; absent historical stays blank |
| merged dce_completed | Alias of existing module_completed, independent of Household/Attitudes completion |
| merged household_completed | Alias of existing participant.household_complete (original column also retained) |

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

Native Reference ID remains participant.code. Join key remains `(session_code, participant_code)`, plus task_index for DCE tasks. Native/attitudes-wide/DCE-wide:1 row per participant/session; tasks/difference/merged:4 per slot; long:8. No grain change or missing→0 conversion.

Part A completes before ID display; Part B DCE now precedes Part C Household and Part D Attitudes. Household fields, units, codes and conditional null rules are unchanged. A dropout at Household after four choices has module_completed/dce_completed=1, household_complete/household_completed=0, attitudes_completed=0; Household answers and attitude raw/scores stay missing. A1–3-choice dropout retains submitted choices plus four assigned set/block/facility profiles; future choices remain missing and module_completed=0. No fields are imputed from later modules.

The dictionaries below retain their stated historical meanings. V2.4 housing attributes and A−B definitions remain current; prior V3.0 wording/DK behavior applies only to historical V3.0 rows.

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# Data dictionary — current V2.4 Housing

Current DCE design/survey/wording/numeric/treatment versions are V2.4; design and numeric hash `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`. Attitudes stays V3.0. Native rounds are random_matrix.1–4.player; codes are session.code and participant.code. Use both codes plus task_index for a task key. Round 1 is authoritative for module metadata.

| Field / alias | Values and meaning |
| --- | --- |
| block_id | New native String A/B; blank before first Choice. Legacy V2.3 integer 1/2/3 remains historical |
| choice_set_id / set_id | Stable S01–S08, with design_version; set_id is an analysis alias |
| choice / choice_ab | Raw displayed A/B, blank if unanswered; no default |
| task_index / presentation_order | 1–4; normalized task_index also retained for unassigned slots |
| facility_type | nuclear/oil_fired, shared by A/B; blank if unassigned |
| premium_sek | 0/500/1000/2000; 0 is a valid price contrast, blank if unassigned |
| base_rent_sek | 6500 on assigned tasks only |
| side_swapped | Native Boolean: 1=whole canonical A/B profiles reversed, 0=canonical orientation; blank if unassigned |
| A_distance_km / home_A_distance_km | Actual displayed distance, 10/50; same for B |
| A_rent_sek_month / home_A_rent_sek | Actual displayed rent, 6500/7000/7500/8500 SEK/month; same for B |
| A_near20 / home_A_near20 | int(actual distance<20), never independent; same for B |
| A_facility_type, B_facility_type | Both equal task facility_type |
| chosen_facility_type | Saved from displayed chosen profile, nuclear/oil_fired; blank if unanswered |
| chosen_distance_km | Saved from displayed choice: 10/50; blank if unanswered |
| chosen_rent_sek | Saved actual chosen rent; blank if unanswered |
| chosen_far | 1=chosen 50km, 0=chosen 10km; blank if unanswered |
| chosen_near20 | Existing field, chosen distance<20; blank if unanswered |
| task_completed | New nullable Boolean, initialized false only for new slots; true after valid A/B submission |
| task_displayed | Existing first-render indicator; assigned future tasks can remain false |
| task_started_at / task_submitted_at / task_duration_s | Existing timing algorithm; duration seconds, missing if unanswered; never filled as zero for dropout |
| task_timing_status | Existing not_submitted/ok/missing_start/clock_reversed |
| assignment_json | Round-1 complete four-task snapshot, codes, block, seed/index, versions, whole profiles and swap flags |
| facility_type_assignment | Fixed set→facility map; no randomized Coal overlay |
| facility_assignment_seed | Retained legacy field; blank in V2.4 because facility is frozen in the matrix |
| random_seed / allocation_index | Saved participant order/side RNG seed; one-based session claim index |
| module_started / tasks_answered / module_completed | Assigned / count 0–4 / all four valid responses |
| participant.finished | Whole survey completion after preserved V3 attitudes; distinct from DCE completion |
| A_size_m2, B_size_m2, housing_size_m2 | Retained native legacy columns; NULL in V2.4, excluded from V2.4 analysis files |

The eight new nullable fields are premium_sek, base_rent_sek, side_swapped, chosen_facility_type, chosen_distance_km, chosen_rent_sek, chosen_far and task_completed. Existing chosen_near20 is reused. No default/backfill applies to historical rows; only new databases are used. All aliases are export aliases of retained native fields, not duplicate sources of truth.

Exports: native/wide one row per slot; tasks/difference four rows per slot; long eight rows per slot. Unassigned/excluded slots retain missing profiles/outcomes, while all assigned future profiles remain in the snapshot. Long uses alternative_id/home=A/B, facility_type, distance_km, rent_sek_month, near20, far, chosen. Completed tasks have one chosen=1; unanswered alternatives both have blank chosen.

Difference uses chose_A, delta_rent_1000=(rent_A−rent_B)/1000, delta_far=far_A−far_B, oil=1 for oil_fired/0 for nuclear and delta_far_x_oil=delta_far×oil. There is no V2.4 delta_size_m2, Coal contrast or redundant distance main effect. All formats include set/version/hash, actual raw response, saved chosen attributes and missingness. [Model and interpretation](V2_4_DESIGN_SPECIFICATION.md).

The adapter rejects bad snapshots, inconsistent aliases/profiles/choice/completion, duplicate/missing task keys and mixed versions. Legacy V2.3 conversions keep their existing schema; no Coal→Oil mapping or new default. The attitude join supports both dispatch paths and preserves string block A/B for V2.4. Household, Consent, cookies, Reference ID and V3 attitude definitions below are unchanged.

---

# Historical dictionary (pre-V2.4; original definitions retained)

The following V2.3 housing values and version-specific behaviors describe historical records only. Use the current section above for V2.4. The source/archive retains this entire original dictionary.

# Data dictionary — V3.0 attitudes / V2.2b Housing / V2.3 treatment

## V3.0 attitude additions

Existing Housing, Household and historical definitions below retain their meanings. New sessions add `session.config.attitudes_version=V3.0`, while all current Housing version/hash values remain unchanged. Eight new nullable native Player columns are created only in fresh databases: five response fields plus attitudes_version, attitudes_completed and attitudes_submitted_at. No historical default/backfill occurs.

| Native field (attitudes.1.player.*) | Type / allowed values | Missingness / meaning |
| --- | --- | --- |
| attitudes_version | String V3.0 | New-session label including excluded/unstarted slots; old absent stays blank |
| attitudes_completed | Nullable Boolean | New sessions start false; true only after all five valid answers; old unknown blank |
| attitudes_submitted_at | Nullable Float / Unix seconds | Successful submission timestamp; blank otherwise |
| nuclear_support | Integer −2/−1/0/1/2 | Higher=support; required, no default |
| nuclear_risk | Integer −2/−1/0/1/2 | Higher=greater safety concern; required, no default |
| nuclear_economic | Integer −2/−1/0/1/2 or raw 99 | Higher=more positive perceived economic effect; 99=DK |
| nuclear_climate | Integer −2/−1/0/1/2 or raw 99 | Higher=more help reducing emissions; 99=DK |
| housing_cost | Integer −2/−1/0/1/2 | Higher=greater priority on low costs; required, no default |

These category codes are ordinal, not an interval scale. All raw fields remain NULL until a successful whole-page submission; partially selected browser controls and invalid form submissions are not saved as answers. 0 is a substantive neutral response. Legacy 1–10 preview fields remain unused; legacy `completed` mirrors successful V3 completion only in new sessions. `participant.finished` now requires the valid attitude submission, whereas `random_matrix.1.player.module_completed` continues to describe the four Housing Choices independently.

`attitudes_wide.csv` adds five *_score columns, each −2…2 or blank, and `nuclear_economic_dk` / `nuclear_climate_dk` (1=DK, 0=submitted ordinal, blank=unanswered). Raw 99 remains recoverable; score is blank, never 99 or 0. `attitudes_status` distinguishes submitted, not_submitted and historical_unavailable. A supplied merge missing its attitude row adds missing_export_row without inventing scores/version/completion.

The new wide table is unique on string `(session_code, participant_code)`. `analysis_merged.csv` left-joins it and native Household/status fields to the unchanged DCE difference tasks with many-to-one validation. A DCE-complete/attitude-unsubmitted person keeps four choices, scores missing and attitudes_completed=0. Historical preview completion never becomes a V3 answer. `attitudes_custom.csv` continues to mean the existing whole-survey timing export; it is unchanged.

Exact labels/directions: [ATTITUDE_SCALE](ATTITUDE_SCALE.md). Full schemas, join cardinalities, dtypes, compatibility, commands and audit: [CSV_INTEGRATION](CSV_INTEGRATION.md). The remaining dictionary is the retained Housing and historical reference; any older descriptions of Attitudes as a preview apply to their stated earlier releases.

## Native records and version boundaries

Native `all_apps_wide.csv` remains one row per participant slot, including exclusions and partial responses. Task prefixes are `random_matrix.<round>.player.<field>` for rounds 1–4. Round 1 is authoritative for module metadata; later-round module counters are unused defaults. Native `participant.code` / `session.code` become `participant_code` / `session_code` in normalized exports.

New-session config: `matrix_version=V2.0`, `treatment_design_version=V2.3`, `survey_version=V2.2b`, `study_mode=pilot`, `data_class=synthetic`. Live remains blocked. The obsolete `Player.matrix_version` is a retained V0 column, not the new numeric-version field.

| Field | Storage / meaning | Missing-value policy |
| --- | --- | --- |
| participant_code, session_code | Native codes / normalized aliases; use both for provenance | Present for each participant slot |
| survey_version | Player string, all four rounds: V2.2b | New slots populated, including exclusions/unstarted |
| wording_version | Nullable Player string, all four rounds: V2.2b | No default/backfill; historical missing stays missing; version is not exposure |
| numeric_matrix_version | New nullable Player string, all four rounds: V2.0 | Populated on new session creation; historical absent stays blank |
| numeric_matrix_hash | New nullable Player string, all four rounds | Original canonical source hash `96862c147a85b30d887c0a77432805011ae6e755e608a0c8e408a82571dd5053`; includes original nuclear source labels; not the full mixed-treatment hash |
| treatment_design_version | New nullable Player string, all four rounds: V2.3 | New session label; no historical inference |
| design_version, design_hash | Player strings, assigned rounds: V2.3 / `4c925a9034bcfebb4dd15e904d4f345b6c1422f169b96f4c50b249a3558bcb7e` | Blank before assignment; full design hash covers numeric provenance and allocation rules |
| block_id | Player integer 1/2/3, all assigned rounds | Blank until first Choice, including while on Instructions |
| facility_assignment_seed | New nullable round-1 string | Saved block-pair seed; same seed for the complementary pair, not a unique participant ID; blank before assignment |
| facility_type_assignment | New nullable round-1 JSON string | Canonical map from the four set IDs to nuclear/coal; two of each; blank before assignment |
| random_seed | Round-1 string | Independent per-participant set/side shuffle seed, blank before assignment |
| allocation_index | Round-1 integer | One-based claim order within session; blank before assignment |
| assignment_method | Assigned Player string | `permuted-triplets-with-facility-pairs-v2`; blank before assignment |
| display_version | Assigned Player string | `housing-choice-v2.3`; blank before assignment |
| choice_set_order_json | Round-1 JSON string | Four ordered set IDs, blank before assignment |
| side_allocation_json | Round-1 JSON string | Near's ordered sides, two A/two B, blank before assignment |
| assignment_json | Round-1 JSON string | Codes, block/index, both seeds, map, numeric/treatment provenance and complete task snapshots; blank before assignment |
| assignment_claimed | Round-1 Boolean | Atomic claim guard; initially false; technical, not an answer |
| task_count | Round-1 integer | Four planned slots, including unstarted; not exposure |
| tasks_answered | Round-1 integer 0–4 | Count of successful Choice submissions; zero is not zero WTP |
| module_started | Round-1 Boolean | First Choice assignment occurred |
| module_completed | Round-1 Boolean | All four experimental choices submitted; distinct from later survey completion |
| participant.finished | Existing native participant Boolean | Full survey completion; retained in native wide CSV, join to normalized outputs by codes if needed |
| allocation_plan_json | Round-1 Subsession JSON | Session seed, capacity-length block sequence, facility schedule, full treatment payload/hash and provenance |
| allocation_cursor | Round-1 Subsession integer | Claimed assignments, starts zero, never reduced for dropout |

The six new nullable fields are numeric_matrix_version, numeric_matrix_hash, treatment_design_version, facility_assignment_seed, facility_type_assignment and facility_type. Other fields already existed. New columns are created only in fresh databases. Subsession columns appear as `random_matrix.1.subsession.*`. A saved session plan does not imply each slot received treatment.

Pair replay requires session seed/block sequence or the saved schedule, plus allocation_index; facility_assignment_seed alone intentionally does not encode whether this person is the first or complementary member. The persisted map and full snapshot are sufficient to recover the realized treatment without redrawing. Session plan slots also store one-based block_ordinal and coal_set_ids. See [RANDOMIZATION_PLAN](RANDOMIZATION_PLAN.md).

## Per-task fields

| Field | Type / units | Meaning and missingness |
| --- | --- | --- |
| task_index | Integer 1–4 | Actual native round; native field blank before assignment, normalized rows always retain known index |
| choice_set_id | String S01–S12 | Frozen set ID; blank if unassigned |
| presentation_order | Integer 1–4 | Actual randomized order; blank if unassigned |
| facility_type | New nullable string | nuclear or coal, common to both apartments; blank if unassigned or historically absent |
| near_side | String A/B | Near's displayed side; blank if unassigned |
| A_size_m2, B_size_m2 | Integer / m² | Whole-apartment 40/55/70 |
| A_distance_km, B_distance_km | Integer / km | One 10 and one 30 |
| A_rent_sek_month, B_rent_sek_month | Integer / SEK per month | Exact original frozen prices |
| A_near20, B_near20 | Integer 0/1 | distance<20, one of each |
| A_facility_type, B_facility_type | Existing strings | Equal to task facility_type in current assigned tasks; historical nuclear values keep their original meaning |
| choice | String A/B | Selected apartment; NULL/blank if unanswered, no default |
| chosen_near20 | Integer 0/1 | Chosen profile's proximity; blank if unanswered |
| task_displayed | Boolean | Server rendered at least once; false for assigned-but-unseen tasks; not human attention |
| task_started_at | Float / UTC Unix seconds | First render time; blank if never rendered |
| task_submitted_at | Float / UTC Unix seconds | Successful submission time; blank if unanswered |
| task_duration_s | Float / seconds | Submission minus first render; blank if unanswered or invalid clock/baseline |
| task_timing_status | String | not_submitted / ok / missing_start / clock_reversed |

Profiles are blank before assignment. All four planned profiles are saved on first Choice even when later tasks remain unseen. Missing choice, chosen indicator and duration never become zero. Boolean CSVs use 1/0; blank is distinct. Round-1 completion and each task's exposure are explicit flags, not preference measures.

## Export grains and transformations

`random_matrix_custom.csv` has one row per participant×round, repeating module metadata from round 1. `scripts/export_dce.py` reads native wide CSV without opening a database and produces:

| File | Grain | Facility / outcome representation |
| --- | --- | --- |
| dce_wide.csv | Participant | Shared seeds/map/provenance and task1_… through task4_… including facility_type/choice |
| dce_tasks.csv | Task | Four rows per slot, common facility_type plus both A/B profiles |
| dce_long.csv | Alternative | Two rows/task, apartment=A/B and facility_type; chosen=1/0 only for answered tasks, both blank if unanswered |
| dce_difference.csv | Task | facility_type, coal, Δ attributes, interaction and chose_A (1=A, 0=B, blank=unanswered) |

All formats carry participant/session IDs, block/set/order, treatment and wording, assignment snapshot, and module completion. Native wide remains the source for unchanged Household and whole-survey completion fields. Native round-2–4 facility_assignment_seed/map cells are blank by design; use round 1. Normalized exports repeat them for each task.

Difference definitions: `delta_rent_1000=(A_rent_sek_month−B_rent_sek_month)/1000`; `delta_size_m2=A_size_m2−B_size_m2`; `delta_near20=A_near20−B_near20`; `coal=int(facility_type=='coal')`; `delta_near20_coal=delta_near20*coal`. Unassigned or historically missing task facility yields blank coal/interaction, not assumed Nuclear. The analyst supplies a constant 1 for an A-position intercept; ΔCoal is identically zero because A/B share context and must not be mistaken for the existing coal column. No estimator is run by exporting.

The transformer rejects duplicate/invalid keys, missing task rows, invalid choices, snapshot/profile/context differences, conflicting metadata and completion inconsistencies. Current native exports require current provenance columns and consistent labels across rounds. Existing output names are refused. Current examples: [native](../data/synthetic/v2_2b_browser_1794733130242432000/all_apps_wide.csv), [wide](../data/synthetic/v2_2b_browser_1794733130242432000/dce_wide.csv), [long](../data/synthetic/v2_2b_browser_1794733130242432000/dce_long.csv), [difference](../data/synthetic/v2_2b_browser_1794733130242432000/dce_difference.csv). Browser bundle: 7 native/wide, 28 task/difference, 56 long rows; four completions, two exclusions, one two-answer partial. [Native custom task example](../data/synthetic/v2_smoke_20261115T085800004256Z/random_matrix_custom.csv).

## Historical compatibility and timing

V2.0–V2.2a historical native exports retain `survey_version=V2.0`; the converter also accepts current V2.2b. Old absent wording/treatment fields stay blank; explicit historical wording stays unchanged. Original alternative-level nuclear observations remain nuclear in long format, while absent new task-level treatment provenance is not backfilled. Older one-round DEMO exports are incompatible with this four-round converter. Original files are never rewritten.

New-session callbacks label current rows only; Instructions/Choice guards reject old/missing wording and incompatible treatment plans. The helper checks schema columns read-only and refuses old databases. New schema/session creation is mandatory; no migration or old-session resumption occurred.

ScenarioInstructions remains round 1 only. It does not allocate, start task timing or record a new response. Native PageTimes has a separate Instructions completion; Choice 1's native interval follows it. Each task timer begins at first Choice render and survives reload/validation. Native PageTimes lacks wording: join codes to native data. No completion event means no completed duration. Timing is not an exclusion criterion. The browser bundle includes [page_times.csv](../data/synthetic/v2_2b_browser_1794733130242432000/page_times.csv), five Instructions and eighteen Choice completions. The unchanged timing adapter is documented in [TIMING](TIMING.md).

## Historical V0/V1 dictionary and unchanged Household/cookie fields

The sections below preserve earlier field meanings and release-specific behavior. References to a one-round DEMO Matrix, imaginary tokens and pre-screen assignment describe historical V0 only; the V2 definitions above supersede them for new sessions.

Verified against native oTree 6.0.15 CSV output on 2026-11-13.

## Export conventions

The wide export `all_apps_wide.csv` has **one row per participant slot**. Player fields below have names such as `household.1.player.country_of_residence`; the middle `1` is the round number. Per-app exports use `player.<name>`. Participant/session fields retain the full prefixes shown below. All declared participant fields were observed in the native export; core outcomes also have module-local Player columns.

Empty CSV cells represent missing responses unless a row specifies another meaning. Native Boolean values export as `1`/`0`; blank is distinct from False. In memory, unfilled model fields may be None (strings may be empty); use `field_maybe_none` when reading unsubmitted fields. No arbitrary 99/999 missing codes are defined.

| Variable Name | Type | Module | Description | Allowed Values | Missing Values | Export Status | Unit | Export Name |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| participant.code | String | oTree | Built-in technical respondent key; no new personal identifier | oTree-generated code | Not expected for allocated slots | Native CSV | None / category or metadata | participant.code |
| session.code | String | oTree | Session key; use with participant.code for provenance | oTree-generated code | Not expected | Native CSV | None / category or metadata | session.code |
| session.config.name | String | settings | Named configuration | nuclear_survey_pilot / nuclear_survey_live | Not expected | Native CSV | None / category or metadata | session.config.name |
| session.config.study_mode | String | settings | Operational mode | pilot / live (blocked) | Not expected | Native CSV | None / category or metadata | session.config.study_mode |
| session.config.data_class | String | settings | Data-use classification; not automatic detection | synthetic / live (blocked) | Not expected | Native CSV | None / category or metadata | session.config.data_class |
| session.config.matrix_version | String | settings | Expected design version | DEMO-V0-1 / TBD for blocked live | Not expected | Native CSV | None / category or metadata | session.config.matrix_version |
| participant.eligible | Boolean | shared | Cross-app screening outcome | True / False | False until eligible | Native CSV | None / category or metadata | participant.eligible |
| participant.exit_reason | String | shared | Cross-app screen status | not_screened / declined / under_18 / empty if eligible | Empty means eligible after screening | Native CSV | None / category or metadata | participant.exit_reason |
| participant.household_complete | Boolean | shared | Validated Household Q2–Q5 submitted | True / False | False before completion | Native CSV | None / category or metadata | participant.household_complete |
| participant.demo_assignment | JSON string | shared | Frozen DEMO assignment for this participant slot | Serialized DEMO snapshot | Absent before session assignment; present even if excluded | Native CSV | None / category or metadata | participant.demo_assignment |
| participant.finished | Boolean | shared | Eligible participant submitted final placeholder | True / False | False before completion | Native CSV | None / category or metadata | participant.finished |
| willing_to_participate | BooleanField | eligibility | Initial voluntary participation agreement after purpose/privacy information; synthetic Pilot only | True / False | Blank if page not submitted | Native CSV | None / category or metadata | eligibility.1.player.willing_to_participate |
| adult_confirmed | BooleanField | eligibility | 18+ confirmation without exact age or DOB | True / False | Blank before age submission | Native CSV | None / category or metadata | eligibility.1.player.adult_confirmed |
| eligible | BooleanField | eligibility | Exported screening outcome copy | True / False | Initial False | Native CSV | None / category or metadata | eligibility.1.player.eligible |
| exit_reason | StringField | eligibility | Exported screening status copy | not_screened / declined / under_18 / empty | Empty means passed; not missing | Native CSV | None / category or metadata | eligibility.1.player.exit_reason |
| country_of_residence | StringField | household | Country coding; reserved, no V0 form | TBD; unused | Blank in V0 | Native CSV | None / category or metadata | household.1.player.country_of_residence |
| age_group | StringField | household | Q2 adult age category | Six stable codes in V1 table below | Blank if excluded/unsubmitted | Native CSV | None / category or metadata | household.1.player.age_group |
| housing_tenure | StringField | household | Tenure category; reserved, no V0 form | TBD; unused | Blank in V0 | Native CSV | None / category or metadata | household.1.player.housing_tenure |
| income_range | StringField | household | Income category; currency/basis TBD; reserved, no V0 form | TBD; unused | Blank in V0 | Native CSV | None / category or metadata | household.1.player.income_range |
| monthly_electricity_bill | FloatField | household | Reserved monthly bill; not collected | Reserved; any future collected amount must use SEK | Blank in V0, never impute zero | Native CSV | SEK/month if activated; currently unused | household.1.player.monthly_electricity_bill |
| previous_residence_near_nuclear | BooleanField | household | Reserved prior residence indicator; proximity definition TBD | True / False; wording TBD | Blank in V0; not equivalent to False | Native CSV | None / category or metadata | household.1.player.previous_residence_near_nuclear |
| placeholder_completed | BooleanField | household | Technical placeholder was submitted | True / False | Initial False | Native CSV | None / category or metadata | household.1.player.placeholder_completed |
| scenario_id | StringField | random_matrix | DEMO scenario key | DEMO-S01 / DEMO-S02 | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.scenario_id |
| treatment_arm | StringField | random_matrix | DEMO allocation label | DEMO-A / DEMO-B | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.treatment_arm |
| nuclear_distance_km | FloatField | random_matrix | Fictional distance, km | 12 / 34; DEMO only | Assigned at creation, including excluded slots | Native CSV | km | random_matrix.1.player.nuclear_distance_km |
| housing_price | FloatField | random_matrix | Fictional price, no real currency | 1234 / 2345; DEMO only | Assigned at creation, including excluded slots | Native CSV | Imaginary DEMO tokens/month (not currency) | random_matrix.1.player.housing_price |
| housing_size_m2 | FloatField | random_matrix | Fictional floor area, square metres | 56 / 78; DEMO only | Assigned at creation, including excluded slots | Native CSV | m² | random_matrix.1.player.housing_size_m2 |
| price_unit | StringField | random_matrix | Explicit imaginary price basis | DEMO tokens per month (not currency) | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.price_unit |
| alternative_attributes_json | LongStringField | random_matrix | Serialized alternative details | JSON object with alternative_id and fixture | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.alternative_attributes_json |
| matrix_version | StringField | random_matrix | Frozen design version | DEMO-V0-1 | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.matrix_version |
| is_demo | BooleanField | random_matrix | Explicit synthetic design flag | True in V0 | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.is_demo |
| assignment_method | StringField | random_matrix | Frozen mechanism version | DEMO-sha256-participant-code-v1 | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.assignment_method |
| display_version | StringField | random_matrix | Template/presentation version | DEMO-page-v0-1 | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.display_version |
| scenario_snapshot_json | LongStringField | random_matrix | All realized attributes plus mechanism/display versions | Valid JSON object | Assigned at creation, including excluded slots | Native CSV | None / category or metadata | random_matrix.1.player.scenario_snapshot_json |
| scenario_displayed | BooleanField | random_matrix | Server rendered scenario; not proof of reading | True / False | Initial False; excluded stays False | Native CSV | None / category or metadata | random_matrix.1.player.scenario_displayed |
| scenario_acknowledged | BooleanField | random_matrix | Scenario page submitted; no preference outcome | True / False | Initial False; excluded stays False | Native CSV | None / category or metadata | random_matrix.1.player.scenario_acknowledged |
| nuclear_energy_support | IntegerField | attitudes | Reserved scale; wording and anchors TBD | Integers 1–10 | Blank in V0; no sentinel value decided | Native CSV | None / category or metadata | attitudes.1.player.nuclear_energy_support |
| nuclear_risk_perception | IntegerField | attitudes | Reserved scale; wording and anchors TBD | Integers 1–10 | Blank in V0; no sentinel value decided | Native CSV | None / category or metadata | attitudes.1.player.nuclear_risk_perception |
| economic_impact_perception | IntegerField | attitudes | Reserved scale; wording and anchors TBD | Integers 1–10 | Blank in V0; no sentinel value decided | Native CSV | None / category or metadata | attitudes.1.player.economic_impact_perception |
| climate_impact_perception | IntegerField | attitudes | Reserved scale; wording and anchors TBD | Integers 1–10 | Blank in V0; no sentinel value decided | Native CSV | None / category or metadata | attitudes.1.player.climate_impact_perception |
| housing_cost_sensitivity | IntegerField | attitudes | Reserved scale; wording and anchors TBD | Integers 1–10 | Blank in V0; no sentinel value decided | Native CSV | None / category or metadata | attitudes.1.player.housing_cost_sensitivity |
| completed | BooleanField | attitudes | Final placeholder submitted, Completion available | True / False | Initial False; excluded stays False | Native CSV | None / category or metadata | attitudes.1.player.completed |

## Built-in metadata and interpretation

Native CSV also includes participant ID-in-session, label, bot flag, current page/app, page indexes, start timestamp, visited flag, payoff, built-in external-platform IDs; session label/comment and external-platform IDs; per-app role, payoff, group ID, player ID and round number. These are oTree operational fields, not added survey questions. The project does not populate personal labels or recruitment IDs. No new IP or browser metadata fields are added.

`session.is_demo` is an oTree flag, independent of our authoritative `session.config.study_mode` and `data_class`. Fees/payoffs are zero in this scaffolding and are not WTP observations. Config currency SEK is an oTree display setting; it does not define the experiment's price units. Fixture prices use imaginary DEMO tokens.

CSV contains an allocation even when a participant never sees the scenario. For exposure use `scenario_displayed`; for progression use `scenario_acknowledged`, screening status and completion flags. A displayed flag proves only server rendering. An excluded participant must not be treated as exposed or completed merely because a snapshot exists.

There is no housing choice, WTP, exact age, birth date or personal contact field in V0. Unused legacy household and attitude blanks remain intentional; V1 active household fields follow the rules below. Future respondent-level analysis should retain excluded/incomplete cases with appropriate status rather than silently converting missing responses to zero.

Source: [oTree CSV/export documentation](https://otree.readthedocs.io/en/latest/admin.html); implementation validated with actual synthetic exports and `tests/test_smoke.py`.


## Cookies and elapsed-time extension

| Variable Name | Type | Module | Description | Allowed Values | Missing Values | Export Status | Unit | Export Name |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cookies_allowed | BooleanField | eligibility | Allow optional temporary cookie probe on combined consent page; not global platform-cookie consent | True / False | Blank if excluded or page not submitted | Native CSV | None / category or metadata | eligibility.1.player.cookies_allowed |
| cookie_probe_status | StringField | eligibility | Browser-reported test result, not a verified security assertion | not_tested / supported / blocked / declined | not_tested before submission or when JavaScript unavailable | Native CSV | None / category or metadata | eligibility.1.player.cookie_probe_status |
| participant.cookies_allowed | Boolean or None | shared | Cross-app copy of the optional preference | True / False | Blank before submission | Native CSV | None / category or metadata | participant.cookies_allowed |
| session_code | String | timing | Existing session key for timing rows | Built-in code | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | session_code |
| participant_code | String | timing | Existing respondent key for joins | Built-in code | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | participant_code |
| page_index | Integer | timing | Native page index, not necessarily consecutive after skipped pages | Native positive index | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | page_index |
| app_name | String | timing | App owning the completed page | One of the four apps | Not expected for derived rows | attitudes custom CSV / PageTimes | None / category or metadata | app_name |
| page_name | String | timing | Native page class name; HouseholdInformation covers Q2–Q5 together | Page class name | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | page_name |
| round_number | Integer | timing | Native round number | 1 in V0 | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | round_number |
| epoch_time_completed | Integer | timing | Native completion event time, UTC Unix seconds | Native timestamp | Not expected | attitudes custom CSV / PageTimes | UTC Unix seconds | epoch_time_completed |
| timeout_happened | Integer flag | timing | Native timeout flag | 0 / 1 | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | timeout_happened |
| is_wait_page | Integer flag | timing | Native wait-page flag | 0 in V0 | Not expected | attitudes custom CSV / PageTimes | None / category or metadata | is_wait_page |
| seconds_on_page | Integer or blank | timing | Current completion minus previous event for same participant/session | Nonnegative seconds, including valid 0 | Blank for missing baseline or reversed clock | attitudes custom CSV | seconds | seconds_on_page |
| timing_status | String | timing | Whether elapsed time can be computed | ok / missing_baseline / clock_reversed | Not expected | attitudes custom CSV | None / category or metadata | timing_status |
| timing_version | String | timing | Derivation algorithm version | page-completion-delta-v1 | Not expected | attitudes custom CSV | None / category or metadata | timing_version |

Timing export is long format (one completed page per row); it does not replace the respondent-level wide export. Join `participant_code` to `participant.code` and `session_code` to `session.code`. Unsubmitted/abandoned/terminal pages have no completed duration; do not treat absence as zero. Native InitializeParticipant events provide the first baseline and are omitted from the derived table. Timing uses no added identifier, cookie, IP or fingerprint.


## V1.0 active question fields, units and export names

All numeric amounts are **SEK**; income is **Net Monthly Personal Income — After Tax**. The original income_range column remains reserved/blank and is not another income measure. All columns below appear in native wide CSV; local app CSV uses `player.<name>`. These fields apply to V1 synthetic sessions; historical V0 files have no new columns.

| Name | Data type | Module / meaning | Unit | Allowed values | Missing value policy | Wide export name | None / category or metadata | Name |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| willing_to_participate | BooleanField (existing) | eligibility / initial consent | None | True/False; CSV 1/0 | Blank before submission | eligibility.1.player.willing_to_participate | None / category or metadata | willing_to_participate |
| adult_confirmed | BooleanField (existing) | eligibility / Q1a | None | True/False; CSV 1/0 | Blank before age submission | eligibility.1.player.adult_confirmed | None / category or metadata | adult_confirmed |
| participant.code | Built-in string (existing) | Q1b Survey Reference ID, cross-app join | None | oTree-generated code | Present for allocated slots; UI hidden until eligible | participant.code | None / category or metadata | participant.code |
| age_group | StringField (existing, now choices) | household / Q2 | Age category | 18_25=18–25; 26_35=26–35; 36_45=36–45; 46_55=46–55; 56_65=56–65; 66_plus=66 or above | Blank before valid submission/excluded; required otherwise | household.1.player.age_group | None / category or metadata | age_group |
| rent_status | BooleanField (new) | household / Q3a | None | True=Yes / False=No; CSV 1/0 | Blank before valid submission/excluded | household.1.player.rent_status | None / category or metadata | rent_status |
| monthly_rent_sek | IntegerField (new) | household / Q3b, personally paid monthly rent | SEK/month | Positive integer when rent_status=True | NULL/blank when No, excluded or unsubmitted; never 0 for No | household.1.player.monthly_rent_sek | None / category or metadata | monthly_rent_sek |
| income_thousand_sek | IntegerField (new) | household / Q4, original Net Monthly Personal Income — After Tax input | 1,000 SEK/month | Nonnegative integer incl. 0 | NULL/blank when refused, excluded or unsubmitted | household.1.player.income_thousand_sek | None / category or metadata | income_thousand_sek |
| income_sek | IntegerField (new, derived) | household / Q4, Net Monthly Personal Income — After Tax | SEK/month | income_thousand_sek × 1000; includes genuine 0 | NULL/blank when source missing; never 0 for refusal | household.1.player.income_sek | None / category or metadata | income_sek |
| income_not_disclosed | BooleanField (new) | household / Q4 refusal indicator | None | True=Prefer not to say; False=numeric answer; CSV 1/0 | NULL/blank before valid submission/excluded | household.1.player.income_not_disclosed | None / category or metadata | income_not_disclosed |
| previous_power_plant_exposure | IntegerField (new) | household / Q5 lived within approx. 20 km of any power plant | Category | 1=Yes; 0=No; 2=I don't know | NULL/blank if excluded/unsubmitted; 2 is a substantive category | household.1.player.previous_power_plant_exposure | None / category or metadata | previous_power_plant_exposure |
| placeholder_completed | BooleanField (existing) | household / successful full-page submission | None | True/False; CSV 1/0 | Initial False | household.1.player.placeholder_completed | None / category or metadata | placeholder_completed |
| participant.household_complete | Participant Boolean (existing) | shared / routing mirror of validated household completion | None | True/False; CSV 1/0 | Initial False | participant.household_complete | None / category or metadata | participant.household_complete |

Storage limit: rent ≤ 2^63−1; raw income thousands ≤ floor((2^63−1)/1000). These prevent integer database overflow, not research thresholds. All parsing/conversion is integer arithmetic; no floating-point rounding or exchange rates. Amounts with signs, exponents, decimals, separators, non-ASCII digits or whitespace are rejected.

V0 legacy fields `country_of_residence`, `housing_tenure`, `income_range`, `monthly_electricity_bill`, `previous_residence_near_nuclear` stay unused. Any future monetary use of the electricity field must declare SEK; it currently has no collected amount. Matrix's unchanged price_unit remains imaginary DEMO tokens, not a monetary response or silently re-labelled SEK. Formal future WTP/Matrix amounts must use SEK.

Survey Reference ID is **participant.code**, not `treatment_arm`, `scenario_id`, or a hash of demographic responses. A label does not make records fully anonymous. No ID-copy event or clipboard content is recorded. Deletion correspondence is outside this dataset.


## V1.1 ordering update — no new columns

Age is now answered first, including by adults who later decline participation. Under-18 participants have adult_confirmed=False, willing_to_participate/cookies_allowed blank, and cookie_probe_status=not_tested. Adults who decline have adult_confirmed=True, willing_to_participate=False, cookies_allowed blank, cookie_probe_status=not_tested. Consent plus cookie choice are submitted together on VoluntaryParticipation. Eligible respondents see participant.code beginning with Household.

Timing now has one VoluntaryParticipation observation for the combined privacy/consent/cookie page, no standalone CookiePreferences observation. Historical V1.0 events retain their original meaning. Keep release provenance with each export when comparing durations across versions.
