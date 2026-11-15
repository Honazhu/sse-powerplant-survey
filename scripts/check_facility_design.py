"""Synthetic design/optimizer diagnostics only; never reads respondent data or opens a DB."""
import argparse, csv, hashlib, importlib.util, itertools, json, math, random
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import importlib, sys, types
package=types.ModuleType('_facility_diagnostics')
package.__path__=[str(ROOT/'random_matrix'/'legacy_v23')]
sys.modules.setdefault('_facility_diagnostics',package)
matrix=importlib.import_module('_facility_diagnostics.matrix')
facility_design=importlib.import_module('_facility_diagnostics.facility_design')
randomization=importlib.import_module('_facility_diagnostics.randomization')


def sample(seed,count=50):
    session_seed=f'session-{seed}'
    blocks=randomization.allocation_sequence(count,session_seed)
    plan=dict(seed=session_seed,design=facility_design.design_payload(),design_hash=facility_design.DESIGN_HASH,
              sequence=blocks,facility_schedule=facility_design.facility_schedule(blocks,session_seed))
    facility_design.validate_plan(plan)
    rows=[]
    for i,block in enumerate(blocks):
        assignment=randomization.make_assignment(plan,block,f'participant-{seed}-{i}',i+1,str(i),'synthetic')
        for task in assignment['tasks']:
            a,b=task['A'],task['B'];coal=int(task['facility_type']=='coal')
            rows.append(dict(participant=i,block_id=block,task_index=task['task_index'],choice_set_id=task['choice_set_id'],
                             near_side=task['near_side'],facility_type=task['facility_type'],Coal=coal,
                             delta_rent_1000=(a['rent_sek_month']-b['rent_sek_month'])/1000,
                             delta_size_m2=a['size_m2']-b['size_m2'],delta_near20=a['near20']-b['near20'],
                             delta_near20_coal=(a['near20']-b['near20'])*coal,position_A=1))
    return rows


def design(rows,scale_size=False):
    return np.array([[1,r['delta_rent_1000'],r['delta_size_m2']/(15 if scale_size else 1),r['delta_near20'],r['delta_near20_coal']] for r in rows],float)


def context_ranks(rows):
    # Separate context models each need position, rent, size and proximity.
    return {facility: int(np.linalg.matrix_rank(design(
        [row for row in rows if row['facility_type'] == facility])[:, :4]))
        for facility in ('nuclear', 'coal')}


def fit_logit(X,y,groups):
    beta=np.zeros(X.shape[1]);converged=False
    def loss(b):
        z=X@b;return float(np.sum(np.logaddexp(0,z)-y*z))
    for iteration in range(100):
        z=np.clip(X@beta,-700,700);p=1/(1+np.exp(-z));w=p*(1-p);H=X.T@(w[:,None]*X);g=X.T@(y-p)
        if np.linalg.cond(H)>1e12 or np.max(np.abs(beta))>35:break
        step=np.linalg.solve(H,g);factor=1.
        for _ in range(30):
            trial=beta+factor*step
            if loss(trial)<=loss(beta)+1e-10:break
            factor/=2
        else:break
        beta=trial
        if np.max(np.abs(factor*step))<1e-8:
            converged=True;break
    z=np.clip(X@beta,-700,700);p=1/(1+np.exp(-z));H=X.T@((p*(1-p))[:,None]*X)
    converged=converged and np.linalg.cond(H)<1e12 and np.max(np.abs(beta))<35
    result={'converged':bool(converged),'iterations':iteration+1,'beta':beta.tolist(),'hessian_condition':float(np.linalg.cond(H))}
    if converged:
        scores=np.array([X[groups==g].T@(y[groups==g]-p[groups==g]) for g in np.unique(groups)])
        inv=np.linalg.inv(H);G=len(scores);N=len(y);K=X.shape[1]
        covariance=inv@(scores.T@scores)@inv*(G/(G-1))*((N-1)/(N-K))
        result['participant_cluster_se']=np.sqrt(np.maximum(np.diag(covariance),0)).tolist()
    return result


def run(destination,replications=500):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    rows=sample(532722);X=design(rows);Xs=design(rows,True);groups=np.array([r['participant'] for r in rows])
    diagnostics=[];context_checks=[];set_counts=defaultdict(Counter);patterns=Counter()
    for r in rows:set_counts[r['choice_set_id']][r['facility_type']]+=1
    for i in range(50):patterns[''.join('C' if r['Coal'] else 'N' for r in rows if r['participant']==i)]+=1
    for seed in range(replications):
        rr=sample(seed);xx=design(rr);cc=defaultdict(Counter)
        context_checks.append(context_ranks(rr))
        for r in rr:cc[r['choice_set_id']][r['facility_type']]+=1
        imbalance=max(abs(c['coal']-c['nuclear']) for c in cc.values())
        correlations=[float(np.corrcoef([r['Coal'] for r in rr],[r[f] for r in rr])[0,1]) for f in ('delta_rent_1000','delta_size_m2')]
        diagnostics.append((int(np.linalg.matrix_rank(xx)),float(np.linalg.cond(xx)),imbalance,*correlations))
    truth=np.array([.15,-.6,.6,-.8,-.4]);fits=[]
    for seed in range(200):
        rr=sample(seed);xx=design(rr,True);gg=np.array([r['participant'] for r in rr]);rng=np.random.default_rng(seed+9000)
        # Shared participant effects create repeated-choice dependence; fitting is a working pooled model.
        eta=xx@truth+rng.normal(0,.30,50)[gg]*xx[:,3]+rng.normal(0,.20,50)[gg]
        y=rng.binomial(1,1/(1+np.exp(-eta)));fits.append(fit_logit(xx,y,gg))
    rng=np.random.default_rng(532722);eta=Xs@truth+rng.normal(0,.30,50)[groups]*Xs[:,3]+rng.normal(0,.20,50)[groups]
    y=rng.binomial(1,1/(1+np.exp(-eta)));example=fit_logit(Xs,y,groups)
    separation=fit_logit(Xs,(Xs[:,3]>0).astype(int),groups)
    support=[]
    for s in matrix.CHOICE_SETS:
        sid,b,ns,nr,fs,fr=s
        for sign,coal in itertools.product((-1,1),(0,1)):
            support.append([1,sign*(nr-fr)/1000,sign*(ns-fs),sign,sign*coal])
    support=np.array(support,float);coal=np.array([r['Coal'] for r in rows]);extended=np.column_stack([X,coal*X[:,1],coal*X[:,2]])
    valid=[f for f in fits if f['converged']]
    report={'purpose':'synthetic feasibility diagnostics, not a power calculation or WTP analysis','numeric_matrix_hash':matrix.DESIGN_HASH,'design_hash':facility_design.DESIGN_HASH,'design_version':'V2.3',
        'seed':532722,'participants':50,'tasks':200,'columns':['position_A','delta_rent_1000','delta_size_m2','delta_near20','delta_near20_coal'],
        'rank':int(np.linalg.matrix_rank(X)),'support_rank':int(np.linalg.matrix_rank(support)),
        'separate_context_ranks':context_ranks(rows),
        'separate_context_rank_min':{facility:min(check[facility] for check in context_checks)
                                     for facility in ('nuclear','coal')},
        'rank_with_zero_coal_main_effect_column':int(np.linalg.matrix_rank(np.column_stack([X,np.zeros(len(X))]))),
        'rank_with_rent_and_size_coal_interactions':int(np.linalg.matrix_rank(extended)),
        'condition_number_raw':float(np.linalg.cond(X)),'condition_number_size_divided_by_15':float(np.linalg.cond(Xs)),
        'set_facility_counts':dict(set_counts),'presentation_patterns':dict(patterns),
        'simulation_sessions':replications,'rank_min':min(d[0] for d in diagnostics),'rank_max':max(d[0] for d in diagnostics),
        'condition_range':[min(d[1] for d in diagnostics),max(d[1] for d in diagnostics)],'max_per_set_imbalance':max(d[2] for d in diagnostics),
        'coal_delta_rent_correlation_range':[min(d[3] for d in diagnostics),max(d[3] for d in diagnostics)],
        'coal_delta_size_correlation_range':[min(d[4] for d in diagnostics),max(d[4] for d in diagnostics)],
        'synthetic_logit_fits':len(fits),'converged_fits':len(valid),'example_fit':example,
        'median_cluster_se':np.median([f['participant_cluster_se'] for f in valid],axis=0).tolist(),
        'wrong_rent_sign_fits':sum(f['beta'][1]>=0 for f in valid),
        'perfect_separation_stress':separation,
        'gate_passed':all(d[0]==5 and d[2]<=1 for d in diagnostics)
                      and all(all(rank==4 for rank in check.values()) for check in context_checks)
                      and example['converged'] and not separation['converged']}
    for r,a in zip(rows,y):r['synthetic_chose_A']=int(a)
    with (destination/'difference_design.csv').open('x',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (destination/'simulation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    sys.exit(0 if run(args.output)['gate_passed'] else 1)
