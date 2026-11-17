> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# V3.3.1 — Attitude Slider Discoverability Patch

Unanswered sliders now show a visible gray hollow circle at the center of the existing range, together with **Not answered** and **Drag the circle or tap a position to answer.** The center is a visual starting position, not a selected Neutral answer. Successful explicit interaction uses the existing green solid thumb, selected label and Selected: response text; the initial hint is hidden.

`RatingQuestion.html` retains the same unnamed native range and named native radios. Its five rating labels are now `type="button"` controls with no name, a 64px minimum height, visible keyboard focus and aria-pressed selection states. They form a group named by the question statement. Each label sets the range position and calls the same existing single-radio selection function as dragging; it never submits the form or adds another named answer. Keyboard Enter/Space works on buttons; arrow navigation remains native on the range. The range is described by its current state, instruction and error text.

The gray hollow/green solid appearance is controlled by CSS variables under the existing data-answered state. Both WebKit and Mozilla native thumb rules use those variables. The visible thumb remains 28px in Chromium inside a 48px-high range hit area; the entire track also responds to touch. Five label columns remain aligned with the five ticks. Mobile labels wrap at 14px and desktop labels use 16px. Fonts, Housing cards and shared SSE layout are unchanged.

`attitudes.js` still derives answered state only from a checked native radio. Initialization, focus and resize never check a radio. Deliberate pointer, range keyboard or label activation selects exactly one. In particular an explicit central-thumb/Neutral-label selection records 0; the untouched range's value=0 is unnamed and never submitted. Existing whole-form server validation and error restoration remain unchanged. No-JavaScript users still see the original native radios; the range/label-button wrapper stays hidden.

V3.3.1 is a UI patch recorded in documentation and test metadata only. Questionnaire/flow versions remain V3.3, Housing V2.4, and no schema or historical version label changes. [Completion and screenshots](V3_3_1_COMPLETION.md), [current verification](UI_TESTING.md).

---

The following release documentation is retained as history. The V3.3.1 section above supersedes earlier descriptions of an invisible unanswered thumb.

# V3.3 UI — reordered native sections and five discrete sliders

Existing SSE/Marcellus/Inter, desktop two-card/mobile stacked Housing presentation and native forms are retained. Progress now reads Part A Eligibility & Data Protection; Part B Housing Choice; Part C Household Information; Part D Attitudes. Reference ID begins at Housing Instructions after combined consent/cookie validation and remains at the top-left of the questionnaire, wrapping at the top on mobile. Copy ID behavior is unchanged.

Attitudes uses five vertically spaced native range controls with five evenly spaced tick/label positions. All labels are Strongly disagree / Slightly disagree / Neutral / Slightly agree / Strongly agree. Statement/field mapping and exact introduction are in [ATTITUDE_SCALE](ATTITUDE_SCALE.md). Native range min −2, max 2, step 1 supports mouse drag, touch drag, track selection and arrow/Home/End keys. Visible focus outlines, statement labels, selected-value aria text, status and nearby errors are supplied.

Blank state hides the thumb and labels no position as selected; status reads Not answered. Focus alone does not answer. An explicit pointer/input/navigation-key action selects one native radio. The range has no name; radios are the sole successful controls and native server source. Without JavaScript or unsupported range, the original five-choice radio renderer remains usable. The enhancement adds no external library or storage.

Selected positions have a visible contrasting thumb, selected label and Selected: response text. Server validation errors appear beside each relevant question. Other valid selections are preserved after an invalid POST; corrected errors clear on interaction. A fresh GET/reload safely requires unsubmitted answers again. Only whole-page valid submission saves values.

At375/390/430 px, tracks resize and labels wrap into two lines, with14 px labels and 16 px status/body; native hit area48 px. Desktop 1440 uses the same five positions and 16 px labels. No horizontal scrolling or continuous decimal values. These sizes were checked in Chrome touch emulation; physical Safari/VoiceOver remain a separate untested boundary. [Current evidence](UI_TESTING.md).

---

# Historical documentation before V3.3

The following text is retained verbatim for provenance. Its release-specific ordering, active UI and test results are historical; the V3.3 section above is current.

# Current V2.4 Housing UI

The existing Marcellus/Inter fonts, SSE Header, shared responsive layout, Reference Badge and Copy behavior are unchanged. `random_matrix/Home.html` replaces the active Apartment include. Each Home A/B card shows Power Plant Type (full Nuclear power plant/Oil-fired power plant label), Distance to Power Plant and Monthly Rent. Facility remains task-level context despite repetition in cards. Size is absent from cards and assumed identical in Instructions. Desktop uses two columns; 390px mobile stacks A then B. The Instructions h1 is Choosing a Rental Home; exact generic scenario/budget text appears once.

Radio labels Choose Home A/B preserve raw native A/B coding. No safety/quality color or preferred answer is introduced. Existing 21px attribute values keep facility labels prominent. Household's frozen generic examples remain unchanged. [Final screenshots and checks](UI_TESTING.md), [wording](SCENARIO_FRAMING.md).

---

# Historical UI design notes (pre-V2.4)

# V3.0 — modular attitude questionnaire

The active Part D is one native oTree form with five independently maintained question includes, followed by existing Completion after a valid submission. The SSE header, self-hosted Marcellus/Inter, participant.code Reference ID, neutral container and responsive navigation are retained. Exact words/labels are centralized in [ATTITUDE_SCALE](ATTITUDE_SCALE.md) and `attitudes/questions.py`.

At desktop widths of 1000px and above, each ordinal scale uses five readable columns; the separate DK response occupies its own row. Narrower screens use vertical options with wrapped full labels. No default radio selection. Cards are at least 56px high; all checked controls meet the 44px touch target criterion. Font size stays readable at 375/390/430px, with no horizontal overflow. Checked cards use a neutral gray fill/border and keyboard focus is visible. Native required-field errors appear next to the relevant question; they indicate missing input, not a desirable attitude. Internal variable names and code 99 are not shown as labels.

Only one **Submit and Continue** button is rendered. It uses the existing navigation-label hook; no shared JavaScript was changed, no nested form and no client-only answer storage. JavaScript-disabled completion was tested. Selecting a radio alone does not persist an answer; server validation and successful submission save all five together. Completion now confirms saved responses, while retaining the synthetic Pilot reminder.

[Desktop neutral](ui_previews/v3_1794735919747499000/desktop_1440_attitudes_neutral_clean.png) · [390px neutral](ui_previews/v3_1794735919747499000/mobile_390_attitudes_neutral_clean.png) · [390px DK](ui_previews/v3_1794735342256838000/mobile_390_attitudes_dk.png) · [Completion](ui_previews/v3_1794735342256838000/mobile_390_completion.png). [UI_TESTING](UI_TESTING.md) records evidence and untested physical-device accessibility. Previous release UI descriptions below are historical and are also preserved in the [pre-V3 archive](history/v2_2b_before_v3.zip).


---

> **Current version note — 2026-11-15:** Current V2.2b treatment context appears on each Choice; Instructions is generic with a hypothetical-scenario clarification. Layout/CSS are unchanged. See [SCENARIO_FRAMING](SCENARIO_FRAMING.md) and [current screenshots](UI_TESTING.md). The descriptions below are historical.

# V2.2a — standalone Instructions and clean housing choices

Verified 2026-11-14 (Europe/Stockholm). The native **ScenarioInstructions** page appears once in round 1 after Household. It uses **Part C — Housing Choice Experiment**, **Choosing a Rental Apartment**, the exact generic scenario and budget text, and **Continue to Housing Choices**. The small plant-context label comes from the saved session design and currently reads **Power plant context: Nuclear power plant**.

All four Choice pages share **Choosing a Rental Apartment**, actual **Choice X of 4**, the required preference question, A/B cards and controls, and Continue. Full scenario, budget panel and the old short reminder are absent. Labels are **Floor Area**, **Distance to Power Plant**, **Monthly Rent**. No review panel, extra answer field, tracking field or fifth task is added.

SSE header, Survey Reference ID, Marcellus/Inter, academic container, colors and responsive CSS are unchanged. Cards remain side by side on desktop and stacked on mobile. No imagery or risk cues were added. Server-formatted rent labels and persisted attributes are unchanged.

The only shared UI code edit allows the existing navigation-label script to respect a button's `data-continue-label`; all other buttons retain Continue. The Instructions template uses the existing native form and navigation classes, without a nested form or JavaScript submission handler. It also works without JavaScript.

Browser checks passed at 375/390/430/1440px, including no horizontal overflow and normal validation/submission. Twenty new screenshots cover Instructions, Choice 1, Choice 4, required-answer error and Completion. [UI_TESTING](UI_TESTING.md) records the results and physical-device limitations; [SCENARIO_FRAMING](SCENARIO_FRAMING.md) records exact text and timing. Previous active UI notes are preserved in the [V2.1.1 archive](history/v2_1_1_before_v2_2a.zip). The following sections are historical descriptions, not the current page flow.

---

## V2.0 housing choice implementation history

Part C uses the existing SurveyBase, institutional header, reference badge, self-hosted Marcellus/Inter, neutral palette and responsive housing cards. No new framework or global redesign. `Choice.html` and `Apartment.html` render persisted Python profiles; HTML contains no matrix amounts or randomization logic.

Title: Choosing a Rental Apartment. Actual progress: Choice 1 of 4 through Choice 4 of 4. Every task presents the approved scenario and exactly three attributes in the same order: floor area, distance to nuclear power plant, monthly rent. Only A/B labels are shown; Near/Far backend labels, block, seed and hash are not respondent instructions.

Desktop cards are side by side with corresponding rows aligned. Below 640px, Apartment A and B stack vertically, followed by the same native radio choices. Labels read Choose Apartment A / Choose Apartment B, with no preselection and existing 56–58px minimum card heights. The native Continue button submits the required choice. Errors use existing form styling; no housing-specific JavaScript is needed.

Small shared CSS additions provide spacing only inside the DCE scenario and a screen-reader-only legend. Existing Eligibility/Household/Attitudes styles and content are retained. The shared DEMO/synthetic-use reminders remain because Live is disabled. Neither distance uses hazard/safety colors or symbols.

The reference badge still displays the same participant.code across all four rounds. Mobile and desktop submit identical A/B codes. Synthetic Chrome captures, mobile input checks and physical-device limitations are recorded in [UI_TESTING](UI_TESTING.md).

---

The following design notes are historical V0/V1 implementation records. Their placeholder descriptions do not describe the active V2 Choice page.


# UI design — V1.0 with UI-V0.1 history

The sections below record the UI-V0.1 baseline; the V1.0 additions at the end supersede placeholder and naming descriptions.

Implemented 2026-11-13 in the existing oTree 6.0.15 project. This is a presentation update only. The user mentioned a hand-drawn reference, but no sketch was attached in the conversation; the written layout and visual requirements guided this version.

## Design principles

Academic minimalism: warm off-white surroundings, a white questionnaire, dark type, thin neutral dividers and restrained green accents. No decorative imagery, animation, gradients, heavy shadows or third-party font requests. The header now uses the SSE emblem supplied by the user in `resource/sselogo.avif`, replacing the original text-only placeholder. Its original proportions are preserved, with a PNG fallback for browsers without AVIF support. The header names Stockholm School of Economics and course 5327, with a student-course / not-official-policy-survey notice.

The hierarchy is institutional header → questionnaire label/DEMO badge → current section → page heading → explanatory panel → question/options → navigation. Only the current section number/name is shown. There is no percentage or claim about how many questions remain on conditional routes.

## Native template layout

`_templates/global/SurveyBase.html` extends `otree/Page.html`. It retains the native form, validation summary, scripts and page routing through `super()`. It adds a header, main landmark, footer and shared content blocks. The native title block is empty; the shared content renders one meaningful h1. The empty `.otree-title` is hidden with the documented public selector.

Shared includes:

| Template | Responsibility |
| --- | --- |
| SurveyHeader.html | Institution/course identity and user-supplied SSE emblem |
| SurveyProgress.html | Current section derived from the existing app constant |
| SurveyBackground.html | Consistent explanatory panel; accepts heading and text |
| SurveyNavigation.html | Native `next_button` and DEMO reminder; absent on terminal pages |
| SurveyRadioField.html | Existing oTree field choices, label/legend and nearby server errors |
| SurveyLikertPreview.html | Reusable 1–10 UI preview with unique group and label IDs |

Each of the nine page templates overrides `survey_title`, `survey_intro`, `survey_body` and, for terminal pages, `survey_navigation`. CookiePreferences keeps its existing cookie script and hidden result field. No framework template is overwritten and no nested form is created.

The supported `global_styles` block loads centralized CSS and a small deferred presentation script. The script sets English document language, adds `viewport-fit=cover` to the existing viewport meta and changes the native Next label to Continue. It stores nothing, handles no answers, randomizes nothing and does not intercept submission. Main/header/footer also carry `lang=en` for script-disabled use.

The framework's debug panel and debug tab-title metadata are suppressed on these questionnaire templates so participant/internal data are not exposed as interface copy. Admin tools remain unchanged. Technical participant URLs still exist as part of oTree navigation; this is not a claim that codes disappear from browser internals.

## Typography and colour tokens

The confirmed pairing is **Marcellus + Inter**, served locally from the supplied ZIP files. Marcellus Regular (400) is used for the questionnaire label, section headings, introductory headings and institution name. Main page titles are 36px on desktop and 30px on mobile. Inter is used for body text, question/option controls, Housing A/B labels and attributes, and prices. Body text remains 16px with line-height 1.65; price values use tabular lining figures. Small metadata/badges remain smaller than body text. Inter uses its supplied variable font (weights 100–900) and automatic optical sizing. Both fonts use `font-display: swap` with appropriate system fallbacks and same-origin preloads; no Google Fonts stylesheet or third-party font request is added.

| Token / use | Value |
| --- | --- |
| Page background | `#f7f6f2` |
| Questionnaire surface | `#ffffff` |
| Main text | `#292f30` |
| Secondary text | `#5e6665` |
| Decorative border | `#d7dcda` |
| Explanatory panel | `#f1f3f2` |
| Accent / button | `#305950` |
| Selected option background | `#edf4f0` |
| Interactive unselected border | `#7c8982` |
| Custom error text | `#9c3030` |

Calculated contrast examples: main text/white 13.60:1; secondary text/panel 5.29:1; button white/accent 7.86:1; unselected control border/white 3.65:1. These are specific token checks, not a claim of comprehensive WCAG certification.

## Desktop/mobile layout

Questionnaire/header maximum width is 848px. Desktop card padding is 40px horizontally. Below 640px, the outer margin is 18px and card padding is 18px; header text wraps, card columns collapse and Continue fills the content width. Safe-area insets are included in the outer body padding and header spacing. Nothing is fixed over the content or browser bottom.

| Component | At least 640px | Below 640px |
| --- | --- | --- |
| Household placeholders | Two columns | One column |
| Housing cards | Two equal columns | A then B vertically |
| Housing preview choices | Two columns | One column |
| Rating scale | Ten columns | Five columns × two rows |
| Navigation | Note and button side by side | Note above full-width button |

No experiment value or encoding depends on the viewport. CSS is scoped primarily to project-owned `survey-*` classes and documented oTree selectors. Hover is an enhancement only; focus and checked states are independently visible. Reduced-motion preferences are respected.

## Form controls and validation

Eligibility uses the existing Python fields, values and wording. Each native radio input is rendered inside a full-card label with an explicit `for`, within a fieldset/legend. This retains checked-state rendering after a validation error, keyboard arrow navigation and native/server validation. Field errors remain next to the question; oTree's global summary is retained. Radio cards are at least 56px high, buttons/scales at least 48px; focus rings are 3px with an offset.

Navigation uses the native `next_button` and its ordinary form submission. oTree's existing submit handler disables the button briefly to prevent rapid duplicate clicks; no competing handler or hidden replacement button was introduced. In a script-disabled browser its label remains Next and ordinary server navigation still works.

Household controls are disabled previews with accessible labels. No income bands, country filters, currency, or new answer categories are defined. Participant Code is not shown in the household page.

## Housing comparison preview

Both cards use the same attribute order: facility type, distance, monthly housing cost, housing size. Housing A reads the already stored `scenario` supplied by Python. Housing B is explicitly undefined and supplies no invented numbers or treatment. Facility type remains DEMO / TBD. The instruction requested in the UI brief is followed immediately by a clear prototype explanation.

A/B radios are interactive presentation controls only. Their names have an `ui_preview_` prefix and their form owner is deliberately detached with `form="survey-preview-only"`; there is no such form and no second/nested form is created. They are therefore absent from the native form's FormData even without JavaScript. No housing-choice field or record was added. The browser test confirms that selected previews do not enter the submitted data.

## Likert preview

Five titled fieldsets demonstrate the existing intended constructs. Endpoint labels say “1 · Label TBD” and “10 · Label TBD”; no agreement/risk-direction anchors are invented. The 1–10 radio groups support native keyboard navigation, selected styling and focus. Like A/B previews, they have no native form owner and are not submitted or persisted.

Showing five components together is a UI gallery on the existing placeholder page. It does not change the planned V1 one-question-per-page design, expose the existing five model fields for answers, or create per-question timing records for these previews. Their page continues to have its original page-level timing meaning.

## Accessibility and limitations

There is a skip link, main landmark, one h1, meaningful section headings, labelled controls and live cookie status. Fields use normal browser controls; no mouse-only custom widget is required. Long text wraps and no horizontal overflow was observed at the five requested widths.

Physical iPhone Safari, VoiceOver and other assistive technologies were not available for testing. Chrome mobile viewport/touch emulation is not equivalent to an actual iPhone. Safe-area CSS is implemented but hardware-notch behavior still needs device testing. This phase is not a formal accessibility audit. The supplied 160×162 emblem is displayed at 66px wide on desktop and 48px on mobile without recolouring or distortion. Study wording, endpoints and Housing B attributes remain TBD.

## Python and data boundary

No app `__init__.py`, model schema, settings, matrix, allocation mechanism, timing function or cookie-probe script changed. Three existing Python test/support files required small presentation-related updates: household's old visible-ID assertion was replaced with internal-ID availability plus removal of the old ID copy; the isolated smoke helper and pytest fixture now copy `_templates`. Existing routing and export assertions remain active.

Sources checked against installed 6.0.15: [official template/includes and public CSS interfaces](https://otree.readthedocs.io/en/latest/templates.html), [manual field rendering and validation](https://otree.readthedocs.io/en/latest/forms.html). Native template inheritance blocks were also verified directly in the installed framework and through rendered-page tests.


## File diff summary

New files: seven shared templates under `_templates/global/`; `_static/survey_ui/survey.css` and `survey.js`; `docs/UI_DESIGN.md` and `docs/UI_TESTING.md`; 45 PNGs and checks.json under `docs/ui_previews/`.

Modified files: all five eligibility HTML templates, household/HouseholdInformation.html, random_matrix/MatrixPlaceholder.html, attitudes/AttitudesPlaceholder.html and Completion.html; household/tests.py; tests/test_smoke.py; scripts/smoke_test.py; README.md; docs/CHANGELOG.md. The three Python changes concern test/support compatibility only. No Python data logic, app class, database schema or research variable changed.

No original file was removed. All screenshots were captured from synthetic sessions in a disposable project. The temporary devserver and independent headless Chrome process were stopped after verification.


## Supplied branding assets — 2026-11-13 refinement

Original assets remain untouched under `resource/`. Runtime copies live in `_static/survey_ui/brand/` and `_static/survey_ui/fonts/`. AVIF is preferred with a PNG fallback decoded from the same source image. Marcellus-Regular.ttf and Inter-VariableFont_opsz,wght.ttf are copied unchanged from their archives. Each family includes its original OFL.txt. See the asset [provenance note](../_static/survey_ui/ASSETS.md).

Current preview examples: [desktop introduction](ui_previews/branding/desktop_1440_introduction.png), [375px introduction](ui_previews/branding/mobile_375_introduction.png), [390px comparison](ui_previews/branding/mobile_390_matrix_demo.png). The earlier UI-V0.1 screenshots remain as historical records of the text-only header and system fonts.


## Participant-facing name — 2026-11-13

Use **Coursework Survey** in the shared masthead, browser title, welcome heading and session display labels. The introduction describes household circumstances, housing choices and perspectives without naming nuclear proximity or the research hypothesis upfront. This is a presentation choice intended to reduce topic cues, not a claim that bias has been eliminated. Internal configuration keys and substantive later-section wording remain unchanged. Existing screenshots predate this naming update.


## V1.0 — modular fields and reference badge (current)

The shared title is now **Power Plant Proximity & Housing Preferences Survey**, with **Stockholm School of Economics · Course 5327** subtitle. Existing Marcellus/Inter, logo, colour tokens, 848px container and 640px breakpoint are retained. Nuclear-only hypotheses are not inserted into welcome/consent language; the later research placeholders remain unchanged.

`SurveyReferenceBadge.html` is a shared server-gated component at the questionnaire's top-left, above the masthead. It displays participant.code only after initial consent plus age eligibility. It wraps naturally on mobile, with a minimum 44px Copy ID button, polite success/fallback status and selectable code. CookiePreferences includes the first-display retention hint. Clipboard access occurs only on click and never sends the code elsewhere.

Household now has four vertical `survey-question` sections, each an independent include. Radio controls reuse SurveyRadioField; SurveyNumberField gives each integer input an explicit label, unit, inputmode=numeric, aria-describedby error association and aria-invalid red border. Numeric inputs deliberately use text controls with a numeric keyboard so malformed values can receive the exact requested error instead of being silently sanitized by number inputs. The model fields remain integers. Server and client validation both reject invalid values.

household.js handles rent show/hide/clear and income refusal/clear, then immediate numeric feedback. It does not save answers. Its submit guard only blocks invalid values; valid submits retain oTree's native form, routing and duplicate-click handling. Without JavaScript the conditional rent block remains visible with a conditional instruction, so every user can enter it if needed; the server still ignores inactive values and enforces all rules. No hidden pre-selected answer or dependency on hover is added.

Q2–Q5 deliberately share one page, so no per-question timing claim is made. No Reference page or extra consent checkbox is created. Schema changes are limited to Household's specified variables; cookies, timing and later-app code are unchanged. Desktop/mobile codes are identical.


## V1.1 — concise welcome and combined consent (current)

Institutional header: exactly two text lines, **Stockholm School of Economics** and **Stockholm School of Economics · 5327 Coursework Survey**, plus the existing supplied logo. The previous separate affiliation disclaimer is removed. Welcome now contains two brief paragraphs: study purpose and an overview of household/hypothetical housing/perspective questions. Shared DEMO and synthetic navigation reminders remain while Live is disabled.

AgeConfirmation is first, followed (adults only) by Introduction and a single VoluntaryParticipation page containing privacy, initial consent and optional cookie choice. Excluded participants go straight to terminal Exit. CookiePreferences is no longer an active page. No consent duplicates or new questions are added. Reference badge/hint now start at Household, after consent submission. Cookie controls still use the original script and shared radio component.
