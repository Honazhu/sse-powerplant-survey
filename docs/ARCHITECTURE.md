> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# Architecture — V3.3 flow/attitudes with frozen V2.4 Housing

`eligibility → random_matrix → household → attitudes`, implemented in native `SESSION_CONFIGS.app_sequence`, not URL jumps. No new app or framework dependency.

| Part | Native pages | Entry and completion |
| --- | --- | --- |
| A — Eligibility & Data Protection | AgeConfirmation → Introduction → VoluntaryParticipation (privacy, consent and Cookie Preferences together); Exit only for exclusions | Age alone never sets eligibility. Adult consent and optional-cookie choice must validate. Under 18/declined terminate. |
| B — Housing Choice | ScenarioInstructions (round 1) → Choice ×4 | Eligibility is required; Household is still NULL. Instructions validates the saved plan; first Choice claims the existing atomic allocation. |
| C — Household Information | HouseholdInformation | Four choices precede it by native page indexes. Existing fields, validators and successful completion flag unchanged. |
| D — Attitudes | AttitudeSurvey → Completion | Eligibility + household_complete; five valid V3.3 answers save together. Completion only after successful attitudes submission. |

Audit found exactly two Household-first restrictions: Random Matrix page predicates and `assign_once` eligibility check. Those restrictions now require eligibility alone. Session plan, shuffled A/B pairs, participant seed, whole-profile side/order randomization, snapshot validation and request transaction behavior are unchanged. No Household answers feed assignment or get fabricated.

Reference badge remains server gated by `participant.eligible`. Because consent/cookies submit together, its first visible page is now Housing Instructions. ID/copy remain unchanged on all later pages and refresh. Native indexes redirect future/stale GET/POSTs to the current page; no custom client router is used.

`SURVEY_FLOW_VERSION="V3.3"`, `ATTITUDES_VERSION="V3.3"`; `HOUSING_DESIGN_VERSION="V2.4"`. Housing canonical SHA-256 remains `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`. `settings.py` persists the flow in session config, mirrored into new nullable `eligibility. Player.survey_flow_version` only during fresh creation. Existing attitudes version/completion/time fields persist V3.3. Original Housing `survey_version` means Housing release and stays V2.4. `PARTICIPANT_FIELDS` and `SESSION_FIELDS` remain unchanged. No old rows are backfilled.

`attitudes/questions.py` defines five explicit question→existing-field mappings. Field declarations/CSV order remain stable while display/form order is Q1 economic, Q2 housing cost, Q3 support, Q4 climate, Q5 risk. `legacy_questions_v30.py` is an exact copy of the prior question definitions, used only by the same existing export adapter for version dispatch.

`RatingQuestion.html` renders native radio fallback plus a disabled unnamed range. Lightweight `attitudes.js` activates five ranges and hides radios; a deliberate input/pointer release/navigation key selects exactly one existing radio. Focusing alone, initialization and the range midpoint select nothing. The radios remain the only submitted source. Server forms reject missing, duplicate, fractional, out-of-range and noncanonical payloads; native validation/population and error rendering remain in control. Other selected values survive invalid POSTs. Fresh GET/reload resets unsubmitted choices; there is no browser storage or autosave. Timing remains page-level, not per-slider attention.

Exports retain native → validated DCE difference → Household/status left join → version-aware attitudes left join. Cardinality, source agreement, string composite keys, input SHA-256 audit, nullable integers and overwrite protection remain. Merged completion aliases expose dce_completed/module_completed and household_completed/household_complete separately. Flow provenance is validated against both native session and Player values; historical absent stays blank.

The isolated Pilot helper checks new flow schema/version read-only and refuses old copies. Original database and historical artifacts remain protected. [Current tests](UI_TESTING.md), [handover](V3_3_COMPLETION.md).

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# Architecture — V2.4 Housing / preserved V3.0 Attitudes

Python 3.11.17, oTree 6.0.15, existing project-local venv. Four native apps remain:

`eligibility → household → random_matrix (four rounds) → attitudes`

Adult/consent checks and Household are unchanged. The current source already contained five V3.0 attitude questions; this release preserves them and their completion behavior. No new app, frontend framework, shared identity field or dependency was introduced.

## Experimental boundaries

`matrix.py` is the frozen V2.4 numeric/context/block source with a canonical hash. `facility_design.py` defines labels, release constants and strict plan/assignment validation. `randomization.py` owns session-seeded shuffled A/B pairs and per-person order/whole-profile side randomization. `__init__.py` declares native fields/pages and saves chosen attributes from the displayed snapshot. Home.html renders the repeated facility/distance/rent card; historical Apartment.html remains inactive.

`ScenarioInstructions` is round-1 only, eligible + Household complete. It validates versions/plan without assignment. `Choice` claims once on first eligible GET; all four round rows already exist and are populated using `in_rounds(1,4)` (installed oTree's in_all_rounds excludes future rounds). Rendering checks saved snapshot against native task fields. Timing starts once per task, unchanged. Required A/B submission saves chosen profile and task completion; native page indexes protect stale URLs/POSTs. No backward navigation is enabled.

Round-1 Subsession owns allocation_plan_json/cursor. Round-1 Player owns assignment_json, seeds, set/side order, block, allocation index and module counters. Later task rows own actual displayed profiles, set/type/premium/base/swap, choice, chosen attributes and task timing. Current design/wording provenance is stored for all new slots; assignment metadata remains blank until entry. Version presence is not exposure. task_completed, module_completed and participant.finished have different grains.

## Persistent local operation

Conditional SQL UPDATE claims the participant once, then atomically increments cursor and writes snapshot/tasks in the same request transaction. A repeated claim loads existing data. No manual partial commit, memory-global counter, adaptive response input or allocation recycling exists. Runtime validation checks plan hash/sequence and exact task profiles. Fifty entrant claims in one session receive 25/25 blocks. Completed balance is outcome-dependent.

The installed ordinary oTree devserver uses memory with shutdown-save behavior. scripts/pilot_server.py prepares an isolated source/assets copy, removes inherited DB overrides, binds localhost and uses the installed disk-backed request transaction server. Never start current models on the source db.sqlite3. Its read-only schema check refuses old previews missing V2.4 fields. New block_id is text A/B rather than legacy integer 1/2/3; no retained schema is migrated. Resume only this release's marked isolated Pilot project.

## Export/version boundary

Native wide and native custom task exports remain available. exports.py selects exports_v24.py for survey V2.4 and frozen legacy_v23/exports.py for historical V2.0/V2.2b (including treatment V2.3). Mixed current/historical input is rejected before writing. Historical four-round adapters preserve Coal, size and missing wording. Unsupported V0 one-round data is refused. No old data is relabelled or given current defaults.

V2.4 emits wide/tasks/long/A−B difference formats, no size coefficient. Native choice/choice_set_id/A_* fields retain names; analysis aliases expose choice_ab/set_id/home_A_* consistently. Persisted chosen values are checked against actual A/B, with blank unanswered outcomes. The unchanged attitude exporter remains independently V3.0; analysis/merge_attitudes.py now handles V2.4 text blocks and difference variables while preserving historical numerical schema and validated joins.

Native size/legacy columns remain declared but unpopulated in V2.4. Archived V2.3 helpers, original complete source snapshot and historical test artifacts retain earlier behavior. Consent, Cookie, timing.py, Reference Badge, Marcellus/Inter/SSE assets, Eligibility, Household and Attitudes source are preserved. Live guards remain active. No resetdb, deployment or Git push occurs.

[Design](V2_4_DESIGN_SPECIFICATION.md) · [Dictionary](DATA_DICTIONARY.md) · [Tests](UI_TESTING.md) · [Completion](V2_4_COMPLETION.md).
