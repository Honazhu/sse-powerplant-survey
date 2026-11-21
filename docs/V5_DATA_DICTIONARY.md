> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

# V5 completed-response data dictionary

The official export is `attitudes.custom_export`, one row per completed eligible consenting participant; CSV uses empty cells for NULL. Rows that fail validation cause export failure, rather than being silently treated as complete. Values are for survey version 5.0.0. The local source files `household/countries.py`, `household/questions_v5.py`, and `attitudes/questions.py` are the authoritative code/label maps. All fields below apply to all V5 completed responses unless stated.

| Field | Meaning / wording | Type and allowed values | Missing / applicability | Source |
|---|---|---|---|---|
| survey_reference_id | Survey Reference ID / oTree participant code | unique string | required | eligibility/participant |
| survey_version | Overall survey release | string `5.0.0` | required | export |
| session_code | oTree session | string | required | session |
| wording_version | Housing introduction and choice wording | string `5.0.0` | required | random_matrix |
| treatment_design_version | Sampling / presentation rules | `V5.0` | required | random_matrix |
| numeric_matrix_hash | Frozen V2.4 original matrix hash | SHA-256 hex | required | random_matrix |
| cookies_allowed | permission for optional research timing | Boolean 1/0; unanswered treated as 0 | required after eligible consent | eligibility |
| assignment_json | Reconstructible seed, design hash, set IDs, order, side mappings and displayed profiles | JSON string | required | random_matrix |
| age_group | Adult age group | `18_25`, `26_35`, `36_45`, `46_55`, `56_65`, `66_plus` | required | household |
| residence_code | In which country or region do you currently live? | ISO alpha-2 in local table; `unable`, `prefer_not` | required; unable is distinct from refusal | household |
| rent_status | Do you currently pay rent or a mortgage for your accommodation? | Boolean 1/0 | required | household |
| rent_category | About how much does your household pay in rent or mortgage per month? Shared flat non-family: own amount | `nothing`, `lt_5000`, `5000_9999`, `10000_14999`, `15000_19999`, `20000_plus` | NULL means not applicable because rent_status=0; `nothing` is an explicit answer | household |
| income_category | Approximately what is your monthly **personal** income after tax? | `lt_10000`, `10000_19999`, `20000_29999`, `30000_39999`, `40000_59999`, `60000_plus`, `dont_know`, `prefer_not` | required; unknown and refusal are distinct categories, not zero | household |
| children_under_18 | Do any children under 18 live in your household? | `yes`, `no`, `prefer_not` | required | household |
| education_completed | Highest completed education | `primary`, `lower_secondary`, `upper_secondary`, `bachelor`, `master`, `doctorate`, `prefer_not` | required; prefer_not is not an education level | household |
| nuclear_economic, housing_cost, nuclear_support, nuclear_climate, nuclear_risk | Five existing V3.3 attitude statements | integers -2 through 2; -2 strongly disagree, 0 neutral, 2 strongly agree | all required; neutral is not missing | attitudes |
| choice_N_choice_set_id | Original matrix ID for position N=1…6 | S01…S08, distinct | required | random_matrix |
| choice_N_facility_type | Power plant for both displayed homes | `nuclear`, `oil_fired` | required | random_matrix |
| choice_N_A_distance_km, choice_N_B_distance_km | Displayed A/B distance | integer 10 or 50 | required | random_matrix |
| choice_N_A_rent_sek_month, choice_N_B_rent_sek_month | Displayed A/B monthly rent in SEK | integer 6500, 7000, 7500 or 8500 | required | random_matrix |
| choice_N_choice | Selected displayed side | `A`, `B` | required | random_matrix |
| choice_N_near_side | Which displayed side is 10 km | `A`, `B` | required | random_matrix |
| choice_N_side_swapped | Whether canonical set profiles were swapped | Boolean 1/0 | required | random_matrix |
| choice_N_task_duration_s | Choice elapsed wall-clock time | nonnegative float seconds when valid | NULL if no timing consent or invalid/missing timing; inspect `task_timing_status` | random_matrix |
| choice_N_task_timing_status | Timing interpretation | `ok`, `no_consent`, `missing_start`, `clock_reversed` | required on completed choice; technical failures differ from no consent | random_matrix |

Separate `attitudes.custom_export_timing` has one row per eligible consenting completed respondent/page, and fields `session_code`, `participant_code`, `page_index`, `app_name`, `page_name`, `round_number`, `epoch_time_completed`, `timeout_happened`, `is_wait_page`, `seconds_on_page`, `timing_status`, `timing_version`. `seconds_on_page` is NULL for missing baseline or reversed clock, as indicated by status; it includes time away and network delay. The native oTree initialization event is present even before consent, and the separate built-in administrative page-times export is not the formal V5 research export. No values are filled with zero merely because data are missing. V4-only real-world plant exposure and former numeric income/rent fields are not asked in V5 and are absent from this export; their historical values must remain in V4 storage.
