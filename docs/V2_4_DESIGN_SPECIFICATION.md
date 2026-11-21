> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

> Historical reference: consult V4_RELEASE_AUDIT.md and current source for the current flow and release status. Older versions and evidence links below may not describe this package.

# V2.4 — simplified Housing Choice Experiment

Research instruction accepted on 2026-11-15 (Europe/Stockholm). This is a new design, incompatible with the V2.3 treatment matrix. The existing V3.0 attitude form was found in actual source and is preserved without new questions. Only new isolated synthetic Pilot databases/sessions may run this release. Live remains disabled.

## Research decisions and limits

Primary question: willingness to pay additional monthly rent to move from 10 km to 50 km from a nuclear power plant. Secondary/exploratory question: whether that WTP differs for an oil-fired power plant. Both distances straddle the course's 20 km classification, but the estimate is a discrete 10→50 km contrast, not a causal discontinuity at exactly 20 km and not a safety distance.

Housing size is held identical to simplify the experiment and focus its four choices on distance/rent. There is no randomized size or size coefficient. Oil-fired replaces Coal because the research group explicitly chose this new comparison; no assertion about relative safety, continuous operation, or current Swedish plant availability is made. The 6,500 SEK base rent is the group's supplied fixed design anchor, **not a validated Swedish market average**. Human Pilot checks should assess its plausibility; it is not personalized or updated at runtime.

All near homes cost 6,500 SEK/month. Far homes cost 6,500 + premium, where premium is 0/500/1,000/2,000 SEK. These are fixed monthly amounts for the entire home. S05/S06 deliberately compare equal rents; neither is an attention check or automatic exclusion rule. This forced A/B experiment has no outside option and does not directly measure personal maximum WTP.

## Frozen canonical matrix

| Set | Block | Facility | Canonical Home A: km / SEK | Canonical Home B: km / SEK | Premium SEK |
| --- | --- | --- | --- | --- | ---: |
| S01 | A | nuclear | 10 / 6500 | 50 / 7500 | 1000 |
| S02 | B | oil_fired | 50 / 7000 | 10 / 6500 | 500 |
| S03 | B | nuclear | 50 / 8500 | 10 / 6500 | 2000 |
| S04 | A | oil_fired | 10 / 6500 | 50 / 8500 | 2000 |
| S05 | B | nuclear | 10 / 6500 | 50 / 6500 | 0 |
| S06 | A | oil_fired | 50 / 6500 | 10 / 6500 | 0 |
| S07 | A | nuclear | 50 / 7000 | 10 / 6500 | 500 |
| S08 | B | oil_fired | 10 / 6500 | 50 / 7500 | 1000 |

Block A = S01/S04/S06/S07. Block B = S02/S03/S05/S08. Each has two tasks of each facility, every premium once, and one canonical Near-A and one Near-B per facility. Facility is permanently attached to its V2.4 set. In a task both homes share the same plant type. It is task-level context even though shown prominently inside both cards.

## Provenance and canonical hash

`DESIGN_VERSION = "V2.4"`; `survey_version = wording_version = numeric_matrix_version = treatment_design_version = "V2.4"`. The independently stored wording version concerns language; the design version/hash concern the frozen experiment. Existing numeric provenance fields refer to the complete V2.4 payload in this release, not to the old V2.0 numeric matrix.

SHA-256: `77b7ca09b110d974140745fe583049c18ce1a56290e550969e0279c08e3bde39`.

Input: UTF-8 `json.dumps(design_payload(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)` from `random_matrix/matrix.py`, with no trailing newline. It includes eight canonical A/B profiles, stable set IDs, block membership, base/premium/distance levels, facility scope, size assumption, allocation/order/side rules and absence of demographic inputs. [Canonical JSON](v2_4_evidence/design/canonical_design.json) has one trailing newline for readability; strip it to reproduce the hash. Wording is separately versioned; it is not part of this hash.

V2.3's `4c925a9034bcfebb4dd15e904d4f345b6c1422f169b96f4c50b249a3558bcb7e` and V2.0's `96862c147a85b30d887c0a77432805011ae6e755e608a0c8e408a82571dd5053` remain historical only. Frozen historical helpers are in `random_matrix/legacy_v23/`; the complete prior source/docs/tests are in [pre-V2.4 snapshot](history/pre_v2_4_source.zip). Old evidence and CSVs remain at their original paths.

## Assignment and persistence

Session creation persists a cryptographic session seed, full design/hash, and a sequence of independently shuffled [A,B] pairs truncated to session capacity. At first eligible Choice GET, an atomic conditional Player claim and atomic Subsession cursor increment persist all four task profiles in the same oTree request transaction. Instructions do not allocate or start a choice timer. Each session is independent. Every assigned prefix has block counts differing by at most one; 50 actual entrants in one session yield exactly 25/25. Unused participant slots are not assigned. Dropout claims are never recycled.

A separate saved participant seed uniformly shuffles the four sets. For each facility independently, shuffle [A,B] and associate these Near sides with its two sorted set IDs. This gives one Near-A and one Near-B per facility and two per side overall. Depending on the required Near side, swap the **entire canonical Home profiles**. `side_swapped=1` means displayed A=canonical B and displayed B=canonical A. There are 24 orders × 4 allowed side patterns per block. No browser RNG, demographic dependence, price generation or adaptive pricing exists.

Persisted snapshot validation verifies current hash, block membership, exact profiles/context, premiums, order and side balance. Rendering checks native task columns against the snapshot. Refresh returns the saved assignment; stale POSTs are redirected by native oTree page indexes and cannot overwrite earlier responses. Assignment, exposure, task completion, DCE completion and whole-survey completion are distinct. Report **assigned balance** using module_started and **completed balance** using module_completed separately; equality of completed counts is not guaranteed.

## Data and analysis

`choice` (native) / `choice_ab` (alias) is the displayed A/B response. `choice_set_id` / `set_id` preserves the original V2.4 set identity. Chosen facility/distance/rent/far/near20 are saved from `task[choice]`, never from canonical A/B. `near20=int(distance_km<20)` and `chosen_far=int(chosen_distance_km==50)`. Existing native A/B distance/rent fields are retained; analysis aliases `home_A_*` / `home_B_*` make the Home terminology explicit. No synthetic values populate old size columns.

Native respondent-wide, DCE wide, tasks, long and difference outputs share `(session_code, participant_code)` and task_index 1–4. All four planned task rows survive dropout; two alternative rows survive for every task. A submitted task has one chosen=1 and one chosen=0; unanswered tasks have both chosen values missing. All formats carry saved version/hash and the actual display snapshot. The exporter validates source/snapshot/response/completion agreement before writing new files and refuses existing destinations.

V2.4 binary logit:

`P(choose A) = Λ(alpha_A + beta_r * delta_rent_1000 + beta_f * delta_far + delta * delta_far_x_oil)`.

All differences are **A minus B**: `(rent_A-rent_B)/1000`, `far_A-far_B`, and `(far_A-far_B)*oil`, with nuclear=0 and oil_fired=1. `chose_A=1` for A, 0 for B, blank if unanswered. The intercept is an A-position preference. Facility's common main utility effect cancels within task; a standalone Oil regressor in A-choice space would instead concern an Oil-specific side preference and is not an overall facility preference. Distance km and near20 are deterministic equivalents at two levels and must not enter as independent main effects.

`WTP_N = -1000 * beta_f / beta_r` (primary), and `WTP_O = -1000 * (beta_f + delta) / beta_r` (secondary/exploratory), in SEK/month for moving 10→50 km with other housing conditions held constant. A common rent coefficient is a modeling restriction. Coefficients and WTP ratios depend on specification, hypothetical choices and perceived context; no safe-distance or real-market causal claim follows.

Use participant-cluster standard errors or a justified repeated-choice model; 50 people × four tasks are 50 respondent clusters, not 200 independent people. Full rank is not adequate power, precision or absence of separation. Report uncertainty in the rent denominator and WTP ratio. Nonnegative/near-zero rent coefficients or separation imply unstable valuations; do not force positive WTP. The diagnostic helper's near-zero cutoff 0.05 per 1,000 SEK is an explicit test convention, not a prespecified production inference rule.

There is no formal real-data WTP estimator. `scripts/check_v24_design.py` uses only invented outcomes and tests executable pooled Logit, clustered standard errors, full/block/orientation ranks, correlation and separation/denominator boundaries. [Results](v2_4_evidence/design/simulation.json): all required ranks=4; 500 sessions retain rank 4; 200/200 moderate synthetic fits converge; separated outcomes and zero/wrong-sign rent denominators are flagged. No real WTP results are claimed.

Price/type dependence: at 25/25 block assignment each type receives each premium 25 times, so pooled premium–Oil correlation is exactly 0. Within Block A/B it is respectively +0.1690/−0.1690. Displayed A−B rent differences have random finite-sample correlations with Oil (−0.2621 to +0.1702 across 500 simulations). Unequal completion can disturb balance. Facility switching, order, hypothetical framing and the preserved post-choice nuclear attitudes may affect interpretation and should be assessed during human usability testing.

## Compatibility boundary

New columns are created in fresh databases only. Native block_id is now a String A/B; archived V2.3 uses integer 1/2/3. Historical model/schema are not migrated. Old size fields remain declared but NULL in V2.4. The old `facility_assignment_seed` is blank because facility is frozen, while `facility_type_assignment` stores the fixed map. Participant random_seed and session seed still record actual random draws.

`exports.py` dispatches by saved survey version to `exports_v24.py` or the preserved historical adapter. It rejects files mixing V2.4 and historical designs; run separate conversions. Historical Coal never becomes Oil, old 10/30 never becomes 10/50, old missing metadata is never filled with V2.4 defaults, and old size differences retain their original meanings. V3 attitudes remain independently versioned and their merge validates the selected DCE adapter before joining. Human Pilot means supervised invented responses under the existing consent; Live, deployment and Git push are outside this release.
