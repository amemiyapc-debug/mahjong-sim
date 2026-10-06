const fs=require("fs"); const HM=require("./core.js");
const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const isA=()=>false;   // v1.3c 以降、雀頭は2牌の語で、喘ぎ牌はない(旧版の HM.isAegi は、なくなった)
// 牌効率のヒント: ①完成している語(面子) ②あと1枚の語(搭子) を選び、③どれにも使わない余りの牌から切る
function cpu3(hand14,wall,rng,info){
  const c={}; let heads=0; hand14.forEach(t=>{ if(isA(t)) heads++; else c[t]=(c[t]||0)+1; });
  const cand=[];
  for(const w of G.W){
    let matched=0,miss=0,mt=null; for(const t of w.kinds){ const have=Math.min(c[t]||0,w.need[t]); matched+=have; if(have<w.need[t]){ miss+=w.need[t]-have; mt=t; } }
    const take={}; for(const t of w.kinds) take[t]=Math.min(c[t]||0,w.need[t]);
    if(miss===0) cand.push({w,complete:true,uke:0,mt:null,take});
    else if(miss===1 && (wall[mt]||0)>0) cand.push({w,complete:false,uke:wall[mt],mt,take});
  }
  cand.sort((a,b)=> (b.complete-a.complete) || (b.uke-a.uke));
  const top=cand.slice(0,26);
  let best=null; const chosen=[]; const cc=Object.assign({},c);
  function evalSet(){ const blocks=chosen.length, comp=chosen.filter(x=>x.complete).length; const miss=new Set(); let uke=0;
    chosen.forEach(x=>{ if(!x.complete&&!miss.has(x.mt)){ miss.add(x.mt); uke+=wall[x.mt]; } });
    const sc=blocks*100000+comp*10000+Math.min(uke,9999); if(!best||sc>best.sc) best={sc,sel:chosen.slice()}; }
  (function dfs(s,k){ evalSet(); if(k===4) return;
    for(let j=s;j<top.length;j++){ const x=top[j]; const used=[]; let ok=true;
      for(const t of x.w.kinds){ const take=x.take[t]; if((cc[t]||0)<take){ok=false;break;} used.push([t,take]); }
      if(!ok) continue; used.forEach(([t,n])=>cc[t]-=n); chosen.push(x); dfs(j+1,k+1); chosen.pop(); used.forEach(([t,n])=>cc[t]+=n); } })(0,0);
  // 余りの牌 = 手牌から、選んだ語に使う牌と、雀頭1枚を除いたもの
  const rest=Object.assign({},c);
  if(best) best.sel.forEach(x=>{ for(const t of x.w.kinds){ rest[t]-=x.take[t]; } });
  const left=[]; for(const t in rest) for(let i=0;i<rest[t];i++) left.push(t);
  let headLeft=heads; if(heads>=1) headLeft=heads-1; for(let i=0;i<headLeft;i++) left.push(hand14.find(isA));
  if(left.length===0) return hand14[Math.floor(rng()*hand14.length)];   // (旧版: G.cpuChoose。なくなったので、ランダムに切る)
  // 余りのうち、ほかの牌とつながる語が少ない牌から切る(孤立牌から切る)
  const pot=t=>{ if(isA(t)) return -1; let p=0; for(const w of G.W){ if(!(t in w.need)) continue; let other=0; for(const u of w.kinds){ if(u===t) continue; other+=Math.min(c[u]||0,w.need[u]); } if(other>=1) p++; } return p; };
  let bp=1e9,bt=[]; new Set(left).forEach(t=>{ const p=pot(t); if(p<bp){bp=p;bt=[t];} else if(p===bp) bt.push(t); });
  if(info) info.blocks=best&&best.sel.map(x=>x.w.word+(x.complete?"":"(あと"+x.mt+")")); if(info) info.left=left;
  return bt[Math.floor(rng()*bt.length)];
}
function play(L,rng){
  const deck=HM.shuffle(G.buildDeck(),rng), hand=deck.splice(0,13); let draws=0;
  while(draws<L){ const t=deck.pop(); draws++; const h14=hand.concat([t]); const w=G.win14(h14);
    if(w) return {win:true,draws};
    const wc={}; deck.forEach(x=>wc[x]=(wc[x]||0)+1); const d=cpu3(h14,wc,rng); const i=h14.indexOf(d); h14.splice(i,1); hand.length=0; hand.push(...h14); }
  const wc={}; deck.forEach(t=>wc[t]=(wc[t]||0)+1); return {win:false,tenpai:G.tenpaiWaits(hand,wc).length>0};
}
let seed=99; const rng=()=>{ seed=(seed*1664525+1013904223)%4294967296; return seed/4294967296; };
const N=+process.argv[2]||1000; const st={win:0,ten:0,no:0}; let dr=0; const t0=Date.now();
for(let g=0;g<N;g++){ const r=play(12,rng); if(r.win){st.win++;dr+=r.draws;} else if(r.tenpai) st.ten++; else st.no++; }
console.log(`牌効率のヒント ${N}ゲーム: アガリ ${(st.win/N*100).toFixed(1)}% テンパイ流局 ${(st.ten/N*100).toFixed(1)}% ノーテン ${(st.no/N*100).toFixed(1)}% 平均アガリ巡目 ${(dr/Math.max(1,st.win)).toFixed(1)} (${((Date.now()-t0)/1000).toFixed(0)}秒)`);
// 手牌の例を1つ表示
const deck=HM.shuffle(G.buildDeck(),rng); const hand=G.sortHand(deck.splice(0,14)); const info={};
const d=cpu3(hand,(()=>{const wc={};deck.forEach(x=>wc[x]=(wc[x]||0)+1);return wc;})(),rng,info);
console.log("例の手牌:",hand.map(t=>t.replace("喘:","")).join(" ")); console.log(" 面子・搭子:",(info.blocks||[]).join(" / ")); console.log(" 余りの牌:",(info.left||[]).map(t=>t.replace("喘:","")).join(" "),"→ 捨てる:",d.replace("喘:",""));
