const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync(process.env.DATA||"data.json","utf8")));
let seed=1357; const rng=()=>{ seed=(seed*1664525+1013904223)%4294967296; return seed/4294967296; };
const N=+process.argv[2]||700, L=12; let win=0, han=0; const ys={}; const hist={}; const t0=Date.now();
for(let g=0;g<N;g++){
  const deck=HM.shuffle(G.buildDeck(),rng); let hand=deck.splice(0,13), draws=0;
  while(draws<L){
    const t=deck.pop(); draws++; const h14=hand.concat([t]); const w=G.win14(h14);
    if(w){ win++; han+=w.han; hist[Math.min(w.han,13)]=(hist[Math.min(w.han,13)]||0)+1; w.yaku.forEach(y=>ys[y.name]=(ys[y.name]||0)+1); break; }
    const wc={}; deck.forEach(x=>wc[x]=(wc[x]||0)+1); const a=G.analyze(h14,wc); hand=h14; hand.splice(a.rec>=0?a.rec:0,1);
  }
}
console.log(`${N}ゲーム: アガリ ${(win/N*100).toFixed(1)}% 平均翻 ${(han/win).toFixed(2)} (${((Date.now()-t0)/1000).toFixed(0)}秒)`);
console.log("翻の分布(アガリ手):",Object.keys(hist).sort((a,b)=>a-b).map(k=>k+"翻:"+(hist[k]/win*100).toFixed(1)+"%").join(" "));
const five=Object.keys(hist).filter(k=>k>=5).reduce((s,k)=>s+hist[k],0), eight=Object.keys(hist).filter(k=>k>=8).reduce((s,k)=>s+hist[k],0);
console.log(`5翻以上 ${(five/win*100).toFixed(1)}% / 8翻以上 ${(eight/win*100).toFixed(1)}%`);
const names=[...new Set(G.rows.map(r=>r.name))]; console.log("一度でも成立した役:",Object.keys(ys).length,"/",names.length,"種(アガリ",win,"回)");
const pick=["可愛い声","獣の声","同じ部位の雀頭","前後半々","ばらばら","多色","二刀流","つがい","喘ぎ二重唱","喘ぎながら絶頂","キスしながら喘ぐ","行為づくし","ちん系コンビ","まん系コンビ"];
console.log(pick.map(n=>n+" "+((ys[n]||0)/win*100).toFixed(1)+"%").join(" / "));
const hs=names.filter(n=>/一筋|ぞっこん/.test(n)); const hsTot=hs.reduce((s,n)=>s+(ys[n]||0),0); console.log(`〇〇一筋・ぞっこん(合計): ${(hsTot/win*100).toFixed(1)}%`);
