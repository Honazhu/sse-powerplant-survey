"""V2.4 synthetic identification diagnostics; never fits real respondent data."""
import argparse
from collections import Counter
import csv
import importlib
import itertools
import json
from pathlib import Path
import sys
import types
import numpy as np
from scripts.check_facility_design import fit_logit

ROOT = Path(__file__).resolve().parents[1]
package = types.ModuleType('_v24_diagnostic')
package.__path__ = [str(ROOT / 'random_matrix')]
sys.modules.setdefault(package.__name__, package)
m = importlib.import_module(package.__name__ + '.matrix')
r = importlib.import_module(package.__name__ + '.randomization')
f = importlib.import_module(package.__name__ + '.facility_design')
COLUMNS = ['position_A', 'delta_rent_1000', 'delta_far', 'delta_far_x_oil']


def plan(seed, count=50):
    return dict(seed=seed, sequence=r.allocation_sequence(count, seed), design=m.design_payload(),
                design_hash=m.DESIGN_HASH, assignment_method=r.ASSIGNMENT_METHOD)


def contrast(t):
    far = int(t['A']['distance_km'] == 50) - int(t['B']['distance_km'] == 50)
    return [1, (t['A']['rent_sek_month'] - t['B']['rent_sek_month']) / 1000,
            far, far * int(t['facility_type'] == 'oil_fired')]


def sample(seed, count=50):
    p = plan(str(seed), count)
    f.validate_plan(p)
    rows = []
    for i, block in enumerate(p['sequence']):
        a = r.make_assignment(p, block, f'{seed}-person-{i}', i + 1, str(i), 'synthetic')
        for t in a['tasks']:
            rows.append(dict(participant=i, block_id=block, task_index=t['task_index'],
                             set_id=t['choice_set_id'], facility_type=t['facility_type'],
                             premium_sek=t['premium_sek'], **dict(zip(COLUMNS, contrast(t)))))
    return rows


def design(rows):
    return np.array([[row[c] for c in COLUMNS] for row in rows], float)


def wtp_status(fit, near_zero=0.05):
    """Diagnostic guard only. Threshold is an explicit stress-test convention."""
    if not fit['converged']:
        return 'unstable: separation/nonconvergence'
    beta = fit['beta']
    if not np.all(np.isfinite(beta)) or beta[1] >= 0 or abs(beta[1]) < near_zero:
        return 'unstable: nonnegative/near-zero rent coefficient'
    return 'eligible-for-further-inference-not-a-real-WTP-estimate'


def run(destination, replications=500):
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=False)
    canonical = m.design_payload()['choice_sets']
    ranks = {'full': int(np.linalg.matrix_rank([contrast(s) for s in canonical]))}
    patterns = {}
    for block in m.BLOCKS:
        sets = [s for s in canonical if s['block_id'] == block]
        ranks[block] = int(np.linalg.matrix_rank([contrast(s) for s in sets]))
        patterns[block] = []
        for flip_n, flip_o in itertools.product((False, True), repeat=2):
            tasks = [dict(s, A=s['B'], B=s['A']) if (flip_o if s['facility_type'] == 'oil_fired' else flip_n) else s for s in sets]
            patterns[block].append(int(np.linalg.matrix_rank([contrast(s) for s in tasks])))
    diagnostics, fits = [], []
    for seed in range(replications):
        rows = sample(seed)
        X = design(rows)
        oil = np.array([row['facility_type'] == 'oil_fired' for row in rows], int)
        diagnostics.append(dict(rank=int(np.linalg.matrix_rank(X)), condition=float(np.linalg.cond(X)),
            rent_oil_correlation=float(np.corrcoef(X[:, 1], oil)[0, 1]),
            premium_oil_correlation=float(np.corrcoef([row['premium_sek'] for row in rows], oil)[0, 1])))
        if seed < 200:
            groups = np.array([row['participant'] for row in rows])
            rng = np.random.default_rng(seed + 532724)
            eta = X @ np.array([.15, -.8, 1.0, -.3]) + rng.normal(0, .3, 50)[groups] * X[:, 2]
            y = rng.binomial(1, 1 / (1 + np.exp(-eta)))
            fits.append(fit_logit(X, y, groups))
    rows = sample(532724); X = design(rows); groups = np.array([row['participant'] for row in rows])
    separation = fit_logit(X, (X[:, 2] > 0).astype(int), groups)
    guards = [wtp_status(dict(converged=True, beta=[0, b, 1, -.3])) for b in (1, 0, -1e-8)]
    report = dict(purpose='Synthetic feasibility only; no real WTP or statistical-power claim',
        design_version=m.DESIGN_VERSION, design_hash=m.DESIGN_HASH, columns=COLUMNS,
        canonical_ranks=ranks, ranks_all_four_allowed_side_patterns_per_block=patterns,
        simulation_sessions=replications, participants_per_session=50, tasks_per_session=200,
        rank_range=[min(d['rank'] for d in diagnostics), max(d['rank'] for d in diagnostics)],
        condition_range=[min(d['condition'] for d in diagnostics), max(d['condition'] for d in diagnostics)],
        rent_difference_oil_correlation_range=[min(d['rent_oil_correlation'] for d in diagnostics), max(d['rent_oil_correlation'] for d in diagnostics)],
        premium_oil_correlation_at_25_25=[min(d['premium_oil_correlation'] for d in diagnostics), max(d['premium_oil_correlation'] for d in diagnostics)],
        block_specific_premium_oil_correlation={b: float(np.corrcoef([s['premium_sek'] for s in canonical if s['block_id']==b], [int(s['facility_type']=='oil_fired') for s in canonical if s['block_id']==b])[0,1]) for b in m.BLOCKS},
        synthetic_fits=len(fits), converged=sum(fit['converged'] for fit in fits),
        finite_participant_cluster_se=all(np.all(np.isfinite(fit['participant_cluster_se'])) for fit in fits if fit['converged']),
        rent_guard_flagged_fits=sum(wtp_status(fit).startswith('unstable') for fit in fits),
        deliberate_separation_status=wtp_status(separation), rent_boundary_statuses=guards,
        assigned_balance=dict(Counter(row['block_id'] for row in rows[::4])),
        completed_balance='outcome-dependent; not guaranteed by assignment')
    report['gate_passed'] = (set(ranks.values()) == {4} and all(set(v)=={4} for v in patterns.values()) and
                            report['rank_range'] == [4,4] and report['converged'] == len(fits) and
                            report['finite_participant_cluster_se'] and not separation['converged'] and
                            all(g.startswith('unstable') for g in guards))
    (target/'simulation.json').write_text(json.dumps(report, indent=2)+'\n')
    (target/'canonical_design.json').write_text(m.canonical_json(m.design_payload())+'\n')
    with (target/'difference_design.csv').open('x', newline='') as handle:
        writer=csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(report, indent=2))
    return report['gate_passed']


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args=parser.parse_args()
    raise SystemExit(0 if run(args.output_dir) else 1)
