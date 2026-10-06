# 語呂度ルール v0 (仮) : 語と語がつながるか・つながりの強さ
import itertools,collections,random,csv,sys
sys.path.insert(0,'/home/claude/mahjong-sim/goro')
from tag import rows
BASE={(0,1):1,(0,2):3,(0,3):1,(1,2):2,(1,3):2,(1,5):1,(1,6):1,(2,3):3,(2,4):2,(2,5):2,(2,6):1,
      (3,4):2,(3,5):3,(3,6):1,(4,5):2,(4,6):1,(5,6):3}
SAME_SUB={('高まり','絶頂・結末'):2,('感情・状況','命令・誘い'):1,('行為','キス・吸い'):1}
THRESH=3
def parts(p): return set(p.split('|')) if p else set()
def pscore(a,b):
    A,B=parts(a),parts(b)
    if not A or not B: return 0
    if A&B: return 2
    hole={'穴'}; bodies={'女性器','後ろ','口'}
    if (A&hole and B&bodies) or (B&hole and A&bodies): return 1
    return None   # 部位が違う=つながらない
def link(a,b):
    """a,b: row dicts. 返り値: (score) or 0"""
    sa,sb=a['slot_no_eff'],b['slot_no_eff']
    if sa>sb: a,b=b,a; sa,sb=sb,sa
    if sa==sb:
        base=0
        sub=lambda r: r['sub'].replace('雀頭・','')
        base=SAME_SUB.get((sub(a),sub(b)),1)
    else: base=BASE.get((sa,sb),0)
    # 命令語は係り先のスロットに強くつながる(なめろ→部位、いくな→反応 など)
    for x,y in ((a,b),(b,a)):
        if x['target'] and x['slot_no_eff']<y['slot_no_eff'] and x['target']==y['slot']: base=max(base,3)
    if base==0: return 0
    p=pscore(a['part'],b['part'])
    if p is None: return 0
    ta,tb=a['tone'],b['tone']; t=0
    if ta and tb:
        if ta==tb: t=1
        elif {ta,tb}=={'ラブ','SM'}: return 0
    ra,rb=a['reading'],b['reading']
    ph=1 if (ra[-1:]==rb[:1] or rb[-1:]==ra[:1] or ra[:1]==rb[:1] or ra[-1:]==rb[-1:]) else 0
    sc=base+p+t+ph
    if sa==sb and p==0 and base<2: return 0   # 同じスロットは部位一致がないとつながらない
    return sc if sc>=THRESH else 0
def hand(words,jaw):
    nodes=[words_by_name[w] for w in words]+[words_by_name['【雀頭】'+jaw]]
    L=[]
    for i,j in itertools.combinations(range(len(nodes)),2):
        s=link(nodes[i],nodes[j])
        if s: L.append((nodes[i]['word'],nodes[j]['word'],s))
    return nodes,L
def collapse(nodes,L):
    # 同じスロットで結ばれた語は一つの塊。塊と外の語のつながりは1本に数える
    names=[n['word'] for n in nodes]; slot={n['word']:n['slot_no_eff'] for n in nodes}
    par={n:n for n in names}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    inner=[(a,b,s) for a,b,s in L if slot[a]==slot[b]]
    for a,b,s in inner: par[f(a)]=f(b)
    seen={}
    for a,b,s in L:
        if slot[a]==slot[b]: continue
        k=tuple(sorted((f(a),f(b))))
        seen[k]=max(seen.get(k,0),s)
    out=list(inner)+[(k[0],k[1],s) for k,s in seen.items()]
    return out
def merges(nodes,L):
    L=collapse(nodes,L)
    names=[n['word'] for n in nodes]; par={n:n for n in names}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for a,b,s in L: par[f(a)]=f(b)
    comp=collections.defaultdict(lambda:[0,0])
    for n in names: comp[f(n)][0]+=1
    for a,b,s in L: comp[f(a)][1]+=1
    m=sum(max(0,e-1) for n,e in comp.values())
    return m
def mult(m):
    x=1.0
    for k in range(1,m+1): x*=1+0.5*k
    return x
words_by_name={r['word']:r for r in rows}
if __name__=='__main__':
    for title,ws,jaw in [('良い例',['ぬれまん','おめこ','ぱこぱこ','いくう'],'あん'),
                         ('悪い例',['デカけつ','うんん','エロエロ♡','くり♡'],'あっ')]:
        nodes,L=hand(ws,jaw); m=merges(nodes,L)
        print(title,'つながり',len(L),'合体',m,'倍率',round(mult(m),1))
        for a,b,s in L: print('  ',a,'×',b,s)
