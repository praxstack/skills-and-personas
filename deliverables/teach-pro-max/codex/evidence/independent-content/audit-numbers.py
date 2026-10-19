#!/usr/bin/env python3
from fractions import Fraction as F
from pathlib import Path
import subprocess,json,hashlib,math
root=Path(__file__).resolve().parent
rows=json.loads(subprocess.check_output(['node',str(root/'extract-model.mjs'),str(root/'snapshots')],text=True))
errors=[];max_error=0.0
for prior,hit,false,s in rows['base']:
    # Bayes odds form, independent of model's direct flagged-group division.
    posterior=1/(1+F(100-prior,prior)*F(false,hit))
    expected={'defective':100*prior,'sound':100*(100-prior),'trueFlags':prior*hit,
              'falseFlags':(100-prior)*false,'flagged':prior*hit+(100-prior)*false,'missed':prior*(100-hit),'total':10000}
    for key,n in expected.items():
        if s[key]!=n:errors.append(['base-count',prior,hit,false,key,s[key],n])
    err=abs(s['precision']-float(posterior));max_error=max(max_error,err)
    if err>2e-15:errors.append(['base-posterior',prior,hit,false,err])
    assert all(float(s[k]).is_integer() for k in expected)
    assert 0<=s['precision']<=1
# Evolve one-particle occupancy probabilities by the transition matrix, exactly.
# It is an independent iterative Markov update, not the JS exponential expression.
occupancy={};max_diff=0.0;dot_errors=0
for initial,j,ticks,s,dots in rows['diffusion']:
    key=(initial,j)
    if ticks==0:occupancy[key]=F(initial,60)
    prob=occupancy[key];k=F(j,20);left=60*prob;right=60*(1-prob)
    expected={'left':left,'right':right,'leftToRight':left*k,'rightToLeft':right*k,
              'net':k*(left-right),'nextLeft':60*(prob*(1-k)+(1-prob)*k),'total':F(60)}
    for field,value in expected.items():
        err=abs(s[field]-float(value));max_diff=max(max_diff,err)
        if err>5e-13:errors.append(['diffusion',initial,j,ticks,field,s[field],str(value),err])
    assert left+right==60 and 0<=left<=60 and 0<=right<=60
    assert abs((s['left']+s['right'])-60)<1e-12
    assert 0<=s['left']<=60 and 0<=s['right']<=60
    if dots!=[60,60]:dot_errors+=1;errors.append(['dots',initial,j,ticks,dots])
    occupancy[key]=prob*(1-k)+(1-prob)*k
counterexamples={
 'high_hit_low_posterior':{'parameters':{'base':1,'hit':90,'falseRate':5},'posterior_exact':'2/13','percent':float(F(200,13)),'true_flags':90,'false_flags':495},
 'zero_false_flags_strict_growth_exception':{'base1_precision':1,'base50_precision':1,'hit':90,'falseRate':0},
 'closed_barrier_no_relaxation':{'initialLeft':48,'cross':0,'ticks':20,'left':48,'right':12,'net':0},
 'balanced_open_barrier':{'initialLeft':30,'cross':0.2,'ticks':0,'each_direction':6,'net':0},
 'maximum_crossing_one_tick':{'initialLeft':60,'cross':0.5,'ticks':1,'left':30,'right':30}}
result={'snapshot_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'snapshots').glob('*.js')},'base_grid':len(rows['base']),'base_max_posterior_abs_error':max_error,'diffusion_grid':len(rows['diffusion']),'diffusion_max_abs_error':max_diff,'dot_draw_calls':2*len(rows['diffusion']),'dot_conservation_failures':dot_errors,'voice_states':rows['voice'],'counterexamples':counterexamples,'mismatches':errors}
(root/'numeric-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('voice_states','counterexamples','snapshot_sha256')},indent=2))
