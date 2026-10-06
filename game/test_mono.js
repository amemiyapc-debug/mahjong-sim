// 役ナビの判定(mono: 語が増えても成立が崩れない条件)の確認。UI_SPEC §4・受け入れテスト8
//  (a) 4語+雀頭がそろった集合で、partialRaw(組んだ語だけの判定)が、完全な判定(computeYaku の raw のうち mono の行)と一致する
//  (b) 単調性: 4語+雀頭の部分集合(語を減らす・雀頭を外す)で成立した mono の役は、そろった集合でも成立している
//  (c) 非 mono の役は、partialRaw に出てこない
const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync(process.env.DATA||"data.json","utf8")));
let seed=24680; const rng=()=>{ seed=(seed*1664525+1013904223)%4294967296; return seed/4294967296; }; const ri=n=>Math.floor(rng()*n);
const N=+process.argv[2]||6000; let badA=0,badB=0,badC=0,total=0,maxMs=0;
const monoNames=new Set(G.rows.filter(r=>r.mono).map(r=>r.name)), nonMonoOnly=new Set(G.rows.filter(r=>!r.mono).map(r=>r.name)); G.rows.filter(r=>r.mono).forEach(r=>nonMonoOnly.delete(r.name));
for(let n=0;n<N;n++){
  const four=[]; const first=ri(G.W.length); four.push(first);
  while(four.length<4){ let j; if(rng()<0.55){ const w=G.W[first]; const pool=G.W.filter(x=>x.i!==first&&((w.stem&&x.stem===w.stem)||(w.part&&x.part===w.part)||(x.mods.some(m=>w.mods.includes(m))))); j=pool.length?pool[ri(pool.length)].i:ri(G.W.length); } else j=ri(G.W.length); if(!four.includes(j)) four.push(j); }
  const head=G.H[ri(G.H.length)], ho=G.headObj(head);
  const full=G.computeYaku(four,[],ho), fullMono=new Set(full.raw.filter(x=>monoNames.has(x)));
  const t0=process.hrtime.bigint(); const pr=G.partialRaw(four,ho); maxMs=Math.max(maxMs,Number(process.hrtime.bigint()-t0)/1e6);
  total++;
  if(pr.size!==fullMono.size||[...pr].some(x=>!fullMono.has(x))) badA++;
  for(let m=0;m<(1<<4);m++){ const sub=four.filter((_,k)=>m>>k&1); for(const h of [null,ho]){ const ps=G.partialRaw(sub,h); if([...ps].some(x=>!fullMono.has(x))) badB++; if([...ps].some(x=>nonMonoOnly.has(x))) badC++; } }
}
console.log(`集合 ${total}: (a)完全一致の不一致 ${badA} / (b)単調性の不一致 ${badB} / (c)非monoの混入 ${badC} / partialRaw 最大 ${maxMs.toFixed(2)}ms`);
console.log("mono の役:",monoNames.size,"種 / mono でない役のみ:",nonMonoOnly.size,"種",[...nonMonoOnly].slice(0,12).join(" "));
console.log(badA+badB+badC===0?"すべてOK":"失敗");
