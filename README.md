# SSE 5327 — Power Plant Proximity & Housing Preferences Survey

V4 source packaging candidate: V3.3 flow and attitudes, V3.3.1 slider UI, frozen V2.4 housing design. **Synthetic testing only; the Live configuration is blocked.** This is not authorization to recruit or deploy. Read [the release audit](docs/V4_RELEASE_AUDIT.md) and [handover](docs/V4_HANDOVER.md) before use.

Use Python 3.11 and install `requirements-dev.txt` in a new virtual environment for local testing and analysis. Do not point current models at an existing research database. To run a fresh isolated synthetic pilot:

```sh
python -m scripts.pilot_server --port 8000
```

The helper creates a separate temporary project and database. Its printed address is local only; fill in invented answers. For tests: `python -m pytest -q` and `node tests/test_cookie_probe.js`. Tests requiring excluded historical CSV fixtures are explicitly skipped unless those fixtures are provided in a separate controlled harness. Chrome browser acceptance requires the locally installed Chrome path used by `scripts/run_v33_browser.py`; run it in a disposable copy, because it generates screenshots and exports.

Production uses `otree==6.0.15` and pinned `psycopg2-binary==2.9.13`. Analysis and development additionally need `requirements-dev.txt`. Local synthetic PostgreSQL integration passed; Heroku deployment and the hosted pilot remain unverified. See [V4.1 PostgreSQL deployment fix](docs/V4_1_POSTGRESQL_DEPLOYMENT_FIX.md). Historical documents in `docs/` are references, not authoritative current-flow descriptions. No respondent records or credentials belong in this repository.
