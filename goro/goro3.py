# 語呂度ルール v2(仮): v1 + 複合テーマ + 点の式(最低500点・上限なし)
import sys,itertools,collections,random
sys.path.insert(0,'/home/claude/mahjong-sim/goro')
import goro2 as g2
from goro2 import rows,words_by_name,link,_m,mult,collapse
FLOOR=500
def tags(r):
    t=set()
    n=r['word'].replace('【雀頭】','')
    t.add('部位:'+r['part']) if r['part'] and '|' not in r['part'] else None
    if r['sub']=='絶頂・結末' or r['sub']=='雀頭・快感': t.add('絶頂')
    if r['stem']=='くり': t.add('くり')
    if r['sub']=='キス・吸い': t.add('キス')
    if r['tone']=='ラブ': t.add('ラブ')
    if r['tone']=='SM' or r['sub'] in('命令・誘い','態度') and r['tone']=='SM': t.add('SM')
    if r['sub'] in('命令・誘い',): t.add('命令')
    if r['sub']=='態度': t.add('態度')
    if r['slot']=='音': t.add('水音')
    if 'ぬれ' in n: t.add('ぬれ')
    if '見せ' in n: t.add('見せ')
    return t
for r in rows: r['tags']=tags(r)
# 複合テーマ = (名前, タグA, タグB) : AとBの語を合わせて数える(AもBも1語以上必要)
COMP=[('くりでイく','くり','絶頂'),('まんでイく','部位:女性器','絶頂'),('ちんでイく','部位:男性器','絶頂'),
      ('胸でイく','部位:胸','絶頂'),('お尻でイく','部位:後ろ','絶頂'),('口でイく','部位:口','絶頂'),
      ('ラブキス','キス','ラブ'),('調教','SM','態度'),('命令調教','SM','命令'),('濡れ濡れ','ぬれ','水音'),('見せつけ','見せ','絶頂')]
CL={1:1,2:1,3:2,4:4,5:8}
def best_theme(nodes):
    best=(1,'なし',0)
    c1=collections.Counter(n['stem'] for n in nodes if n['stem']); c2=collections.Counter(n['theme'] for n in nodes if n['theme'])
    for nm,cnt in list(c1.items())+list(c2.items()):
        if CL.get(cnt,1)>best[0]: best=(CL.get(cnt,1),'単:'+nm,cnt)
    for nm,A,B in COMP:
        a=[n for n in nodes if A in n['tags']]; b=[n for n in nodes if B in n['tags']]
        if a and b:
            u={n['word'] for n in a}|{n['word'] for n in b}; k=len(u)
            if CL.get(k,1)>best[0]: best=(CL.get(k,1),'複合:'+nm,k)
    return best
def score(nodes):
    L=[]
    for a,b in itertools.combinations(nodes,2):
        s=link(a,b)
        if s: L.append((a['word'],b['word'],s))
    C=collapse(nodes,L)
    m=_m(nodes,L); ch=mult(m)
    bonus=1+sum(min(3,s-2) for a,b,s in C)         # 句ボーナス(並+1 良+2 絶妙+3)
    tm,tn,k=best_theme(nodes)
    return dict(links=len(C),merges=m,chain=ch,bonus=bonus,theme=tm,theme_name=tn,points=FLOOR*bonus*ch*tm)
def hand(ws,jaw): return [words_by_name[w] for w in ws]+[words_by_name['【雀頭】'+jaw]]
if __name__=='__main__':
    tests=[('良い例(流れ)',['ぬれまん','おめこ','ぱこぱこ','いくう'],'あん'),
           ('悪い例',['デカけつ','うんん','エロエロ♡','くり♡'],'あっ'),
           ('テーマ例2(くり→いく)',['デカまめ','エロくり','くり舐め','いくいく'],'いく'),
           ('感じるテーマ',['きく♡','いくう','ああん','んおお'],'おっ'),
           ('何もつながらない手(例)',['ちんぽ','ぬれくり','おしり','ぱちん'],'ああ')]
    for t,ws,j in tests:
        s=score(hand(ws,j)); print(t,{k:(round(v,1) if isinstance(v,float) else v) for k,v in s.items()})
    random.seed(11)
    words=[r for r in rows if r['kind']=='語']; jaws=[r for r in rows if r['kind']=='雀頭']
    N=30000;P=[];tn=collections.Counter()
    for _ in range(N):
        s=score(random.sample(words,4)+[random.choice(jaws)]); P.append(s['points']); tn[s['theme_name'].split(':')[0]]+=1
    P.sort()
    print('無作為の手 点: 最小',P[0],'中央値',round(P[N//2]),'平均',round(sum(P)/N),'上位10%',round(P[int(N*.9)]),'上位1%',round(P[int(N*.99)]),'最大',round(P[-1]))
    print('500点止まり',round(sum(1 for p in P if p==500)/N*100,1),'%  1万点以上',round(sum(1 for p in P if p>=1e4)/N*100,1),'%  100万点以上',round(sum(1 for p in P if p>=1e6)/N*100,2),'%')
    print('最良テーマの種類(無作為の手)',{k:round(v/N*100,1) for k,v in tn.items()})
