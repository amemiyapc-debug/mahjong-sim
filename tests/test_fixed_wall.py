import sys, random, itertools
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import simulator as sim
from collections import Counter
d=sim.data(); rng=random.Random(21)
allw=list(range(d.nw)); heads=set(d.head_idx)
wt=[(i,Counter(d.W[i].nonzero()[0].repeat(d.W[i][d.W[i].nonzero()[0]]).tolist())) for i in allw]
def slow_sets(cnt):
    c=Counter({k:v for k,v in cnt.items() if v>0}); out=set()
    def dfs(used,head):
        if not c:
            if head and len(used)==4: out.add(frozenset(used))
            return
        t=min(c)
        if not head and t in heads:
            c[t]-=1
            if c[t]==0: del c[t]
            dfs(used,True); c[t]=c.get(t,0)+1
        if len(used)<4:
            for i,wc in wt:
                if i in used: continue
                if all(c.get(k,0)>=v for k,v in wc.items()):
                    for k,v in wc.items():
                        c[k]-=v
                        if c[k]==0: del c[k]
                    dfs(used|{i},head)
                    for k,v in wc.items(): c[k]=c.get(k,0)+v
    dfs(frozenset(),False)
    return out
counts=sim.fixed_wall_counts()[0]
wall=[t for t in range(d.T) for _ in range(int(counts[t]))]
# --- 1) find_complete と総当たり(13枚の完全一致)
bad=0;n=0;wins=0
for trial in range(300):
    pick=rng.sample(allw,4); h=np.zeros(d.T,dtype=np.int8)
    for i in pick: h+=d.W[i]
    h[rng.choice(d.head_idx)]+=1
    tiles=[t for t in range(d.T) for _ in range(h[t])]
    for _ in range(rng.choice([0,0,1])):
        tiles[rng.randrange(13)]=rng.choice(wall)
    h=np.zeros(d.T,dtype=np.int8)
    for t in tiles: h[t]+=1
    slow=slow_sets({k:int(v) for k,v in enumerate(h) if v})
    fast=sim.find_complete(h)
    n+=1; wins+=bool(slow)
    fastset=None
    if fast is not None:
        m=fast[2]; fastset=frozenset(i for i in range(d.nw) if m>>i&1)
    if bool(slow)!=(fast is not None) or (fast is not None and fastset not in slow): bad+=1; print('MISMATCH find_complete',slow,fast)
print('find_complete trials',n,'complete(brute)',wins,'mismatch',bad)
# --- 2) テンパイ判定
bad=0;n=0;ten=0
for trial in range(40):
    seed=rng.randrange(10**6)
    st=sim.FixedSetup(seed)
    pick=rng.sample(allw,4); h=np.zeros(d.T,dtype=np.int16)
    for i in pick: h+=d.W[i]
    h[rng.choice(d.head_idx)]+=1
    tiles=[t for t in range(d.T) for _ in range(h[t])]
    for _ in range(rng.choice([1,1,2])):
        tiles[rng.randrange(13)]=rng.choice(wall)
    hand=np.zeros(d.T,dtype=np.int8)
    for t in tiles: hand[t]+=1
    rem=st.total.astype(np.int16)-hand
    if (rem<0).any(): continue
    for t in rng.sample([t for t in range(d.T) for _ in range(int(rem[t]))],rng.choice([30,100,200])): rem[t]-=1
    check=st.tenpai_checker(hand,rem)
    fast=check(hand)
    slow=False
    for w in range(d.T):
        if rem[w]<=0: continue
        for t in range(d.T):
            if hand[t]<=0 or t==w: continue
            hh=hand.astype(int).copy(); hh[t]-=1; hh[w]+=1
            if slow_sets({k:int(v) for k,v in enumerate(hh) if v}): slow=True;break
        if slow: break
    n+=1; ten+=slow
    if fast!=slow: bad+=1; print('MISMATCH tenpai',fast,slow)
print('tenpai trials',n,'tenpai(brute)',ten,'mismatch',bad)
