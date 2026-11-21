> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# Privacy and data management — V2.0

V2 update: only synthetic Pilot use remains enabled. Part C now records four housing choices, their frozen assignments and server wall-clock timing. No new directly identifying information is collected. The anonymous reference mechanism and all participation wording remain unchanged. New V2 participants receive an assignment only after eligibility and Household completion; the preallocated DEMO-fixture description below applies to historical V0 records only. Historical exports/database remain preserved. Institution/hosting decisions below remain unresolved; this implementation does not authorize real recruitment.

## Technical scope

V0 is local synthetic testing only. Do not recruit respondents or enter real household/attitude information. No name, email, phone, exact address, birth date, custom IP capture, tracking analytics or browser fingerprinting is added. V1 exposes household categories and numeric rent/net-income inputs for invented Pilot responses only. Attitude fields remain unsubmitted previews.

Use oTree's built-in `participant.code` as a technical respondent key. Do not add a second identifier, populate `participant.label` with personal information, or use named recruitment links. Native exports also contain session codes, page metadata and timestamps. oTree has built-in label and external-platform ID columns; these remain unused by this scaffold. Native bot tests may create synthetic labels internally. Export columns must be reviewed before any future sharing.

A random participant code alone is not proof of anonymity or GDPR compliance. Codes and combinations of socioeconomic variables may allow singling out or linkage. Pseudonymised data can remain personal data; true anonymisation requires the individual no longer be identifiable. See the [European Commission's explanation](https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en). This file records technical measures and unresolved responsibilities, not a legal compliance certification.

## Participant information: TBD before real use

The school/research team must confirm the controller, contact, purposes, legal basis, optionality, risks, recipients, transfers, retention period, access rights and complaint/withdrawal route. Agreement to participate in an experiment must not automatically be treated as the correct legal basis for every processing operation. The V1 initial participation page now includes purpose, voluntary participation, course-instructor use and deletion contact. These implemented statements do not resolve the remaining institutional approvals or authorize real recruitment.

Age screening comes first; under-18 respondents skip the participation and cookie page, and participation refusal blocks subsequent survey modules. The local database still contains the participant slot, screening outcome, technical metadata and a preallocated DEMO fixture. Exit does not erase these automatically. The policy for retaining/deleting screening records is TBD and must be settled before recruitment.

## Storage, access and deletion

Local SQLite, logs, secrets, raw data and exports are ignored by Git. Access is restricted operationally to the developer's machine; `.gitignore` is not encryption or access control. No production retention deadline has been invented. Before real data, specify approved storage, access roles, encrypted transport/storage, backup retention, deletion owner and a documented deletion schedule.

Define how withdrawal requests can be located without collecting unnecessary identity data and explain any limits after anonymisation. Deletion must address working files, exports and backups, not just the current database. Do not claim that stopping or closing the browser removes saved answers. Do not use `otree resetdb` as an ad hoc data-subject deletion procedure.

## School and hosting confirmations still required

The school's data protection/ethics requirements and any processor agreement remain **TBD**. For a future host (including oTree Hub or its underlying hosting service), confirm region, subprocessors, international transfers, access controls, logging/IP retention, backups and deletion support. Application-level omission of IP capture does not establish that the web server, proxy or platform records no IP addresses.

Never commit real answers, respondent URLs, private exports or production logs to a public repository. Only clearly artificial `data/synthetic/` examples are allowed in source control. No real participant data was collected in V0.


## Optional cookie probe and behavioral timing — V0 addition

An eligible respondent can allow or refuse a temporary first-party cookie capability test. Only Allow accesses `document.cookie`. The probe writes `nuclear_cookie_probe=1`, reads it, and immediately attempts deletion with Max-Age=0; it uses Path=/, SameSite=Lax, and Secure on HTTPS. It has no participant identifier and no persistent expiration. No analytics/advertising cookie is introduced. Browser policies may block all operations; the result then says blocked. With JavaScript disabled it remains not_tested. A refusal triggers no probe and does not stop the questionnaire.

The stored choice controls this probe only, not oTree/admin/session cookies or cookies of a future host. Actual platform cookies must be inventoried before a real notice is approved. Do not claim that a decline removes cookies already placed by framework/hosting code, or that this DEMO notice completes a legal consent process.

Page completion timestamps already exist in oTree. The shared timing function calculates intervals for the same participant/session, independently of cookies. This introduces a behavioral analysis purpose that must be disclosed and included in the school-approved retention/access plan before real use. V0 records synthetic timing only. Do not infer attention, dishonesty or respondent quality from elapsed time alone. The optional-cookie choice does not opt a participant out of disclosed server page timing; they may decline participation or stop the survey.


## V1.0 reference, contact and deletion handling

The neutral study name is **Power Plant Proximity & Housing Preferences Survey**. Before Household, the existing consent page displays the exact Privacy & Data Use text recorded in [QUESTIONNAIRE](QUESTIONNAIRE.md). It says responses are for a university assignment at SSE and shared with the course instructor for assessment. There is no duplicate acknowledgement page.

After consent and age qualification, the shared top-left badge exposes only the already allocated `participant.code`. Before that it is hidden from the participant UI. The badge stays the same across apps and reload; it is distinct from a scenario/treatment identifier. Copying is an explicit local clipboard action with selectable-text fallback and no added network call, persistence or copy-event log.

The stated deletion contact is **43086@student.hhs.se**. Respondents are instructed to include the Survey Reference ID. The questionnaire does not ask for their email or send any email. Correspondence received outside the app must stay outside research/analysis datasets; access and retention for that correspondence must be set separately. Avoid adding the requester's address or message to participant.label or household fields.

Operational deletion procedure still requires an approved owner and policy: locate the code in the appropriate session, review the request under applicable requirements, apply the approved deletion/anonymisation action to primary records, extracts and working files, and account for backups and shared instructor copies. Log only what the approved process requires, separately with restricted access. Do not promise automatic deletion, a response deadline, full anonymity or universal erasure from backups. Controller, lawful basis, retention periods, access roles, school approval and host arrangements remain **TBD**.

V1 privacy minimisation: adult category only, no birth date; personally paid rent and after-tax income in SEK; generic approx. 20 km power-plant exposure with no location, plant name or coordinates. Q2–Q5 share one page timing observation. Cookie probe/timing behavior and Live blocking are unchanged.


## V1.1 presentation and order

The first page requests only adult confirmation. Eligible-age visitors read the brief welcome, then the combined privacy/participation/cookie page. The reference badge stays hidden until both age and participation conditions pass; first display is Household. A refusal does not require a cookie decision. The probe remains optional and its choice remains separate from agreeing to participate. No new claim of GDPR compliance or data collection permission is introduced by combining the layout.
