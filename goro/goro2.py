# 語呂度ルール v1(仮): v0 + テーマ(同語幹・同テーマ)の層
import sys,re,itertools,collections,random
sys.path.insert(0,'/home/claude/mahjong-sim/goro')
import goro as g
from goro import rows,words_by_name,link as link0,collapse,mult
MODS=['見せ','デカ','エロ','ぬれ','媚び','舐め','コキ','穴','♡','×2']
ALIAS={'まめ':'くり','おまめ':'くり','すじ':'くり'}
def stem(r):
    n=r['word'].replace('【雀頭】','').split('・')[0]
    for m in MODS: n=n.replace(m,'')
    n=n.replace('っ','つ')
    n=ALIAS.get(n,n)
    return n[:2] if len(n)>=2 else n
def theme(r):
    if r['part'] and '|' not in r['part']: return r['part']
    if r['slot_no_eff'] in (5,6): return '感じる'
    if r['tone'] in('SM','ラブ'): return r['tone']
    return ''
for r in rows: r['stem']=stem(r); r['theme']=theme(r)
def link(a,b):
    s=link0(a,b)
    same=a['slot_no_eff']==b['slot_no_eff']
    if a['tone'] and b['tone'] and {a['tone'],b['tone']}=={'ラブ','SM'}: return 0
    # 同じスロットの語は、同語幹(4)・同テーマ(3)ならつながる
    if same:
        if a['stem']==b['stem'] and a['stem']: s=max(s,4)
        elif a['theme'] and a['theme']==b['theme']: s=max(s,3)
    else:
        if a['stem']==b['stem'] and a['stem']: s=s+2 if s else 3
    return s
def hand(words,jaw):
    nodes=[words_by_name[w] for w in words]+[words_by_name['【雀頭】'+jaw]]
    L=[]
    for i,j in itertools.combinations(range(len(nodes)),2):
        s=link(nodes[i],nodes[j])
        if s: L.append((nodes[i]['word'],nodes[j]['word'],s))
    return nodes,L
def merges(nodes,L): return g.merges(nodes,L) if False else _m(nodes,L)
def _m(nodes,L):
    L=collapse(nodes,L)
    names=[n['word'] for n in nodes]; par={n:n for n in names}
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for a,b,s in L: par[f(a)]=f(b)
    comp=collections.defaultdict(lambda:[0,0])
    for n in names: comp[f(n)][0]+=1
    for a,b,s in L: comp[f(a)][1]+=1
    return sum(max(0,e-1) for n,e in comp.values())
CL={1:1,2:1,3:2,4:4,5:8}
def cluster(nodes):
    c1=collections.Counter(n['stem'] for n in nodes if n['stem'])
    c2=collections.Counter(n['theme'] for n in nodes if n['theme'])
    k=max([0]+list(c1.values())+list(c2.values()))
    return k,CL.get(k,1)
def total(words,jaw):
    nodes,L=hand(words,jaw); m=_m(nodes,L); k,cb=cluster(nodes)
    return len(L),m,mult(m),k,cb,mult(m)*cb
if __name__=='__main__':
    tests=[('良い例(流れ)',['ぬれまん','おめこ','ぱこぱこ','いくう'],'あん'),
           ('悪い例',['デカけつ','うんん','エロエロ♡','くり♡'],'あっ'),
           ('テーマ例2(くり+いく)',['デカまめ','エロくり','くり舐め','いくいく'],'いく'),
           ('テーマ例1に近い実在語(感じる)',['きく♡','いくう','ああん','んおお'],'おっ')]
    for t,ws,j in tests:
        l,m,mu,k,cb,tot=total(ws,j); print(t,'つながり',l,'合体',m,'倍率',round(mu,1),'テーマ揃い',k,'語 ×',cb,'→',round(tot,1))
    random.seed(3)
    words=[r for r in rows if r['kind']=='語']; jaws=[r for r in rows if r['kind']=='雀頭']
    N=40000; ts=[];cs=collections.Counter()
    for _ in range(N):
        ws=random.sample(words,4); j=random.choice(jaws)
        nodes=ws+[j]
        L=[]
        for a,b in itertools.combinations(nodes,2):
            s=link(a,b)
            if s: L.append((a['word'],b['word'],s))
        m=_m(nodes,L); k,cb=cluster(nodes); cs[k]+=1; ts.append(mult(m)*cb)
    ts.sort(); print('無作為の手 テーマ揃い数',{k:round(v/N*100,1) for k,v in sorted(cs.items())})
    print('倍率 平均',round(sum(ts)/N,1),'中央値',ts[N//2],'上位1%',ts[int(N*.99)],'最大',ts[-1])
