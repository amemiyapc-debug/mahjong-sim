"""試作HTMLへの追加(20261007-1345・1350): 自分で組んだ面子を組み替えない・飾りに0淫を出さない・アガリ演出の作り直し。
make_prototype.py から apply(s) で呼ばれる。適用済みなら飛ばす。"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHOWJS = open(os.path.join(HERE, "proto_show.js"), encoding="utf-8").read()

CHECKWIN = r'''let lastUserN=0;
function checkWin(){
  if(choice||skipMode)return;
  const all=flat();if(all.length!==14||won)return;
  const melds=items.filter(i=>i.k==="group"&&i.kind==="meld");
  const headG=items.find(i=>i.k==="group"&&i.kind==="head")||null;
  const labels=all.map(t=>t.label),oho=labels.filter(l=>l==="ぉ゛").length;
  const parts=allPartitions(DICT,labels,2000);
  if(!parts.length)return;
  const lv=lvOf(STG.stage),key=(n,l)=>n+"|"+l.slice().sort().join("");
  const info=parts.map(p=>{const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name),sc=scoreHand(ws,hd,oho,true);
    const gs=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lv,sc.yin);
    return {p,pts:gs.points,yin:sc.yin,mk:p.melds.map(m=>key(m.word.name,m.assigned)),hk:key(p.head.name,p.headAssigned)};});
  // 自分で組んだ面子・雀頭を、できるだけ多く残したまま、アガリ形にする。残りの牌は、解読点が最大になる分け方で自動で組む。だめなら、組み替える
  const subsets=[];for(let m=0;m<(1<<melds.length);m++)subsets.push(melds.filter((_,i)=>m&(1<<i)));
  subsets.sort((x,y)=>y.length-x.length);
  let hit=null;
  outer:for(const sub of subsets)for(const keepHead of(headG?[true,false]:[false])){
    const need=sub.map(g=>key(g.name,g.tiles.map(t=>t.label))),hk=keepHead?key(headG.name,headG.tiles.map(t=>t.label)):null;
    let best=null;
    for(const x of info){
      if(hk&&x.hk!==hk)continue;
      const pool=x.mk.slice();let okc=true;
      for(const k of need){const i=pool.indexOf(k);if(i<0){okc=false;break;}pool.splice(i,1);}
      if(!okc)continue;
      if(!best||x.pts>best.pts||(x.pts===best.pts&&x.yin>best.yin))best=x;
    }
    if(best){hit={sub,keepHead,x:best};break outer;}
  }
  if(!hit)return;
  const {sub,keepHead,x}=hit,p=x.p,g=[];
  sub.forEach(s=>g.push(s));
  const fixed=new Set();sub.forEach(s=>s.tiles.forEach(t=>fixed.add(t.id)));if(keepHead)headG.tiles.forEach(t=>fixed.add(t.id));
  const pool=all.filter(t=>!fixed.has(t.id)),take=lab=>pool.splice(pool.findIndex(t=>t.label===lab),1)[0];
  const left=x.mk.slice();sub.forEach(s=>{left.splice(left.indexOf(key(s.name,s.tiles.map(t=>t.label))),1);});
  p.melds.forEach(m=>{const k=key(m.word.name,m.assigned),i=left.indexOf(k);if(i<0)return;left.splice(i,1);
    g.push({k:"group",kind:"meld",tiles:m.assigned.map(take),text:readingOf(m.word,m.assigned),name:m.word.name});});
  if(keepHead)g.push(headG);else g.push({k:"group",kind:"head",tiles:p.headAssigned.map(take),text:p.head.name,name:p.head.name});
  const keptN=sub.length+(keepHead?1:0);lastUserN=melds.length+(headG?1:0);
  if(!practice&&STG.skips>0&&draws<LMAX){items=g;sel=[];tsumoId=null;choice=true;pendingWin={g,keptN};msg="";render();return;}   // 見送りを選べる
  finalizeWin(g,keptN);
}
'''

ITEMS = '''function itemsHTML(sc){
  const ys=sc.items.filter(x=>x.merge||!KZ.has(x.name)),zs=sc.items.filter(x=>!x.merge&&KZ.has(x.name));
  let s=ys.length?ys.map(x=>`<div class="sc">${x.merge?"合体 ":""}${x.name} <span class="han">+${x.han}淫</span>${x.merge?` <small>(${x.merge.join("+")}の合体)</small>`:""}</div>`).join(""):`<div class="sc">解読点に効く名前つき役はありません</div>`;
  if(zs.length)s+=`<div class="tags">${zs.map(x=>`<span class="ktag">${x.name}</span>`).join("")}</div>`;
  return s;
}
let inExplained=false;
function explainIn(y){if(y<=0)return false;let seen=inExplained;try{seen=seen||localStorage.getItem("hm-proto-in-explained")==="1";}catch(e){}if(seen)return false;inExplained=true;try{localStorage.setItem("hm-proto-in-explained","1");}catch(e){}return true;}
'''

CSS = '''#show{background:rgba(8,12,12,.96)}
.stone{position:relative;margin:6px 0;padding:14px 12px;min-height:96px;border:3px solid #3f5a56;border-radius:4px;background:#7d9d96;background-size:100% 100%;image-rendering:pixelated;box-shadow:inset 0 0 0 2px #b4d0c8,inset 0 0 28px rgba(30,55,52,.55)}
.stone .tw{text-align:left;font-weight:900;font-size:1.2rem;line-height:1.55;color:#f2c14e;text-shadow:0 1px 0 #3b2a05,0 -1px 0 #3b2a05,1px 0 0 #3b2a05,-1px 0 0 #3b2a05,0 0 8px rgba(255,214,102,.45);word-break:break-all;min-height:4.6em}
.stone .tw .ln{display:block}.stone .tw .ln.yk{font-size:1rem;margin-top:2px}
.stone.carved .tw{animation:carve 1.4s ease-out;text-shadow:0 1px 0 #3b2a05,0 -1px 0 #3b2a05,1px 0 0 #3b2a05,-1px 0 0 #3b2a05,0 0 10px #ffe08a,0 0 22px #ffbf3c}
@keyframes carve{0%{filter:brightness(2.4);letter-spacing:.12em}100%{filter:none;letter-spacing:0}}
.sh-graph{position:relative;height:150px;margin:6px 0;border-radius:10px;transition:box-shadow .3s,background .3s}
.sh-graph svg{position:absolute;inset:0;width:100%;height:100%}
.sh-graph .nd{position:absolute;transform:translate(-50%,-50%);padding:3px 8px;border-radius:8px;background:#1b1530;color:#efe6ff;border:2px solid #6b4fa0;font-weight:800;font-size:.85rem;white-space:nowrap;transition:box-shadow .3s,border-color .3s,background .3s}
.sh-graph .nd.on{border-color:var(--pc,#c77dff);box-shadow:0 0 12px var(--pc,#c77dff);background:#2a1b4d}
.sh-graph .nd.near{animation:near .3s}
@keyframes near{0%{transform:translate(-50%,-50%) scale(1)}50%{transform:translate(-50%,-50%) scale(1.25)}100%{transform:translate(-50%,-50%) scale(1)}}
.sh-mults{display:flex;justify-content:center;gap:6px;flex-wrap:wrap;min-height:34px}
.sh-mults .mc{padding:4px 10px;border-radius:10px;font-weight:900;color:#fff;background:var(--mc);box-shadow:0 0 14px var(--mc);animation:pop .35s}
.sh-total .reel{font-size:2.1rem;color:#ffd43b;text-shadow:0 0 12px #ff9f1a;font-variant-numeric:tabular-nums;max-width:100%;white-space:nowrap}
.tags{margin-top:3px}.ktag{display:inline-block;margin:2px 3px 0 0;padding:0 7px;border-radius:9px;background:#3a3550;color:#cfc8e8;font-size:.7rem}
'''

SHOWHTML = '''<div id="show" hidden><div class="sh-box" id="shbox">
 <div class="sh-title" id="sh-title"></div>
 <div class="stone" id="sh-stone"><div class="tw" id="sh-type"></div></div>
 <div class="sh-graph" id="sh-graph"><svg id="sh-svg" viewBox="0 0 300 150" preserveAspectRatio="none"></svg><div id="sh-nodes"></div></div>
 <div class="sh-mults" id="sh-mults"></div>
 <div class="sh-total" id="sh-total"></div>
 <div class="sh-btns" id="sh-ingo" hidden><button class="b" id="sh-star">☆ 傑作にする</button><button class="b" id="sh-copy">コピー</button></div>
 <div class="sh-btns"><button class="b" id="sh-skip">スキップ</button><button class="b" id="sh-close" hidden>とじる</button></div>
</div></div>
'''


def apply(s):
    if "/* dan6:c */" in s:
        return s

    def region(start, end, new):
        nonlocal s
        i0 = s.index(start); i1 = s.index(end, i0)
        s = s[:i0] + new + s[i1:]

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6c パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    region("function checkWin(){", "function finalizeWin(g,keptN){", CHECKWIN)
    sub1("kept:keptN,total:5}", "kept:keptN,total:5,user:lastUserN}")
    region("  if(won.kept===0&&best){", "  const melds0=items.filter", "")
    region("function itemsHTML(sc){", "function winHTML(){", ITEMS)
    sub1("ura,total,gs,lv:lvNow,", "ura,total,gs,lv:lvNow,firstIn:explainIn(total),")
    sub1("  s+=`<div style=\"margin-top:6px\">${itemsHTML(d.own.sc)}</div>`;",
         "  s+=`<div style=\"margin-top:6px\">${itemsHTML(d.own.sc)}</div>`;\n  if(d.firstIn)s+=`<div class=\"hint\" style=\"margin-top:4px\"><b>淫</b>とは: 名前つき役の数字です。句ボーナスに足されて、解読点が増えます(例: +3淫なら、句ボーナスが +3)。</div>`;")
    sub1("  if(won.kept<won.total)s+=`<div class=\"hint\" style=\"margin-top:6px\">手で組んだ形のうち ${won.kept}/${won.total} をそのまま使い、残りは自動で組みました。</div>`;",
         "  if(won.user>won.kept)s+=`<div class=\"hint rearr\" style=\"margin-top:6px\"><b>組み替えました</b>。自分で組んだ ${won.user} 個のうち ${won.kept} 個はそのまま使い、残りは、アガリになる形に組み替えました。</div>`;\n"
         "  else if(won.kept<5)s+=`<div class=\"hint\" style=\"margin-top:6px\">自分で組んだ ${won.kept} 個はそのまま。残りの牌は、解読点が最大になる分け方で自動で組みました。</div>`;")
    sub1("#shflash{position:fixed", CSS + "#shflash{position:fixed")
    region('<div id="show" hidden>', "<script>", SHOWHTML)
    region("async function playShow(){", '$$("sh-skip").onclick=', SHOWJS + "\n")
    sub1('$$("show").addEventListener("click",e=>{if(e.target.id==="show"&&showRunning){', '$$("show").addEventListener("click",e=>{if(showRunning&&!e.target.closest("button")){')
    s = s.replace("/* dan6:show */", "/* dan6:show *//* dan6:c */", 1)
    return s
