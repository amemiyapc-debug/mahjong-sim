import sys, random
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import simulator as sim
from collections import Counter
d=sim.data(); rng=random.Random(11)
names=[None]*d.T
for t,i in d.tid.items(): names[i]=t

def complete_slow(cnt, idx, heads):
    """cnt: {tile_id:count} 13枚が 4語(distinct)+喘ぎ牌1 に過不足なく分割できるか(総当たり)"""
    wt=[(i,Counter(d.W[i].nonzero()[0].repeat(d.W[i][d.W[i].nonzero()[0]]).tolist())) for i in idx]
    c=Counter({k:v for k,v in cnt.items() if v>0})
    def dfs(used,head):
        if not c: return head and len(used)==4
        t=min(c)
        if not head and t in heads:
            c[t]-=1
            if c[t]==0: del c[t]
            ok=dfs(used,True); c[t]=c.get(t,0)+1
            if ok: return True
        if len(used)<4:
            for i,wc in wt:
                if i in used: continue
                if all(c.get(k,0)>=v for k,v in wc.items()):
                    for k,v in wc.items():
                        c[k]-=v
                        if c[k]==0: del c[k]
                    ok=dfs(used|{i},head)
                    for k,v in wc.items(): c[k]=c.get(k,0)+v
                    if ok: return True
        return False
    return dfs(frozenset(),False)

mism=tot=ten=0
for trial in range(120):
    st=sim.Setup(1000+trial,14,(2,3))
    # 手牌: 完成形の1行を取り、1〜2枚を山の牌に差し替え → 13枚。さらに14枚目をツモ
    row=st.S[rng.randrange(len(st.S))].astype(np.int16)
    hand=row.copy()
    tiles=[t for t in range(d.T) for _ in range(hand[t])]
    for _ in range(rng.choice([1,2])):
        i=rng.randrange(13); tiles[i]=rng.choice(st.wall)
    hand=np.zeros(d.T,dtype=np.int16)
    for t in tiles: hand[t]+=1
    rem=st.total.astype(np.int16)-hand
    if (rem<0).any(): continue
    # 他に9枚ツモ済みとして山から除く
    for t in rng.sample([t for t in range(d.T) for _ in range(rem[t])],9): rem[t]-=1
    heads={t for t in d.head_idx if st.total[t]>0}
    S=st.S
    h13=hand.astype(np.int8)
    R=S[np.minimum(S,h13).sum(axis=1)>=12]
    fast=sim.is_tenpai(R,h13,rem)
    # 総当たり: ある山の牌wが残っていて、手牌の1枚tを抜いてwを足すと完成
    slow=False
    for w in range(d.T):
        if rem[w]<=0: continue
        for t in range(d.T):
            if hand[t]<=0 or t==w: continue
            h=hand.copy(); h[t]-=1; h[w]+=1
            if complete_slow({k:int(v) for k,v in enumerate(h) if v>0}, st.idx, heads): slow=True; break
        if slow: break
    tot+=1; ten+=slow
    if fast!=slow: mism+=1; print('MISMATCH trial',trial,fast,slow)
print('trials',tot,'tenpai(brute)',ten,'mismatch',mism)
