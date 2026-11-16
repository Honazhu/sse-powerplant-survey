# V5 implementation report — development candidate, not release-ready

## Isolation and V4 audit

The workspace root is not a Git repository. The V4 release package at `/private/tmp/sse-powerplant-survey-release` has an unborn `main` branch and all source files staged, with no commits or tags; a worktree cannot be made from it. This directory is an independent source copy under the workspace. The V4 index and source were not changed; its SHA256SUMS check passed after the work. No production database, push, merge or deployment was used. `SHA256SUMS` from the V4 package was removed from this copy because it described V4 bytes, not V5. Historical files in `docs/` remain for reference only.

The V4 app sequence is eligibility → random_matrix → household → attitudes. Active pages were AgeConfirmation → Introduction → VoluntaryParticipation (or Exit) → ScenarioInstructions → four Choices → HouseholdInformation → AttitudeSurvey → Completion. Exit and other pages use eligibility flags to skip later pages. V4 participant code is an eight-character random oTree code, stored on Participant with a database uniqueness constraint; it is displayed after consent and is also an access credential in participant URLs. V4 Page `attitudes_completed` and `participant.finished` were set on final attitudes submission; there was no independent complete-six/all-fields audit. V4's native database exports and historical transformations include partial respondents; they are generated from database/native CSV, not automatically appended by a found application CSV writer. The old file-based transformations write derived outputs to local files and can include partial records.

The V4 frozen matrix is below. A and B are canonical, before a whole-profile side swap. Every row has the same plant on both sides; 10 km is always SEK 6,500, 50 km is baseline plus premium.

| Set | Type | A: km / SEK | B: km / SEK | V4 block |
|---|---|---|---|---|
| S01 | Nuclear | 10 / 6,500 | 50 / 7,500 | A |
| S02 | Oil | 50 / 7,000 | 10 / 6,500 | B |
| S03 | Nuclear | 50 / 8,500 | 10 / 6,500 | B |
| S04 | Oil | 10 / 6,500 | 50 / 8,500 | A |
| S05 | Nuclear | 10 / 6,500 | 50 / 6,500 | B |
| S06 | Oil | 50 / 6,500 | 10 / 6,500 | A |
| S07 | Nuclear | 50 / 7,000 | 10 / 6,500 | A |
| S08 | Oil | 10 / 6,500 | 50 / 7,500 | B |

V4 assigned one block of four via a seeded permuted A/B sequence and an atomic conditional cursor update on first eligible Choice. Each block had two sets of each facility, all four premiums once, and one near-A and one near-B for each facility. Each participant's four-set order and side assignment were shuffled from a saved seed, and the full plan and realized assignments persisted. V4's facility labels in the option cards come from the task's common facility; profile validation checks both homes. The V4 Cookie control was a temporary browser cookie probe, not a research-timing switch: Choice timestamps were always written and the native page-time export was not filtered. The premise that V4 backend timing was NULL when cookies were declined is not true for this release source.

## V5 flow and randomization

Welcome and age are combined → privacy and independent optional timing consent → instructions → six Choices → household → unchanged attitudes → completion; underage or participation refusal goes to Exit. A code is shown on privacy and completion. Refusal or unanswered cookie choice defaults to no timing. Exact requested wording is used, apart from a sentence identifying necessary session cookies. The instructions' statement that plant type “changes from pair to pair” does not imply guaranteed alternation in the specified random order; researcher review is needed.

The eight original profiles are unchanged. For each participant, the new seeded procedure independently samples three of the four nuclear and three of the four oil sets, shuffles their six positions uniformly, then randomly assigns a 1/2 split of near-A versus near-B independently within each facility. Whole profiles are swapped; 3/3 and side splits are validated against the persisted snapshot. This preserves facility stratification and approximate side balance, but the old four-set blocks and their guarantee that all four premiums occur once cannot be preserved with six of eight. Every permitted subset has probability 1/16; V5 has 16 unordered subsets and 16×6! = 11,520 ordered presentations, before side assignments. The unrestricted figures are 28 and 20,160, respectively. Six responses per participant increase observations, not independent respondents; analyse clustering and changed assignment probabilities. The original V2.4 numeric matrix hash remains recorded; a separate V5 treatment hash covers the revised allocation rules. Seed and assignment snapshot allow reconstruction, not replication of an independent draw without the seed.

## Consent, storage and export

`ConsentTimingPage` suppresses oTree 6.0.15's private page-completion hook unless consent is true. Opt-in Choice timing uses the original server start/end method; no-consent fields are NULL and task completion uses its own flag. Real HTTP tests inspected native page-time batches: only the framework's initialization row existed for non-consenting subjects; consenting subjects had page rows. Initialization happens before consent and remains a technical timestamp; it is not sufficient to derive a dwell interval alone. The first opt-in privacy interval starts at initialization, so it also includes time spent before consent; the age/welcome page has no independent timing record. This relies on an undocumented, version-specific oTree method and requires renewed verification after every framework change. Native administration timestamps and logs remain distinct from research timing. No optional cookie is actually set by this code; the supplied notice equates optional cookies and timing, requiring researcher/legal review.

Final attitudes submission validates adult consent, household codes and conditional applicability, six distinct saved assignments, actual choice/profile correspondence, all five attitudes and timing consent before setting persistent completion flags. `attitudes.custom_export` generates a separate V5 wide CSV from the database, revalidates completed responses and emits one row per unique reference with all six choices; it fails closed on invalid completed data. It does not append to V4 files. `custom_export_timing` is separate, opt-in and completed-only. The native oTree admin downloads and historic transformers are not the formal research CSV and can expose intermediate records. CSV snapshots already downloaded are independent copies and are not automatically purged when database records are removed. There is no tested deletion tool covering all database records, backups and exports; do not make operational deletion guarantees until a procedure is approved and tested.

## Transactions, compatibility and outstanding work

The installed oTree is SQLAlchemy based, not Django: its request middleware commits successful responses and rolls back server errors. The allocation uses conditional updates to claim the participant and increment a session cursor in that request transaction; no explicit Django `transaction.atomic` or explicit `SELECT FOR UPDATE` is present. The framework also has an in-process request lock, which is not a distributed dyno lock. Participant code has a DB unique constraint; no dedicated completion/export uniqueness constraint was added. The completion flags and profile rows commit within the final request, but simultaneous requests, replay with conflicting data, export/write overlap, rollback and transaction retries have **not** been established on PostgreSQL. Do not claim multi-worker/dyno safety.

The V5 page sequence, round count, schema and validation guards are incompatible with resuming V4 sessions under the same code/database. Keep V4 code and database running separately for V4; use a new V5 application/database and fresh sessions. Historical V4 exports remain with V4 tooling. No in-place migration or legacy resume test was performed. V5 has not passed its inherited V4 suite or real PostgreSQL concurrency tests; see test and deployment reports.

## Modified files

- `settings.py`, `timing.py`, `completion_v5.py`
- `eligibility/__init__.py`, `eligibility/questions.py`, `eligibility/AgeConfirmation.html`, `eligibility/VoluntaryParticipation.html`
- `random_matrix/__init__.py`, `random_matrix/randomization.py`, `random_matrix/facility_design.py`, `random_matrix/Choice.html`, `random_matrix/ScenarioInstructions.html`
- `household/__init__.py`, `household/HouseholdInformation.html`, `household/countries.py`, `household/questions_v5.py`, `_static/survey_ui/household.js`
- `attitudes/__init__.py`, `_templates/global/SurveyBase.html`, `_templates/global/SurveyHeader.html`, `_templates/global/SurveyReferenceBadge.html`, `scripts/pilot_server.py`
- `tests/test_v5_design.py`, `tests/test_v5_http.py`, `README.md`, the four V5 reports and `docs/V5_DATA_DICTIONARY.md`; removed V4-only `SHA256SUMS` from this copy.
