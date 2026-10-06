import sys, random, itertools
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import simulator as sim
from collections import Counter
d=sim.data()
W=d.words
def match(tok,w):
    if tok.startswith('mod:'): return w['modifier']==tok[4:]
    if tok.startswith('stem:'): return w['stem']==tok[5:]
    if tok.startswith('part:'): return w['part']==tok[5:]
    return w['word']==tok
def kv(p): return dict(x.split('=',1) for x in p.split(';'))
def indep(ws,y):
    ct,p=y['condition_type'],y['params']; names={w['word'] for w in ws}
    if ct=='count_same_modifier': a=kv(p); return sum(w['modifier']==a['mod'] for w in ws)>=int(a['n'])
    if ct=='count_same_stem': a=kv(p); return sum(w['stem']==a['stem'] for w in ws)>=int(a['n'])
    if ct=='count_same_part':
        c=Counter(w['part'] for w in ws if w['part'] not in('','SM')); return max(c.values(),default=0)>=int(kv(p)['n'])
    if ct=='count_tail_same_part':
        c=Counter(w['part'] for w in ws if w['position']=='語尾' and w['part'] not in('','SM')); return max(c.values(),default=0)>=int(kv(p)['n'])
    if ct=='singles_eq': return sum(w['type']=='単独' for w in ws)==int(kv(p)['n'])
    if ct=='count_in_set': a=kv(p); return sum(any(match(t,w) for t in a['set'].split('|')) for w in ws)>=int(a['min'])
    if ct=='all_in_set': return all(any(match(t,w) for t in kv(p)['set'].split('|')) for w in ws)
    if ct=='contains_all': return any(all(t in names for t in g.split('|')) for g in p.split('/'))
    if ct=='one_from_each':
        groups=[g.split('|') for g in p.split(';')]
        return any(all(any(match(t,w) for t in groups[i]) for i,w in enumerate(perm)) for perm in itertools.permutations(ws,len(groups)))
    if ct=='pair_same_stem_modifiers':
        ms=p.split('|'); return any(all(any(w['stem']==s and w['modifier']==m for w in ws) for m in ms) for s in {w['stem'] for w in ws if w['stem']})
    raise Exception(ct)
rng=random.Random(3)
def mask(ix): return sum(1<<i for i in ix)
bad=0;tested=0;hitcount=Counter()
sets=[tuple(rng.sample(range(d.nw),4)) for _ in range(5000)]
for yi,y in enumerate(d.yaku):
    toks=[]
    ct,p=y['condition_type'],y['params']
    pool=set()
    for tok in itertools.chain.from_iterable(g.split('|') for g in p.replace('/',';').replace('set=','').replace('min=','').split(';')):
        for i,w in enumerate(W):
            if '=' in tok: continue
            try:
                if match(tok,w): pool.add(i)
            except: pass
    # stem/mod based
    for k,v in (kv(p).items() if '=' in p and ct not in('count_in_set','all_in_set') else []):
        if k in('mod','stem'):
            for i,w in enumerate(W):
                if w['modifier' if k=='mod' else 'stem']==v: pool.add(i)
    for i,w in enumerate(W):
        if w['word'] in p.replace('|',';').replace('/',';').replace('=',';').split(';'): pool.add(i)
    pool=sorted(pool) or list(range(d.nw))
    for _ in range(150):
        k=min(4,len(pool)); base=rng.sample(pool,k)
        rest=[i for i in rng.sample(range(d.nw),8) if i not in base][:4-k]
        sets.append(tuple(base+rest))
sets=[s for s in sets if len(set(s))==4]
for s in sets:
    ws=[W[i] for i in s]; m=mask(s)
    fast=set(d.raw_hits(m)); slow={i for i,y in enumerate(d.yaku) if indep(ws,y)}
    tested+=1; hitcount.update(slow)
    if fast!=slow:
        bad+=1; print('MISMATCH',[W[i]['word'] for i in s],[d.yaku[i]['name'] for i in fast^slow])
print('sets',tested,'mismatch',bad,'yaku covered',len(hitcount),'/',len(d.yaku))
