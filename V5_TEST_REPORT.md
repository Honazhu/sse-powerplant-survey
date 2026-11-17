# V5 test report — 2026-11-16

Environment: macOS, Python 3.11 from the existing local development environment, oTree 6.0.15, isolated synthetic SQLite projects and local loopback HTTP. No production connection. `python -m pytest -q tests/test_v5_design.py tests/test_v5_http.py`: **3 passed**. The HTTP test includes server restart and saved database recovery. Two inherited timing helper tests and fifteen historical numeric-validation tests also passed (17 total) from an isolated test project; the latter cover retained V4 helpers, not the new categorical form. An initial attempt from `/private/tmp` failed collection because oTree could not find `_static`; rerunning from the isolated project passed. Bind required local sandbox escalation, approved automatically. Tests and data are synthetic.

| Acceptance item | Result | Evidence / limits |
|---|---|---|
| Age No / Yes | PASS | HTTP Exit / privacy |
| Participation No without cookie | PASS | HTTP Exit |
| Participation Yes, no / missing cookie | PASS | HTTP completed; six timing values empty and no subsequent native page-time rows |
| Participation Yes, cookie Yes | PASS | HTTP completed; six Choice durations and opt-in timing export |
| Dropout after question 2 / 5 | PASS | Neither in formal completed export |
| Six distinct sets, plant match | PASS | 1,000 seeds; 16 permitted subsets observed; persisted snapshot validation |
| Order and refresh | PASS | Same rendered page on repeat GET; seed reproduces assignment; no browser back navigation test |
| Display versus stored data | PASS | HTTP test compares both rendered cards, set IDs and selected A/B against export and snapshot |
| Repeated submit / refresh completion | PASS, limited | Sequential conflicting replay and refresh preserve answers; no conflicting concurrent requests |
| Missing/category semantics | PASS, limited | Don't know, prefer not, unanswered cookie, no-rent NULL, stale valid rent cleared, Yes+Nothing; not all combinations |
| Income ranges / rent categories / children / education | PASS, limited | Choice lists and representative HTTP values; every category is not individually submitted |
| Country codes and labels | PASS | Frozen 249-entry local ISO alpha-2 data, uniqueness, SE/CN/HK/MO/TW; representative HK submission |
| Real-world exposure removed | PASS | Not in V5 form; historical field retained |
| Completed-only CSV | PASS, limited | Three completed rows; underage, refusal and 2/5 dropouts excluded. Wide row has all six tasks. |
| Local restart | PASS | Formal CSV equal after stopping/restarting disk-backed synthetic server |
| Existing full suite | FAIL / incomplete | `pytest -q --maxfail=5` stopped with five setup errors in inherited `tests/test_attitudes.py`: fixture assumes four questions. Further cases were not run. |
| PostgreSQL same-person / multi-person concurrency | NOT TESTED | No postgres, psql, Docker, or isolated service/driver was available. |
| PostgreSQL export during writes / rollback / retry | NOT TESTED | Requires disposable PostgreSQL and concurrency harness. |
| Legacy V4 session resume / export | NOT TESTED | Design chooses separate V4 runtime/database, not in-place resume. No historical fixtures included. |
| Mobile / browser / accessibility | NOT TESTED | HTTP is not visual or browser automation. |
| Heroku restart / multi-dyno | NOT TESTED | No hosted service or credentials used. Local dyno files are not durable. |
| Deletion from database and prior CSV copies | NOT TESTED | No complete deletion implementation exists. |

Do not infer PostgreSQL, real-user, security, or deployment readiness from the SQLite checks. The V4 bots and numerous inherited tests still encode the V4 flow and require migration; full test suite remains a release blocker.
