(function(){
"use strict";
// タップ操作・役ナビの画面(仕様: UI_SPEC_tap.md)。判定・採点は、すべて core.js(HMcore)を使う。
const HM=window.HMcore, G=HM.setup(DATA);
const S={L:12,N:5,initial:2000,mult:1.3,table:"m"};
const $=id=>document.getElementById(id);
let run=null, game=null, sel=[], hintOn=false, hintCache=null, infoWord=-1, idc=0, perf={render:0,hint:0};
const ALL_NAMES=[...new Set(G.rows.map(r=>r.name).concat(G.MERGES.map(m=>m.name)))];

function zload(){ try{ return JSON.parse(localStorage.getItem("hm-zukan-v1")||"{}"); }catch(e){ return {}; } }
function zsave(z){ try{ localStorage.setItem("hm-zukan-v1",JSON.stringify(z)); }catch(e){} }
let Z=zload(); Z.yaku=Z.yaku||{}; Z.teased=Z.teased||0;

const target=()=>Math.round(S.initial*Math.pow(S.mult,run.stage-1)/100)*100;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function wallCount(){ const c={}; game.wall.forEach(t=>c[t]=(c[t]||0)+1); return c; }

function tileHTML(t,cls,attrs){
  const d=HM.DISPLAY[t]; let k="";
  if(["見せ","デカ","エロ","ぬれ"].includes(t)) k="k-head"; else if(["穴","媚び","♡","舐め","コキ"].includes(t)) k="k-tail";
  let inner;
  if(t==="ぉ゛"){ k="k-oho"; inner='<span class="oho1">ぉ</span><span class="oho2">゛</span>'; }
  else if(d){ const sm=["ゃ","ゅ","っ","ぉ゛"].includes(d[1]); inner=`<span class="a">${esc(d[0])}</span><span class="b${sm?" sm":""}">${esc(d[1])}</span>`; }
  else inner=`<span class="one">${esc(t)}</span>`;
  return `<button class="tile ${k} ${cls||""}" ${attrs||""} aria-label="${esc(t)}">${inner}</button>`;
}

// ---- 手牌の状態 ----
// game.tiles: [{id,t,g}] 画面の並び順。g=グループ番号(0=組んでいない)。game.groups[g]={id,kind:"meld"|"head"|"tatsu",word,head,cands}
const strs=()=>game.tiles.map(x=>x.t);
const ungrp=()=>game.tiles.filter(x=>!x.g);
const groupsOf=kind=>Object.values(game.groups).filter(g=>g.kind===kind);
const meldWords=()=>groupsOf("meld").map(g=>g.word);
const headGroup=()=>groupsOf("head")[0]||null;
const headKey=h=>G.H[h].tiles.map(t=>G.norm(t)).sort().join("|");
const tileObj=id=>game.tiles.find(x=>x.id===id);
function setMsg(t){ const m=$("msg"); if(m) m.textContent=t||""; }
function changed(){ hintCache=null; infoWord=-1; render(); }

function makeGroup(ids,kind,info){
  const objs=ids.map(tileObj);
  const raw=kind==="meld"?G.W[info.word].tiles:kind==="head"?G.H[info.head].tiles:null;
  let ordered;
  if(raw){ const pool=objs.slice(); ordered=G.allocTiles(raw,objs.map(o=>o.t)).map(t=>{ const k=pool.findIndex(o=>o.t===t); return pool.splice(k,1)[0]; }); }
  else ordered=objs.slice().sort((a,b)=>game.tiles.indexOf(a)-game.tiles.indexOf(b));
  const pos=Math.min(...objs.map(o=>game.tiles.indexOf(o)));
  const rest=game.tiles.filter(x=>!objs.includes(x)); rest.splice(pos,0,...ordered); game.tiles=rest;
  const gid=++game.gseq; ordered.forEach(o=>o.g=gid); game.groups[gid]=Object.assign({id:gid,kind},info); return gid;
}
function ungroup(gid){ game.tiles.forEach(x=>{ if(x.g===gid) x.g=0; }); delete game.groups[gid]; }
function ungroupAll(){ game.tiles.forEach(x=>x.g=0); game.groups={}; }
function groupLabel(g){
  const T=game.tiles.filter(x=>x.g===g.id).map(x=>x.t);
  if(g.kind==="tatsu") return "搭子";
  if(g.kind==="meld"){ const w=G.W[g.word]; return G.labelOf({name:w.word,tiles:w.tiles},T); }
  const h=G.H[g.head]; return G.labelOf({name:h.head,tiles:h.tiles},T);
}
function organize(){
  const T=game.tiles, byG=g=>T.filter(x=>x.g===g.id);
  let out=[]; groupsOf("meld").forEach(g=>out=out.concat(byG(g))); groupsOf("head").forEach(g=>out=out.concat(byG(g))); groupsOf("tatsu").forEach(g=>out=out.concat(byG(g)));
  const drawn=T.find(x=>x.id===game.drawnId&&!x.g); const rest=T.filter(x=>!x.g&&x!==drawn);
  const order=G.sortHand(rest.map(x=>x.t)), pool=rest.slice(), sorted=order.map(t=>pool.splice(pool.findIndex(o=>o.t===t),1)[0]);
  game.tiles=out.concat(sorted,drawn?[drawn]:[]); sel=[]; changed();
}

// ---- 流れ ----
function newRun(){ run={stage:1,lives:3,stageScore:0,gamesUsed:0,streak:0,total:0,wins:0,teased:0,seen:{},bestHan:0}; newGame(); }
function newGame(){
  const deck=HM.shuffle(G.buildDeck());
  const first=G.sortHand(deck.splice(0,13));
  game={wall:deck,tiles:first.map(t=>({id:++idc,t,g:0})),drawnId:-1,draws:0,discards:[],over:false,groups:{},gseq:0,win:false};
  sel=[]; hintCache=null; infoWord=-1; setMsg(""); drawTile(); render();
}
function drawTile(){   // 自動ツモ: 配牌のあとと、捨てた直後
  const t=game.wall.pop(); game.draws++; const o={id:++idc,t,g:0}; game.tiles.push(o); game.drawnId=o.id; game.win=G.isWin14(strs()); hintCache=null;
}
function doDiscard(){
  if(!game||game.over||sel.length!==1||game.tiles.length!==14) return;
  const o=tileObj(sel[0]); if(!o||o.g) return;
  game.tiles=game.tiles.filter(x=>x!==o); game.discards.push(o.t); sel=[]; infoWord=-1; setMsg("");
  if(game.draws>=S.L) endGameNoWin(); else { drawTile(); render(); }
}
function tryMeld(ids){
  const m=G.matchWords(ids.map(id=>tileObj(id).t));
  if(!m.length){ setMsg("語になりません"); render(); return; }
  const w=m[0].w;
  if(meldWords().includes(w)){ setMsg("「"+G.W[w].word.split("・")[0]+"」はすでに組んでいます(同じ語は1手牌に1回だけ)"); render(); return; }
  setMsg(""); makeGroup(ids,"meld",{word:w}); changed();
}
function onTile(id){
  if(!game||game.over) return; const o=tileObj(id); if(!o) return;
  if(o.g){ ungroup(o.g); sel=[]; setMsg(""); changed(); return; }
  const k=sel.indexOf(id);
  if(k>=0){ sel.splice(k,1); render(); return; }
  if(sel.length>=2){ const ids=sel.concat([id]); sel=[]; tryMeld(ids); return; }
  sel.push(id); setMsg(""); render();
}
function makeHeadFromSel(){
  if(sel.length!==2||headGroup()) return; const hs=G.matchHeads(sel.map(id=>tileObj(id).t)); if(!hs.length) return;
  const ids=sel.slice(); sel=[]; makeGroup(ids,"head",{head:hs[0]}); changed();
}
function makeTatsuFromSel(){
  if(sel.length!==2) return; const ts=G.matchTatsu(sel.map(id=>tileObj(id).t)); if(!ts.length) return;
  const ids=sel.slice(); sel=[]; makeGroup(ids,"tatsu",{cands:ts}); changed();
}
function completeTatsu(gid,xid,w){
  const g=game.groups[gid]; if(!g) return; if(meldWords().includes(w)){ setMsg("その語はすでに組んでいます"); render(); return; }
  const ids=game.tiles.filter(x=>x.g===gid).map(x=>x.id).concat([xid]); ungroup(gid); sel=[]; makeGroup(ids,"meld",{word:w}); setMsg(""); changed();
}
function buildWordFromHint(w){   // 面子の候補: 組んでいない牌から、その語を組む
  const U=ungrp(), idxs=G.idxsForWord(G.W[w].word,U.map(x=>x.t)); if(idxs.length!==3) return;
  sel=[]; makeGroup(idxs.map(i=>U[i].id),"meld",{word:w}); setMsg(""); changed();
}
function buildHeadFromHint(h){
  if(headGroup()) return; const U=ungrp(), idxs=G.idxsForHead(G.H[h].head,U.map(x=>x.t)); if(idxs.length!==2) return;
  sel=[]; makeGroup(idxs.map(i=>U[i].id),"head",{head:h}); setMsg(""); changed();
}
function buildTatsuFromHint(w){
  const U=ungrp(), idxs=G.idxsForWord(G.W[w].word,U.map(x=>x.t)); if(idxs.length!==2) return;
  const ts=G.matchTatsu(idxs.map(i=>U[i].t)); if(!ts.length) return;
  sel=[]; makeGroup(idxs.map(i=>U[i].id),"tatsu",{cands:ts}); setMsg(""); changed();
}

// ---- アガリ ----
function doWin(){
  if(!game||!game.win||game.over) return;
  game.over=true; setMsg("");
  showModal("アガリ!","<p>採点中…</p>",[]);
  setTimeout(finishWin,0);
}
function finishWin(){
  const t0=performance.now(), hand=strs();
  const parts=G.allPartitions(hand,500), sc=parts.map(p=>G.scorePartition(hand,p));
  const key=r=>r.han*1000+r.yaku.length+r.merges.length;
  let bi=0; sc.forEach((r,i)=>{ if(key(r)>key(sc[bi])) bi=i; });
  const best=parts[bi], w=sc[bi];
  // 画面の組み: 手で組んだ面子・雀頭を、できるだけ多く残す(同じ数なら、翻の高いほう)
  const M=meldWords(), hg=headGroup(), hk=hg?headKey(hg.head):null; let si=bi, sn=-1;
  parts.forEach((p,i)=>{ const n=p.four.filter(x=>M.includes(x)).length+((hg&&headKey(p.head)===hk)?1:0);
    if(n>sn||(n===sn&&key(sc[i])>key(sc[si]))){ sn=n; si=i; } });
  const scr=parts[si], same=p=>p.four.slice().sort().join()===best.four.slice().sort().join()&&headKey(p.head)===headKey(best.head), differs=!same(scr);
  const pot=Math.min(run.streak,5)*500, base=HM.pointsFor(w.han,S.table), pts=base+pot;
  run.stageScore+=pts; run.total+=pts; run.wins++; run.gamesUsed++; run.streak=0; run.bestHan=Math.max(run.bestHan,w.han);
  const names=w.yaku.map(y=>y.name).concat(w.merges.map(m=>m.name));
  names.forEach(n=>{ run.seen[n]=(run.seen[n]||0)+1; Z.yaku[n]=(Z.yaku[n]||0)+1; }); zsave(Z);
  const layout=(p)=>{   // 4語+雀頭の並び(手で組んだ語を先に)
    const avail=hand.slice(), items=p.four.map(x=>({kind:"meld",word:x})).concat([{kind:"head",head:p.head}]);
    items.sort((a,b)=>(M.includes(b.word)?1:0)-(M.includes(a.word)?1:0)||(a.kind==="head")-(b.kind==="head"));
    return items.map(it=>{ const raw=it.kind==="meld"?G.W[it.word].tiles:G.H[it.head].tiles, nm=it.kind==="meld"?G.W[it.word].word:G.H[it.head].head;
      const al=G.allocTiles(raw,avail); al.forEach(t=>{ const k=avail.indexOf(t); if(k>=0) avail.splice(k,1); });
      return `<div class="grp ${it.kind}">${al.map(t=>tileHTML(t,"mini","tabindex=\"-1\"")).join("")}<span class="gl">${esc(G.labelOf({name:nm,tiles:raw},al))}</span></div>`; }).join("");
  };
  let body=`<div class="rlay">${layout(scr)}</div><p><small>手で組んだ形のうち <b>${sn}/5</b> を使った</small></p>`;
  if(differs) body+=`<p><small>得点は、最も翻が高い分け方で数えました: ${best.four.map(x=>esc(G.W[x].word.split("・")[0])).join("・")}+雀頭 ${esc(G.H[best.head].head)}</small></p>`;
  body+=`<div class="yk"><span>形が成立</span><span>1翻</span></div>`;
  w.yaku.forEach(y=>{ body+=`<div class="yk"><span>${esc(y.name)}</span><span>${y.han}翻</span></div>`; });
  w.merges.forEach(m=>{ body+=`<div class="yk"><span><b>${esc(m.name)}</b>(合体: ${m.sources.map(esc).join("+")})</span><span>${m.han}翻</span></div>`; });
  body+=`<p class="big">${w.han}翻 = ${base.toLocaleString()}点`+(pot?` + 積み${pot.toLocaleString()}点`:"")+`</p><p><small>全部で ${parts.length}通りの分け方を採点しました</small></p>`;
  if(hintOn){
    const near=G.nearSwap(best.four,hand,G.headObj(G.H[best.head]),5);
    body+=`<div class="sec infoBox"><b>惜しかった役(4語のうち1語を替えれば成立)</b>${near.map(n=>`<div><span class="yk2">${esc(n.name)} ${n.han}翻</span> <small>${esc(n.from.split("・")[0])} → ${esc(n.to.split("・")[0])}</small></div>`).join("")||"<small>なし</small>"}</div>`;
  }
  perf.win=performance.now()-t0;
  showModal("アガリ!",body,[{label:"次へ",fn:afterGame}]);
}
function endGameNoWin(){
  game.over=true; const waits=G.tenpaiWaits(strs(),wallCount());
  let near="";
  if(hintOn){
    const M=meldWords(); const an=G.analyze(strs(),wallCount(),{}); const four=[...new Set(M.concat(an.blocks.filter(b=>b.complete).map(b=>G.idx[b.word])))].slice(0,4);
    const hg=headGroup(), ho=hg?G.headObj(G.H[hg.head]):null, list=G.nearAdd(four,ho,5);
    near=`<div class="sec infoBox"><b>惜しかった役(あと1語で成立)</b>${list.map(n=>`<div><span class="yk2">${esc(n.name)} ${n.han}翻</span> <small>${esc(n.by.split("・")[0])}</small></div>`).join("")||"<small>なし</small>"}</div>`;
  }
  if(waits.length){
    run.streak++; let extra="";
    if(run.streak===3){ run.teased++; Z.teased++; zsave(Z); extra=`<p class="big">焦らしプレイ達成!(3連続)</p>`; }
    const pot=Math.min(run.streak,5)*500;
    showModal("テンパイ流局",`<p>待ち: ${waits.map(esc).join("・")}</p>${extra}<p>ゲームは消費しません。連続${run.streak}回、積み点 ${pot.toLocaleString()}点(次のアガリで加算)</p>${near}`,[{label:"次のゲームへ",fn:afterGame}]);
  } else {
    run.gamesUsed++; run.streak=0;
    showModal("ノーテン",`<p>ツモを使い切りました。ゲームを1つ消費します。積み点はリセットされます。</p>${near}`,[{label:"次へ",fn:afterGame}]);
  }
}
function afterGame(){
  hideModal();
  if(run.stageScore>=target()){
    const k=run.stage; run.stage++; run.stageScore=0; run.gamesUsed=0; run.streak=0;
    showModal(`ステージ${k} クリア!`,`<p>次のステージ${run.stage}の目標は ${target().toLocaleString()}点です。</p>`,[{label:"続ける",fn:()=>{hideModal();newGame();}}]); return;
  }
  if(run.gamesUsed>=S.N){
    run.lives--; run.stageScore=0; run.gamesUsed=0; run.streak=0;
    if(run.lives<=0){ gameOver(); return; }
    showModal("ステージ失敗",`<p>目標点に届きませんでした。ライフが1つ減ります(残り${run.lives})。同じステージをやり直します。</p>`,[{label:"やり直す",fn:()=>{hideModal();newGame();}}]); return;
  }
  newGame();
}
function gameOver(){
  const names=Object.keys(run.seen);
  let body=`<p class="big">到達ステージ ${run.stage}</p><div class="yk"><span>合計得点</span><span>${run.total.toLocaleString()}点</span></div>
  <div class="yk"><span>アガリ回数</span><span>${run.wins}回</span></div><div class="yk"><span>最高の翻</span><span>${run.bestHan}翻</span></div>
  <div class="yk"><span>焦らしプレイ(3連続テンパイ)</span><span>${run.teased}回</span></div>`;
  body+=`<p class="label">成立した役(${names.length}種)</p><div class="chips">${names.map(n=>`<span class="chip">${esc(n)}×${run.seen[n]}</span>`).join("")||"なし"}</div>`;
  showModal("ゲームオーバー",body,[{label:"もう一度",fn:()=>{hideModal();newRun();}}]);
}
function showModal(title,body,btns){
  $("card").innerHTML=`<h2>${esc(title)}</h2>${body}<div class="btns">${btns.map((b,i)=>`<button class="btn primary" data-i="${i}">${esc(b.label)}</button>`).join("")}</div>`;
  $("modal").hidden=false;
  $("card").querySelectorAll("button[data-i]").forEach(el=>el.addEventListener("click",()=>btns[+el.dataset.i].fn()));
}
function hideModal(){ $("modal").hidden=true; }

// ---- ヒント(ONのときだけ。組みが変わったときだけ計算する) ----
function hintKey(){
  return strs().join("")+"|"+game.tiles.map(x=>x.id+":"+x.g).join(",")+"|"+Object.values(game.groups).map(g=>g.kind+(g.word??g.head??"")).join(",");
}
function computeHints(){
  const key=hintKey(); if(hintCache&&hintCache.key===key) return hintCache.v;
  const t0=performance.now(), wc=wallCount(), U=ungrp(), Us=U.map(x=>x.t), mw=meldWords(), hg=headGroup(), ho=hg?G.headObj(G.H[hg.head]):null;
  const st=G.wordStatus2(Us,wc), built=new Set(mw);
  // 面子の候補(組んでいない牌だけで作れる語): 新しく成立する役の翻が高い順
  const cands=st.done.map(n=>G.idx[n]).filter(w=>!built.has(w)).map(w=>({w,gain:G.gainBy(mw,ho,w)}));
  cands.sort((a,b)=>((b.gain[0]?b.gain[0].han:-1)-(a.gain[0]?a.gain[0].han:-1))||(a.w-b.w));
  const heads=hg?[]:G.headStatus(Us,wc).done.map(n=>G.hidx[n]);
  const tatsu=st.one.filter(o=>!built.has(G.idx[o.word])).slice(0,16);
  // 完成牌: 組んだ搭子 + 組んでいない牌1枚で、語になる
  const comps=[]; groupsOf("tatsu").forEach(g=>{ const tt=game.tiles.filter(x=>x.g===g.id).map(x=>x.t);
    U.forEach(x=>{ G.matchWords(tt.concat([x.t])).forEach(m=>{ if(!built.has(m.w)) comps.push({gid:g.id,tile:x,w:m.w}); }); }); });
  const now=G.partialYaku(mw,ho);
  // 次の一手: 組める語・完成牌で、新しく成立する役(翻の高い順、上位3)
  const next={}; const addNext=(w,gain)=>gain.forEach(y=>{ if(!(y.name in next)||next[y.name].han<y.han) next[y.name]={name:y.name,han:y.han,via:G.W[w].word}; });
  cands.forEach(c=>addNext(c.w,c.gain)); comps.forEach(c=>addNext(c.w,G.gainBy(mw,ho,c.w)));
  const nextList=Object.values(next).sort((a,b)=>b.han-a.han).slice(0,3);
  const v={cands,heads,tatsu,comps,now,nextList}; hintCache={key,v}; perf.hint=performance.now()-t0; return v;
}
function infoHTML(w){
  const mw=meldWords(), hg=headGroup(), ho=hg?G.headObj(G.H[hg.head]):null;
  const g1=G.gainBy(mw,ho,w), n1=new Set(g1.map(y=>y.name)), g2=G.gainByNext(mw,ho,w).filter(y=>!n1.has(y.name)).slice(0,8), n2=new Set(g2.map(y=>y.name));
  const rel=G.relatedYaku(w).filter(n=>!n1.has(n)&&!n2.has(n)).slice(0,14);
  return `<div class="infoBox" id="infoBox"><b>「${esc(G.W[w].word.split("・")[0])}」が関わる役</b>
   <div>組むと成立: ${g1.map(y=>`<span class="yk2 new">${esc(y.name)} ${y.han}翻</span>`).join("")||"<small>なし</small>"}</div>
   <div>組んだあと、あと1語で成立: ${g2.map(y=>`<span class="yk2">${esc(y.name)} ${y.han}翻<small>(${esc(y.by.split("・")[0])})</small></span>`).join("")||"<small>なし</small>"}</div>
   <div>ほかに関わる役: ${rel.map(n=>`<span class="yk2">${esc(n)}</span>`).join("")||"<small>なし</small>"}</div></div>`;
}
const CAND_TOP=8;
function hintHTML(){
  const hv=computeHints(); const candBtn=c=>{ const nm=G.W[c.w].word.split("・")[0]; return `<span class="cand"><button class="btn" data-act="meld" data-w="${c.w}">${esc(nm)}</button>${c.gain[0]?`<span class="nav">▸${esc(c.gain[0].name)}</span>`:""}<button class="info" data-act="info" data-w="${c.w}" aria-label="${esc(nm)}が関わる役">ⓘ</button></span>`; };
  let h=`<div class="sec" id="navSec"><b>役ナビ</b><div>いま成立: ${hv.now.map(y=>`<span class="yk2">${esc(y.name)} ${y.han}翻</span>`).join("")||"<small>なし</small>"}</div>
    <div>次の一手: ${hv.nextList.map(y=>`<span class="yk2 new">${esc(y.name)} ${y.han}翻<small>←${esc(y.via.split("・")[0])}</small></span>`).join("")||"<small>なし</small>"}</div></div>`;
  h+=`<div class="sec" id="candSec"><b>面子になる語(タップで組む。▸=組むと成立する役)</b>${hv.cands.slice(0,CAND_TOP).map(candBtn).join("")||"<small>なし</small>"}`+
    (hv.cands.length>CAND_TOP?`<details><summary>ほか ${hv.cands.length-CAND_TOP}語</summary>${hv.cands.slice(CAND_TOP).map(candBtn).join("")}</details>`:"")+
    (infoWord>=0?infoHTML(infoWord):"")+`</div>`;
  h+=`<div class="sec"><b>雀頭になる2枚</b>${hv.heads.map(x=>`<span class="cand"><button class="btn" data-act="head" data-h="${x}">${esc(G.H[x].head)}</button></span>`).join("")||"<small>"+(headGroup()?"組み済み":"なし")+"</small>"}</div>`;
  h+=`<div class="sec"><b>搭子(あと1枚で語。山の残りが多い順・上位16)</b>${hv.tatsu.map(o=>`<span class="cand"><button class="btn" data-act="tatsu" data-w="${G.idx[o.word]}">${esc(o.word.split("・")[0])}←${esc(o.need)}(${o.left})</button></span>`).join("")||"<small>なし</small>"}</div>`;
  return h;
}

// ---- 表示 ----
function render(){
  if(!run||!game) return; const t0=performance.now();
  const tg=target(), pct=Math.min(100,Math.round(run.stageScore/tg*100)), pot=Math.min(run.streak,5)*500;
  $("status").innerHTML=
   `<div><b>ステージ ${run.stage}</b></div><div>ライフ <b>${"♥".repeat(run.lives)}${"♡".repeat(Math.max(0,3-run.lives))}</b></div><div>ゲーム <b>${Math.min(run.gamesUsed+1,S.N)}/${S.N}</b></div>
    <div class="wide">目標 <b>${tg.toLocaleString()}点</b> / 現在 <b>${run.stageScore.toLocaleString()}点</b><div class="bar"><i style="width:${pct}%"></i></div></div>
    <div>ツモ <b>${game.draws}/${S.L}</b></div><div>山 <b>${game.wall.length}</b>枚</div><div>積み <b>${run.streak}連 ${pot.toLocaleString()}点</b></div>`;
  const hv=hintOn&&!game.over?computeHints():null, compIds=new Set(hv?hv.comps.map(c=>c.tile.id):[]);
  // 手牌
  let h="", T=game.tiles, i=0;
  while(i<T.length){
    const o=T[i];
    if(o.g){ let j=i; while(j<T.length&&T[j].g===o.g) j++; const g=game.groups[o.g], lab=groupLabel(g);
      h+=`<div class="grp ${g.kind}" data-gid="${g.id}" title="${esc(g.kind==="meld"?G.W[g.word].word:g.kind==="head"?G.H[g.head].head:"搭子")}">${T.slice(i,j).map(x=>tileHTML(x.t,"",`data-id="${x.id}"`)).join("")}<span class="gl">${esc(lab)}</span></div>`; i=j; }
    else { const cls=[]; if(sel.includes(o.id)) cls.push("sel"); if(compIds.has(o.id)) cls.push("comp"); if(o.id===game.drawnId&&i===T.length-1) cls.push("drawn");
      h+=tileHTML(o.t,cls.join(" "),`data-id="${o.id}"`); i++; }
  }
  $("hand").innerHTML=h;
  $("compBar").innerHTML=hv&&hv.comps.length?`<span>この牌で面子にできます →</span>`+hv.comps.map(c=>`<button class="btn" data-act="comp" data-gid="${c.gid}" data-id="${c.tile.id}" data-w="${c.w}">${esc(c.tile.t)} で『${esc(G.W[c.w].word.split("・")[0])}』</button>`).join(""):"";
  $("bDiscard").disabled=sel.length!==1||game.tiles.length!==14||game.over; $("bWin").disabled=!game.win||game.over;
  $("bSort").disabled=game.over; $("bUngroup").disabled=game.over||!Object.keys(game.groups).length;
  const hb=$("bHint"); hb.textContent="ヒント: "+(hintOn?"オン":"オフ"); hb.setAttribute("aria-pressed",hintOn?"true":"false");
  // 選択中の操作
  let sb="";
  if(sel.length===1) sb=`<small>「${esc(tileObj(sel[0]).t)}」を選んでいます。あと2枚で語。1枚だけなら、「この牌を捨てる」(14枚のとき)。</small>`;
  else if(sel.length===2){
    const tt=sel.map(id=>tileObj(id).t), hs=G.matchHeads(tt), ts=G.matchTatsu(tt), wc=wallCount();
    const left=m=>(wc[m]||0)+G.FLEX.reduce((a,f)=>a+(f.base===m?(wc[f.tile]||0):0),0);
    const waits=[...new Set(ts.map(x=>x.missing))].slice(0,5).map(m=>esc(m)+"(山"+left(m)+")").join("・");
    sb=`<span>${esc(tt.join("・"))}</span><button class="btn" data-act="mkhead" ${hs.length&&!headGroup()?"":"disabled"}>雀頭にする</button><button class="btn" data-act="mktatsu" ${ts.length?"":"disabled"}>搭子にする</button>`+
       (ts.length?`<small>待ち: ${waits}</small>`:"")+`<small>(3枚目をタップすると、語を作ります)</small>`;
  }
  $("selBar").innerHTML=sb;
  $("hintPanel").innerHTML=hv?hintHTML():"";
  $("discards").innerHTML=game.discards.map(t=>tileHTML(t,"mini")).join("")||"<small>まだありません</small>";
  const names=Object.keys(Z.yaku);
  $("zukan").innerHTML=`<p>成立した役 <b>${names.length}</b> / ${ALL_NAMES.length}種(合体を含む) 　焦らしプレイ ${Z.teased}回</p><div class="chips">${ALL_NAMES.map(n=>`<span class="chip${Z.yaku[n]?" done":""}">${Z.yaku[n]?esc(n):"？？？"}</span>`).join("")}</div>`;
  perf.render=performance.now()-t0;
}

// ---- 操作 ----
$("hand").addEventListener("click",e=>{ const b=e.target.closest(".tile"); if(!b||!b.dataset.id) return; onTile(+b.dataset.id); });
document.addEventListener("click",e=>{
  if(!game||game.over) return;
  const el=e.target.closest("[data-act]"); if(!el) return; const act=el.dataset.act, t0=performance.now();
  if(act==="meld"){ buildWordFromHint(+el.dataset.w); }
  else if(act==="head"){ buildHeadFromHint(+el.dataset.h); }
  else if(act==="tatsu"){ buildTatsuFromHint(+el.dataset.w); }
  else if(act==="comp"){ completeTatsu(+el.dataset.gid,+el.dataset.id,+el.dataset.w); }
  else if(act==="info"){ infoWord=(infoWord===+el.dataset.w)?-1:+el.dataset.w; render(); }
  else if(act==="mkhead"){ makeHeadFromSel(); }
  else if(act==="mktatsu"){ makeTatsuFromSel(); }
  perf.op=performance.now()-t0;
});
$("bDiscard").addEventListener("click",doDiscard);
$("bWin").addEventListener("click",doWin);
$("bSort").addEventListener("click",()=>{ if(game&&!game.over) organize(); });
$("bUngroup").addEventListener("click",()=>{ if(game&&!game.over){ ungroupAll(); sel=[]; setMsg(""); changed(); } });
$("bHint").addEventListener("click",()=>{ hintOn=!hintOn; hintCache=null; infoWord=-1; render(); });
function loadSettings(){ $("sL").value=S.L; $("sN").value=S.N; $("sI").value=S.initial; $("sM").value=S.mult; $("sT").value=S.table; }
$("bApply").addEventListener("click",()=>{
  S.L=Math.max(6,Math.min(20,+$("sL").value||12)); S.N=Math.max(2,Math.min(10,+$("sN").value||5));
  S.initial=Math.max(500,+$("sI").value||2000); S.mult=Math.max(1,+$("sM").value||1.3); S.table=$("sT").value; newRun();
});
loadSettings();
// テスト用の入口(画面の操作と同じ関数を使う)
function setHand(tiles,drawn){   // tiles=手牌(drawn があれば、最後に足す)
  const list=tiles.slice(); if(drawn) list.push(drawn);
  game.tiles=list.map(t=>({id:++idc,t,g:0})); game.groups={}; game.gseq=0; game.drawnId=drawn?game.tiles[game.tiles.length-1].id:-1; sel=[]; infoWord=-1; hintCache=null;
  game.win=list.length===14&&G.isWin14(list); render();
}
window.__HM={S,G,render,setHand,onTile,makeGroup,ungroup,organize,doDiscard,doWin,drawTile,
  get run(){return run;},get game(){return game;},get sel(){return sel;},set hint(v){hintOn=v;hintCache=null;render();},get hintOn(){return hintOn;},get perf(){return perf;},
  strs,tileObj,computeHints,hintKey,endGameNoWin,newGame,newRun};
showModal("ひらがな麻雀(仮) テストプレイ版",
 `<p>4つの語(各3牌)と、雀頭(2牌の語。喘ぎ声や略称)をそろえた14牌でアガるゲームです。</p>
  <ul><li>ツモは自動です(配牌のあとと、捨てた直後)。ツモは${S.L}回まで。</li><li>牌を3枚タップすると、語になれば面子になります。2枚タップで、雀頭か搭子(あと1枚で語)にできます。組んだ牌をタップすると解除します。</li><li>14枚を、組んでいなくても、4語+雀頭に分けられればアガれます(「アガる」を押します)。得点は、いちばん翻が高い分け方で数えます。</li><li>「ぉ゛」は、「お」の代わりに使える牌です(4枚)。使ってアガると、「オホ声」の役が付きます。</li>
  <li>${S.N}ゲーム以内に目標点を取るとステージクリア。失敗するとライフが1つ減り、ライフ0で終了です。</li><li>ツモを使い切ってテンパイなら、ゲームを消費しません(連続で積み点)。</li><li>「ヒント」をオンにすると、面子・雀頭・搭子の一覧、完成牌(橙色)、役ナビ、惜しかった役を表示します(最初はオフです)。</li></ul>`,
 [{label:"はじめる",fn:()=>{hideModal();newRun();}}]);
})();
