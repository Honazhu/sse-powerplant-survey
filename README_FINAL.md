# Power Plant Proximity & Housing Preferences — Final candidate

**READY FOR STAGING — NOT APPROVED FOR LIVE.** This is an isolated oTree 6 project for the Stockholm School of Economics course research survey. Do not use real respondents until the blockers in `FINAL_TEST_REPORT.md` are resolved. The `survey-v5` directory and its databases remain separate. Never point this code at a Pilot database or resume Pilot participants here. No migration is provided. Do not replace the runtime or database of an existing session created with a different app order; run the corrected release in an isolated environment and create new sessions.

The flow is eligibility and consent → housing choices → attitudes → household including optional feedback → completion. The researcher confirmed that Final will retain V5's six tasks: three nuclear and three oil-fired. The V5 allocation and price/distance matrix are preserved. The export still labels both prior and corrected Final schemas `survey_version=final`; use the session code and recorded session configuration to keep data collected under different orders separate.

## Local setup

Use Python 3.11; install `pip install -r requirements.txt`. From this directory, with no `DATABASE_URL` pointing to real data, use `otree devserver` and create the `survey_final_qa` session in the admin interface. The dev server is for disposable tests, not durable collection. Alternatively, in a fresh isolated directory, run `otree create_session survey_final_qa 20`. Never use resetdb on existing data. QA is labeled `qa`/`synthetic`, and is excluded from the production research export. No synthetic test participant should be created in an actual production database.

The production configuration is `survey_final_production` (`live`/`production`); create a fresh session only after the checklist and test blockers are cleared. Participant start links are created through the oTree session admin interface; no room or participant labels are preconfigured. See `FINAL_DEPLOYMENT_CHECKLIST.md`.

## Export

Use oTree Admin → Data → custom export for **household**, `custom_export`, for a completed-only participant-wide CSV. The separate `custom_export_timing` is for consenting completed production participants. Export is computed from the database, is not appended on page views, and excludes QA and incomplete records. Treat exports as sensitive. The native oTree exports, page times and historical V5 export scripts are raw operational data, not the Final research dataset. The V5 individual-income categories are never mapped onto Final household income.

Submitted form pages are persisted even if the participant does not finish. An offline administrator deletion tool is tested on synthetic SQLite data; PostgreSQL and hosted operations remain unverified. See `FINAL_DATA_DELETION_GUIDE.md`. No automated stale-record cleanup is implemented. The research dataset is completed-only; raw storage, logs, backups and third-party infrastructure may retain technical or incomplete data. See the checklist and test report.

## QA and deletion

For the local Final suite, install `requirements-dev.txt` and optionally `requirements-browser.txt`, then run `python -m pytest -q`. Set `FINAL_CHROME` if Chrome is not at the default macOS path, and set `FINAL_BROWSER_ARTIFACTS` to save synthetic screenshots. Without Playwright or Chrome the browser test is skipped. The separate historical tests in `tests/legacy_reference/` target prior versions and are not counted as Final passes. PostgreSQL staging instructions and a gated test harness are in `FINAL_DEPLOYMENT_CHECKLIST.md`; the offline admin deletion workflow and its limits are in `FINAL_DATA_DELETION_GUIDE.md`.
