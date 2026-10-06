const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
function play(L,rng){
  const deck=HM.shuffle(G.buildDeck(),rng), hand=deck.splice(0,13); let draws=0;
  while(draws<L){ const t=deck.pop(); draws++; const h14=hand.concat([t]); const w=G.win14(h14); if(w) return {win:true,draws};
    const wc={}; deck.forEach(x=>wc[x]=(wc[x]||0)+1); const a=G.analyze(h14,wc); const di=a.rec>=0?a.rec:h14.indexOf(G.cpuChoose(h14,rng)); h14.splice(di,1); hand.length=0; hand.push(...h14); }
  const wc={}; deck.forEach(t=>wc[t]=(wc[t]||0)+1); return {win:false,tenpai:G.tenpaiWaits(hand,wc).length>0};
}
let seed=2024; const rng=()=>{ seed=(seed*1664525+1013904223)%4294967296; return seed/4294967296; };
const N=3000; const st={win:0,ten:0,no:0}; const t0=Date.now();
for(let g=0;g<N;g++){ const r=play(12,rng); if(r.win) st.win++; else if(r.tenpai) st.ten++; else st.no++; }
console.log(`analyze(決まった順序の牌効率ヒント) ${N}ゲーム: アガリ ${(st.win/N*100).toFixed(1)}% テンパイ流局 ${(st.ten/N*100).toFixed(1)}% ノーテン ${(st.no/N*100).toFixed(1)}% (${((Date.now()-t0)/1000).toFixed(0)}秒)`);
