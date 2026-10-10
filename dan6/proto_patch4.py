"""試作HTMLへの追加(20261010-1925): 手牌固定の再修正(搭子も固定)。以降の作業(100語・アガリ演出・句バナー・エンディング・研究メモ)もここに足す。
make_prototype.py から apply(s) で呼ばれる。適用済み(/* dan6:d */)なら飛ばす。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 作業1: 手牌固定 ----
# 自分で組んだ面子・雀頭・搭子(2牌)を、できるだけ多く、その形のまま確定する。搭子は、和了牌で完成して面子になるか、そのまま雀頭になる。
# 自動で分けるのは、何も組んでいない牌だけ。組んだ形を壊さないとアガリにならない場合だけ組み替え、「組み替えました」と、どの語がどう変わったかを出す。
CHECKWIN = r'''let lastUserN=0,lastRearr="";
function groupDesc(g){return g.kind==="dazi"?"搭子「"+g.tiles.map(t=>t.label).join("+")+"」":(g.kind==="head"?"雀頭":"面子")+"「"+(g.text||g.name)+"」";}
function checkWin(){
  if(choice||skipMode)return;
  const all=flat();if(all.length!==14||won)return;
  const ugs=items.filter(i=>i.k==="group");      // 自分で組んだ形(面子・雀頭・搭子)
  const labels=all.map(t=>t.label),oho=labels.filter(l=>l==="ぉ゛").length;
  const parts=allPartitions(DICT,labels,2000);
  if(!parts.length)return;
  const lv=lvOf(STG.stage),key=(n,l)=>n+"|"+l.slice().sort().join("");
  const info=parts.map(p=>{const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name),sc=scoreHand(ws,hd,oho,true);
    const gs=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lv,sc.yin);
    return {p,pts:gs.points,yin:sc.yin,mk:p.melds.map(m=>key(m.word.name,m.assigned)),mm:p.melds.map(m=>m.assigned.map(nz)),hk:key(p.head.name,p.headAssigned),hm:p.headAssigned.map(nz).slice().sort().join("")};});
  // 形 g を、分け方 x のどの構成要素(面子の番号。雀頭は -1)に割り当てるか。1つの構成要素に割り当てられる形は1つだけ
  function assign(sub,x){
    const used=new Set(),res=[];
    const rec=i=>{
      if(i===sub.length)return true;const g=sub[i],opts=[];
      if(g.kind==="meld"){const k=key(g.name,g.tiles.map(t=>t.label));x.mk.forEach((m,j)=>{if(m===k)opts.push(j);});}
      else if(g.kind==="head"){if(x.hk===key(g.name,g.tiles.map(t=>t.label)))opts.push(-1);}
      else{const gk=g.tiles.map(t=>nz(t.label));
        x.mm.forEach((arr,j)=>{const rest=arr.slice();let okk=true;for(const l of gk){const q=rest.indexOf(l);if(q<0){okk=false;break;}rest.splice(q,1);}if(okk)opts.push(j);});   // 搭子 → 面子(和了牌で完成)
        if(x.hm===gk.slice().sort().join(""))opts.push(-1);}                                                                                   // 搭子 → そのまま雀頭
      for(const j of opts){if(used.has(j))continue;used.add(j);res[i]=j;if(rec(i+1))return true;used.delete(j);}
      return false;};
    return rec(0)?res.slice():null;}
  function build(sub,x,as){
    const p=x.p,fixed=new Set();sub.forEach(s=>s.tiles.forEach(t=>fixed.add(t.id)));
    const pool=all.filter(t=>!fixed.has(t.id));
    const take=lab=>{let i=pool.findIndex(t=>t.label===lab);if(i<0)i=pool.findIndex(t=>nz(t.label)===nz(lab));return i<0?null:pool.splice(i,1)[0];};
    const g=[];
    for(let j=0;j<p.melds.length;j++){const m=p.melds[j],gi=sub.findIndex((s,i)=>as[i]===j);
      if(gi>=0&&sub[gi].kind==="meld"){g.push(sub[gi]);continue;}
      let tiles;
      if(gi>=0){const s=sub[gi],rest=m.assigned.slice();s.tiles.forEach(t=>{const q=rest.findIndex(l=>nz(l)===nz(t.label));if(q>=0)rest.splice(q,1);});
        tiles=orderTiles(s.tiles.concat(rest.map(take)),m.assigned);}
      else tiles=m.assigned.map(take);
      if(tiles.some(t=>!t))return null;
      g.push({k:"group",kind:"meld",tiles,text:readingOf(m.word,m.assigned),name:m.word.name});}
    const hi=sub.findIndex((s,i)=>as[i]===-1);
    if(hi>=0)g.push(sub[hi].kind==="head"?sub[hi]:{k:"group",kind:"head",tiles:sub[hi].tiles,text:p.head.name,name:p.head.name});
    else{const tiles=p.headAssigned.map(take);if(tiles.some(t=>!t))return null;g.push({k:"group",kind:"head",tiles,text:p.head.name,name:p.head.name});}
    return g.reduce((n,x)=>n+x.tiles.length,0)===14?g:null;}
  // 残す形の数が多い順に試す(同じ数なら、組み方の違う全部の組を試す)。残す形が決まったら、解読点が最大になる分け方を使う
  const subsets=[];for(let m=0;m<(1<<ugs.length);m++){const sub=ugs.filter((_,i)=>m&(1<<i));subsets.push(sub);}
  subsets.sort((a,b)=>b.length-a.length);
  let hit=null;
  for(const sub of subsets){
    let best=null;
    for(const x of info){const as=assign(sub,x);if(!as)continue;if(!best||x.pts>best.x.pts||(x.pts===best.x.pts&&x.yin>best.x.yin))best={x,as};}
    if(best){const g=build(sub,best.x,best.as);if(g){hit={sub,g};break;}}
  }
  if(!hit)return;
  const {sub,g}=hit;const keptN=sub.length;lastUserN=ugs.length;
  const broken=ugs.filter(u=>!sub.includes(u)),made=g.filter(x=>!sub.includes(x));
  lastRearr=broken.length?broken.map(groupDesc).join("・")+" を解いて、"+made.map(x=>groupDesc(x)).join("・")+" に組み替えました":"";
  if(!practice&&STG.skips>0&&draws<LMAX){items=g;sel=[];tsumoId=null;choice=true;pendingWin={g,keptN};msg="";render();return;}   // 見送りを選べる
  finalizeWin(g,keptN);
}
'''


def apply(s):
    if "/* dan6:d */" in s:
        return s

    def region(start, end, new):
        nonlocal s
        i0 = s.index(start); i1 = s.index(end, i0)
        s = s[:i0] + new + s[i1:]

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6d パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    region("let lastUserN=0;", "function finalizeWin(g,keptN){", CHECKWIN)
    sub1("kept:keptN,total:5,user:lastUserN}", "kept:keptN,total:5,user:lastUserN,rearr:lastRearr}")
    sub1("<b>組み替えました</b>。自分で組んだ ${won.user} 個のうち ${won.kept} 個はそのまま使い、残りは、アガリになる形に組み替えました。", "<b>組み替えました</b>。自分で組んだ ${won.user} 個のうち ${won.kept} 個はそのまま。${won.rearr}。")
    s = s.replace("/* dan6:c */", "/* dan6:c *//* dan6:d */", 1)
    return s
