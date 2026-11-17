> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

> **Current version note — 2026-11-15:** V2.2b retains the V2.2a timing flow below, with survey/wording V2.2b and treatment design V2.3. Join task timing to the saved facility_type; timing.py is unchanged. See [current evidence](UI_TESTING.md).

# Page timing and cookies — V2.2a flow / V2.0 design

## V2 choice-task timing

`timing.py` and the optional cookie probe remain unchanged. Random Matrix creates one native ScenarioInstructions completion in round 1, then four Choice completions in rounds 1–4. The existing `attitudes_custom.csv` exports native consecutive-completion deltas for all apps. No additional timing field or new timing algorithm is introduced.

In V2.2a, Instructions duration is measured from Household completion to Instructions submission. Choice 1's native duration starts at that Instructions completion; the first-render task timer is also unset until Choice 1 is rendered. In V2.1.1 the first task included full instructions, so first-task durations must not be pooled across those wording versions without acknowledging the different page structure.

Refreshing Instructions creates no completed timing event, allocates no block and starts no Choice timer. Leaving on Instructions gives no completed Instructions duration and leaves all choice outcomes/timers missing. A duration records elapsed time, not proof of reading. Never exclude respondents automatically using Instructions time.

The isolated HTTP test waits 2.1 seconds on Instructions, checks the separate native event and verifies Choice 1's timer starts only after submission. Browser exports contain five Instructions events and eighteen submitted Choice events across four complete and one partial synthetic participants. [Timing evidence](ui_previews/v2_2a_1794693463956067000/timing-verification.json) · [Native PageTimes](../data/synthetic/v2_2a_browser_1794693478137951000/page_times.csv).

Part C additionally stores `task_started_at` at the first server render of each task, `task_submitted_at` on its successful A/B submission and `task_duration_s = submitted − started` in floating-point seconds. These timestamps use UTC Unix epoch seconds. Reload/validation/re-entry do not restart the timer. Waiting away from the tab and process downtime count toward this wall-clock interval. It is not active engagement or an attention measure.

`task_timing_status` is `not_submitted`, `ok`, `missing_start` or `clock_reversed`. A missing/reversed baseline gives a blank duration, never an invented zero. An unsubmitted task has blank submitted_at/duration, including a task that was displayed and then abandoned. Assigned-but-unseen tasks also have blank started_at and task_displayed=False.

The task timer and native `seconds_on_page` have different starting events and precision; their values need not match. Neither cookies nor income/age affect timing. No response quality threshold or WTP imputation is applied.

## Measurement

The current layout records **one duration per submitted page**. Household contains Q2–Q5 together, and VoluntaryParticipation combines privacy, consent and cookie preference. These pages do not provide separate durations for individual questions. `timing.iter_page_durations(rows)` derives the elapsed time between consecutive native oTree completion events for the same `(session_code, participant_code)`. Native InitializeParticipant supplies the first baseline. The helper preserves native event order, including interleaved participants.

This is server wall-clock elapsed time in integer seconds, including reading, answering, validation retries, refreshes, network delay and time away from the tab. It is not active engagement, focus time or millisecond reaction time. Reloading does not submit a page or reset the native preceding-completion baseline. A one-question page provides a question-level elapsed measure; pages containing instructions or placeholders must remain labelled as page measures.

Missing baseline or reversed clock produces blank duration and a status flag. A genuine zero-second interval is valid. Unsubmitted, abandoned and terminal Completion pages have no completed-duration row. A normal terminal Exit also has no row unless submitted (the bypass-resistance bot deliberately does so). No attention cutoff, exclusion threshold or behavior model is defined in V0.

## Function and exports

```python
from timing import iter_page_durations

# rows: dictionaries read from native oTree PageTimes CSV
page_durations = list(iter_page_durations(rows))
```

The function uses only Python's standard library. The oTree adapter `export_page_durations(players)` reads native timing events and filters to the requested participant/session keys. `attitudes.custom_export` makes it available in admin Data. All four apps are covered by that export; placing the adapter in attitudes does not limit records to attitude pages.

The isolated smoke helper writes `attitudes_custom.csv` in a new timestamped synthetic bundle. This is long format. Join its `participant_code` and `session_code` with the corresponding dotted columns in `all_apps_wide.csv` for wording version, eligibility and completion. Native PageTimes does not itself contain wording metadata. Retain timing version `page-completion-delta-v1` and the questionnaire release: V2.2a separates Instructions; V1.1 combined cookies with VoluntaryParticipation; V1.0 had a separate CookiePreferences event.

## Cookie choice and support probe

Cookie preferences are on VoluntaryParticipation, after the initial adult screen and brief welcome. There is no preselected answer. Allow triggers a first-party test cookie with a constant value, followed immediately by deletion; no identifier is stored in it. Refusal performs no cookie access. Browser blocking is recorded as blocked, while no script execution is not_tested. The status is a client-reported capability observation, not tamper-proof evidence.

Refusing or blocking this optional probe does not change eligibility or page timing. The participant's oTree URL still identifies the allocated slot. This choice is not a control over every framework/host cookie; inventory and final cookie wording remain TBD. Do not use cookies to deduplicate real people or claim they make the data anonymous.

## Validation and limitations

Native bot integration checks exercise one-question screening flow, custom timing export, exclusion, cookie refusal/blocking and Completion. Deterministic unit tests verify elapsed-time arithmetic and bad-baseline handling. Node VM tests check that the probe does not run on load/refusal, deletes its cookie, and handles blocked browser access. These checks do not replace a graphical browser/hosting test before recruitment.

Reference: [oTree admin page-times export](https://otree.readthedocs.io/en/latest/admin.html#export-data), plus installed 6.0.15 event/export source inspected on 2026-11-13. No live-data analysis or production deployment was performed.


## What “Since” in Session Monitor means

Verified against the installed oTree **6.0.15** implementation: admin labels `_last_page_timestamp` as **Since**. `session_monitor.js` converts the timestamp into a `timeago` display. For example, **2m** is an approximate relative age in minutes, not a switch in export units or a finalized question duration. The timestamp is updated by native page-completion/progression handling; it is not a keystroke or active-attention clock. A participant still on a page has not generated that page's completed-duration row.

`attitudes_custom.csv` continues to use integer **seconds_on_page** (for example, a computed 120-second interval exports as 120). Since and the completed-duration export serve different purposes. Refresh, validation retries and time away can contribute to elapsed duration. No per-question breakdown is available for Household's four questions or the combined consent/cookie page. timing.py and its calculation are unchanged.
