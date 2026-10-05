const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles; let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
const has=n=>G.idx[n]!==undefined, hasH=n=>G.hidx[n]!==undefined;
const base=[...W("ちんぽ"),...W("見せまん"),...W("デカぱい")];
const win=(ws,head)=>G.win14([...ws.flatMap(W),...(Array.isArray(head)?head:H(head))]);
// v1.3m: 合体に吸収された役も、成立した役として数える(合体の元の役)
const names=r=>r?r.yaku.map(y=>y.name).concat(...(r.merges||[]).map(m=>m.sources)):[];
for(const n of ["けつ媚び","ちつ媚び","ちく媚び","まんしゃ","けつしゃ","ぱいしゃ","がんしゃ","くち穴","くち♡","エロおな","おな♡","媚びおな","ぬれおな","おなめ","ぱかあ","くぱあ","ままあ","すき♡・きす♡","穴すき・きす穴","エロすき・エロきす","ぬれすき・ぬれきす","きく♡","穴きく","きつく・きっく","きくう","ちくコキ・くちコキ","エロちく・エロくち"]) ok("語がある: "+n, has(n));
ok("雀頭 いく・きく がある", hasH("いく")&&hasH("きく"));
// 役
let r=win(["おな♡","ちんぽ","見せまん","デカぱい"],"あん"); ok("おな♡ → オナニー(1翻)", names(r).includes("オナニー"));
r=win(["おなめ","ちんぽ","見せまん","デカぱい"],"あん"); ok("おなめ → 女王様", names(r).includes("女王様")); 
r=win(["ままあ","ちんぽ","見せまん","デカぱい"],"あん"); ok("ままあ → 赤ちゃんプレイ", names(r).includes("赤ちゃんプレイ"));
r=win(["まま♡","ちんぽ","見せまん","デカぱい"],"あん"); ok("まま♡ → 赤ちゃんプレイ", names(r).includes("赤ちゃんプレイ"));
r=win(["すき♡・きす♡","ちんぽ","見せまん","デカぱい"],"あん"); ok("すき♡・きす♡ → ラブ系", names(r).includes("ラブ系"));
r=win(["すき♡・きす♡","ちゅっちゅ","見せまん","デカぱい"],"あん"); ok("すき(きす)+ちゅっちゅ → キスの雨(キス系2語)", names(r).includes("キスの雨"));
r=win(["きく♡","ちんぽ","見せまん","デカぱい"],"あん"); ok("きく♡ → 快感系", names(r).includes("快感系"));
r=win(["ちんぽ","見せまん","デカぱい","エロまん"],"きく"); ok("雀頭きく → 快感系", names(r).includes("快感系"));
// つ=っ(互換)
r=win(["けつ媚び","ちんぽ","見せまん","デカぱい"],"あん"); ok("けつ媚び でアガれる", !!r);
r=G.win14([...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),"き","っ","く",...H("あん")]); ok("き・っ・く で きつく・きっく が成立(つ=っ)", !!r&&r.wordsDisp.some(n=>n.includes("きつく")));
r=G.win14([...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),"い","く","つ",...H("あん")]); ok("い・く・つ でも いくっ が成立(つ=っ)", !!r&&r.wordsDisp.some(n=>n.startsWith("いく")));
console.log("   表示:", r?r.wordsDisp.join(" "):"");
r=G.win14([...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),"け","っ","穴",...H("あん")]); ok("け・っ・穴 で けつ穴(っをつとして使う)", !!r); console.log("   表示:", r?r.wordsDisp.join(" "):"");
// つ≠ちゅ(一方向)は維持
r=G.win14([...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),"つ","っ","つ",...H("あん")]); ok("つ・っ・つ では ちゅっちゅ にならない", !r||!r.wordsDisp.includes("ちゅっちゅ"));
// 山: つ・っの枚数は、それぞれの語の数から
const d=G.buildDeck(); const c=t=>d.filter(x=>x===t).length; console.log("   山",d.length,"枚 つ",c("つ"),"っ",c("っ"),"ちゅ",c("ちゅ"),"お",c("お"),"ぉ゛",c("ぉ゛"));
console.log(ng?"失敗 "+ng:"すべてOK");
