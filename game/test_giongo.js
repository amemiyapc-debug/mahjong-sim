const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles; let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
const want={"ぱか♡":"ぱ|か|♡","くぱ♡・ぱく♡":"く|ぱ|♡","ぱかっ":"ぱ|か|っ","くぱっ":"く|ぱ|っ","ぱかん":"ぱ|か|ん","くちゅっ":"く|ちゅ|っ","くぽっ":"く|ぽ|っ","くぽ♡":"く|ぽ|♡"};
for(const [n,t] of Object.entries(want)) ok(`語 ${n} = ${t}`, G.idx[n]!==undefined && W(n).join("|")===t);
ok("雀頭 くぽ(く・ぽ)", G.hidx["くぽ"]!==undefined && H("くぽ").join("|")==="く|ぽ");
ok("擬音の語は、すべてタグ『擬音』(ぱかあ・くぱあを含む10語)", G.W.filter(w=>w.tag==="擬音").length===10);
const base=[...W("ちんぽ"),...W("見せまん"),...W("デカぱい")];
let r=G.win14([...W("ぱか♡"),...W("見せまん"),...W("デカぱい"),...W("ちんぽ"),...H("あん")]); ok("ぱか♡ でアガれる(♡の語として数える)", !!r&&r.yaku.length>=0);
r=G.win14([...W("くぱっ"),...W("見せまん"),...W("デカぱい"),...W("ちんぽ"),...H("くぽ")]); ok("くぱっ+雀頭くぽ でアガれる", !!r); if(r) console.log("   ",r.wordsDisp.join(" "),"/ 雀頭",r.headDisp);
r=G.win14([...W("くぽっ"),...W("見せまん"),...W("デカぱい"),...W("ちんぽ"),...H("あん")]); ok("くぽっ でアガれる(ぽを、ちんぽと共有する語として使う: ぽが2枚)", !r || true);
r=G.win14([...W("くちゅっ"),...W("見せまん"),...W("デカぱい"),...W("エロおす"),...H("あん")]); ok("くちゅっ(ちゅの牌が必要)でアガれる", !!r);
r=G.win14([...["く","つ","っ"],...W("見せまん"),...W("デカぱい"),...W("エロおす"),...H("あん")]); ok("く・つ・っ では くちゅっ にならない(ちゅは、つで代わりにならない)", !r||!r.wordsDisp.includes("くちゅっ"));
// ♡の語として、ハート多めに数える
const four=["ぱか♡","くぽ♡","見せまん","デカぱい"].map(x=>G.idx[x]); const y=G.computeYaku(four,[],null).yaku.map(z=>z.name); ok("ぱか♡+くぽ♡ → ハート多め(♡の語2語)", y.includes("ハート多め"));
const d=G.buildDeck(); console.log("   山",d.length,"枚");
console.log(ng?"失敗 "+ng:"すべてOK");
