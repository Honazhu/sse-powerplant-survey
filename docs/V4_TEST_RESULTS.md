# V4 test results

Run date: 2026-11-15. Python 3.11.17, oTree 6.0.15, macOS. All runtime application source is unchanged from baseline.

| Check | Result and scope |
| --- | --- |
| Full original pytest suite, sanitized source plus excluded legacy fixtures in a separate temporary harness | 164 passed, 23.42 s |
| Release itself | 145 passed, 19 historical-fixture cases intentionally skipped (see test collection hook) |
| Native oTree bots / CSV / household / live guard | Passed in pytest, fresh synthetic project; eight bot cases |
| 50 entrants / duplicate GET / restart / sequential replay | Passed on SQLite; 25 A / 25 B for entrants |
| Chrome V3.3.1 synthetic suite | Passed: 108 reported checks, 20 generated screenshots; four viewports, touch emulation, no-JS, invalid POST and ghost/Neutral |
| Cookie probe | Four cases passed, Node |
| Native → tasks/long/difference/merged | 11 participant records, 44 unique task keys, 30 valid completed task timings; 44 difference → 44 merged; completed long tasks one chosen alternative |
| Syntax / imports / app sequence / design hash / `pip check` | Passed locally; no fresh Linux installation |
| Production command | Local disposable SQLite startup: HTTP 200; owned process group stopped |
| PostgreSQL, Heroku, real devices / VoiceOver | Not tested |

An initial sandboxed test attempt gave 98 passed, 34 failed and 32 errors because local socket binding was denied and intentionally excluded historical fixtures were absent; the subsequent localhost-enabled runs above resolved these test-environment causes. Test harness outputs and historical test fixtures are outside the release and are not publication artifacts. The real browser never contacted Heroku. The browser server log recorded two WebSocket closing-handshake / socket-not-connected warnings; the same run completed its checks and exports, with SQLite integrity ok and no foreign-key violations. This is not evidence that every network failure is harmless.
