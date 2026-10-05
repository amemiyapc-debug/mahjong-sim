const fs=require("fs"); const HM=require("./core.js"); const data=JSON.parse(fs.readFileSync("data.json","utf8")); const G=HM.setup(data);
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles; let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
const tri=G.W.filter(w=>w.type==="修飾3型"); ok("修飾3型は100語",tri.length===100);
ok("山の枚数から、修飾3型を除いている(旧ルール: tile_usage.csv の max(4,使う語の数)。新ルール: tile_copies_adopted.csv と同じ)", (()=>{ const D=(process.env.HM_DATA_DIR||require("path").join(__dirname,"..","v13m")); const rd=n=>fs.readFileSync(D+"/"+n,"utf8").replace(/^\uFEFF/,"").trim().split("\n").slice(1).map(l=>l.split(","));
  if((data.options||{}).tileRule==="new"){ const exp={}; rd("tile_copies_adopted.csv").forEach(r=>exp[r[0]]=+r[4]); return Object.keys(exp).every(t=>G.deckCounts[t]===exp[t]); }
  const exp={}; rd("tile_usage.csv").forEach(r=>exp[r[0]]=Math.max(4,+r[1])); return Object.keys(exp).every(t=>G.deckCounts[t]===exp[t]); })());
const eg=["エロ媚び穴","見せ媚び♡","見せコキ穴","見せエロ♡"].filter(n=>G.idx[n]!==undefined); console.log("  採用済みの例:",eg.join(" "),"/ 未採用:",["エロ媚び穴","見せ媚び♡","見せコキ穴","見せエロ♡"].filter(n=>G.idx[n]===undefined).join(" "));
// 修飾3型を使ったアガリ
const t1=tri[0], t2=tri[1]; const h=[...t1.tiles,...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),...H("あん")]; const w=G.win14(h); ok(`修飾3型(${t1.word})でアガれる`, !!w); if(w) console.log("  ",w.wordsDisp.join(" "),"/",w.yaku.map(y=>y.name).join(","));
// 語頭づくし・語尾づくしは、修飾3型を含まない
const hd=["見せちん","デカぱい","エロまん","ぬれまん"].map(x=>G.idx[x]); const y1=G.computeYaku(hd,[],null).yaku.map(y=>y.name); ok("語頭づくし(位置で数える)", y1.includes("語頭づくし"));
const four=[tri[0].i,...["見せちん","デカぱい","エロまん"].map(x=>G.idx[x])]; const y2=G.computeYaku(four,[],null).yaku.map(y=>y.name); ok("修飾3型が混ざると語頭づくしは付かない", !y2.includes("語頭づくし"));
// 修飾づくし(単独語なし)には数える
ok("修飾3型は修飾づくしに数える", y2.includes("修飾づくし"));
console.log(ng?"失敗 "+ng:"すべてOK");
