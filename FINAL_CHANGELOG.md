# Final candidate changes

- Isolated Final runtime and new database requirement; Pilot remains in `survey-v5`. Final production and separately tagged QA configs use eligibility → random_matrix → attitudes → household.
- Participation and optional timing are separate mandatory decisions for consenting adults; refusal exits. Screening includes research purpose and recipient. Removed active demo text and retained reference ID.
- Five new question-specific radio sets use scores 2, 1, 0, −1, −2; 99 is an internal explicit-missing sentinel, never an exported score.
- Added gender and main activity, age non-disclosure, payment status and conditional numeric payment/missing reason, numeric household after-tax income and missing reason. Retained countries, children and education choices. Added optional 1,500-character feedback at the end.
- Final household submission validates the eligibility, attitudes, six persisted V5 choices, and household, then marks completion. Completion page follows it. Production wide export excludes QA and incomplete participants, protects opt-out timing, and includes schema/design IDs and missing reasons.
- Added constrained country selection and client-side search, responsive form rules, and local official technology marks. Chrome emulated viewport behavior is tested; real device behavior remains unverified.
- Preserved the V5 matrix and six-task allocation (three nuclear and three oil-fired), as confirmed by the researcher after the initial four-versus-six discrepancy was identified.
- Raw oTree persistence is not a completed-only database. Added an offline admin deletion tool tested on synthetic SQLite, with a PostgreSQL rehearsal still required; no automatic cleanup was introduced.

## Changed and added files relative to V5

- Configuration and data: `.gitignore`, `settings.py`, `timing.py`, `completion_final.py`.
- Eligibility: `eligibility/__init__.py`, `AgeConfirmation.html`, `VoluntaryParticipation.html`, `CookiePreferences.html`.
- Attitudes: `attitudes/__init__.py`, `questions.py`, `AttitudeSurvey.html`.
- Housing choices: `random_matrix/__init__.py`, `randomization.py`, `ScenarioInstructions.html`. The matrix and facility-design files are byte-identical to V5.
- Household: `household/__init__.py`, `HouseholdInformation.html`, new `Completion.html`.
- Shared templates: `_templates/global/SurveyBase.html`, `SurveyNavigation.html`, `SurveyProgress.html`, `SurveyReferenceBadge.html`.
- Presentation: `_static/survey_ui/household.js`, `survey.css`, `ASSETS.md`, and the three files under `_static/survey_ui/brand/technology/`.
- Verification: `tests/test_final_http.py`.
- Documents: `README.md`, `README_FINAL.md`, `FINAL_CHANGELOG.md`, `FINAL_TEST_REPORT.md`, `FINAL_DEPLOYMENT_CHECKLIST.md`, `FINAL_DATA_DICTIONARY.csv`.

## QA remediation — 2026-11-17

- Preserved ten historical V2/V3/V5 test modules under `tests/legacy_reference/` and excluded them explicitly from Final discovery; added Final-specific contract, flow, dropdown/browser and deletion tests. The V5 project and its own tests are untouched.
- Corrected the six-task `assign_once` comment; byte-identical matrix/design and allocation AST checks protect the experiment. Marked the old four-task V2.4 exporter as historical.
- Added `scripts/delete_final_participant.py` and `FINAL_DATA_DELETION_GUIDE.md`: offline preview, exact confirmation, Final-only checks, participant-related row/timing deletion in a transaction, and explicit external-copy/worker-buffer limits.
- Added `tests/test_final_browser.py`, `requirements-browser.txt`, and synthetic 375 px screenshots under `test_artifacts/browser/`.
- Added `scripts/postgres_qa.py`, gated to an explicitly acknowledged empty `final_test_*` database; not executed against PostgreSQL.
- Revalidated the schema and dictionary; no column changes were needed. Updated the report, checklist and README with staging/live distinctions.
- Clearly labeled the inherited `docs/` files as historical; Final documentation is maintained in `README_FINAL.md` and `FINAL_*`.

## Survey sequence correction

- Updated both Final session configurations and progress labels to Eligibility / Consent → Housing Choice → Attitudes → Household → Completion. The change applies to newly created sessions. Keep existing sessions on their original runtime and database; no database migration is performed.
- Updated HTTP, browser, configuration and PostgreSQL QA tests for the corrected flow. Six-task assignment, question wording, models, and export schema are unchanged.
