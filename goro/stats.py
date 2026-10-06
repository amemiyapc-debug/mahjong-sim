import random,collections,itertools,csv
from goro import *
words=[r for r in rows if r['kind']=='語']
jaws=[r for r in rows if r['kind']=='雀頭']
# 1. 全組
tot=0;lk=[];rej=[]
for a,b in itertools.combinations(words,2):
    tot+=1
    s=link(a,b)
    if s: lk.append((a,b,s))
    else:
        sa,sb=sorted([a['slot_no_eff'],b['slot_no_eff']])
        if sa!=sb and BASE.get((sa,sb),0)>=2: rej.append((a,b))
print('語どうしの組',tot,'つながる',len(lk),round(len(lk)/tot*100,1),'%')
q=collections.Counter('並' if s==3 else '良' if s==4 else '絶妙' for a,b,s in lk); print(q)
deg=collections.Counter()
for a,b,s in lk: deg[a['word']]+=1; deg[b['word']]+=1
iso=[w['word'] for w in words if deg[w['word']]==0]
print('つながる相手が0の語',len(iso),iso[:40])
import statistics
print('1語あたりの相手数 平均',round(statistics.mean(deg[w['word']] for w in words),1),'中央値',statistics.median(deg[w['word']] for w in words),'最大',max(deg.values()))
# by slot pair
sp=collections.Counter(); spt=collections.Counter()
for a,b in itertools.combinations(words,2):
    k=tuple(sorted([a['slot'],b['slot']],key=lambda x:['前置き','感情・誘い','部位','行為','音','反応','喘ぎ声'].index(x)))
    spt[k]+=1
for a,b,s in lk:
    k=tuple(sorted([a['slot'],b['slot']],key=lambda x:['前置き','感情・誘い','部位','行為','音','反応','喘ぎ声'].index(x)))
    sp[k]+=1
print('スロット組別 つながる割合')
for k in sorted(spt,key=lambda k:-sp[k]/spt[k])[:25]: print(' ',k,sp[k],'/',spt[k],round(sp[k]/spt[k]*100,1),'%')
# samples
random.seed(7)
hi=[x for x in lk if x[2]>=4]; mid=[x for x in lk if x[2]==3]
samples=[]
for lab,pool,n in [('絶妙・良(4以上)',hi,14),('並(3)',mid,14)]:
    for a,b,s in random.sample(pool,n): samples.append((lab,a['word'],b['word'],s,a['slot']+'→'+b['slot'] if a['slot_no_eff']<=b['slot_no_eff'] else b['slot']+'→'+a['slot']))
for a,b in random.sample(rej,10): samples.append(('つながらない(スロットは自然な組)',a['word'],b['word'],0,a['slot']+'/'+b['slot']))
with open('/mnt/user-data/outputs/link_samples_v1.csv','w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['区分','語A','語B','語呂度','スロット']);w.writerows(samples)
for s in samples: print(s)
# MC
random.seed(3)
N=60000;ms=collections.Counter();mults=[]
for _ in range(N):
    ws=random.sample(words,4); j=random.choice(jaws)
    nodes=ws+[j]; L=[]
    for a,b in itertools.combinations(nodes,2):
        s=link(a,b)
        if s: L.append((a['word'],b['word'],s))
    class _:pass
    m=merges(nodes,L); ms[m]+=1; mults.append(mult(m))
print('無作為の手(辞書から4語+雀頭を一様に抽選。牌の制約なし) 合体回数の分布')
for k in sorted(ms): print(' ',k,round(ms[k]/N*100,2),'%')
mults.sort(); print('倍率 平均',round(sum(mults)/N,2),'中央値',mults[N//2],'上位1%',mults[int(N*.99)],'最大',mults[-1])
