const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles;
let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
const base=[...W("ちんぽ"),...W("見せまん"),...W("エロおす")];
// 1) ちゅ=つ: ちち ゅ♡ (ち + ちゅ + ♡)
let h=[...base,"ち","ちゅ","♡",...H("あん")]; let w=G.win14(h);
ok("ちゅをつとして使える(アガれて、ちゅが、つ・っの代わりに使われる)", w&&(w.wordsDisp.concat([w.headDisp])).some(n=>n.includes("ちゅ")));
h=[...base,"け","ちゅ","穴",...H("あん")]; w=G.win14(h); ok("けちゅ穴(けつ穴のつをちゅで)", w&&w.wordsDisp.some(n=>n.includes("けちゅ")));
// 2) つ→ちゅ は不可(つつ=ちゅっちゅとは認識できない)。つ・っ・つ では、ちゅっちゅが成立しない
h=[...W("ちんぽ"),...W("見せまん"),...W("エロおす"),"つ","っ","つ",...H("あん")]; w=G.win14(h); ok("つ・っ・つではちゅっちゅが成立しない", !w||!w.wordsDisp.includes("ちゅっちゅ"));
// 2b) ちゅ・つ・っ(つ1枚+ちゅ1枚)でも、ちゅっちゅには、ちゅが2枚いる
h=[...W("ちんぽ"),...W("見せまん"),...W("エロおす"),"ちゅ","つ","っ",...H("あん")]; w=G.win14(h); ok("ちゅ・つ・っではちゅっちゅが成立しない(ちゅが足りない)", !w||!w.wordsDisp.includes("ちゅっちゅ"));
// 2c) べろちゅ: べ・ろ・ちゅ は成立、べ・ろ・つ は不成立
h=[...W("ちんぽ"),...W("見せまん"),...W("エロおす"),"べ","ろ","ちゅ",...H("あん")]; w=G.win14(h); ok("べろちゅ(ちゅ1枚)は成立", w&&w.wordsDisp.includes("べろちゅ"));
h=[...W("ちんぽ"),...W("見せまん"),...W("エロおす"),"べ","ろ","つ",...H("あん")]; w=G.win14(h); ok("べ・ろ・つではべろちゅが成立しない", !w||!w.wordsDisp.includes("べろちゅ"));
// 3) 本物のちゅ2枚でちゅっちゅ(ちゅ→ちゅ)
h=[...W("ちんぽ"),...W("見せまん"),...W("エロおす"),"ちゅ","っ","ちゅ",...H("あん")]; w=G.win14(h); ok("ちゅ・っ・ちゅ でも成立", w&&w.wordsDisp.includes("ちゅっちゅ"));
// 4) 山の枚数
const d=G.buildDeck(); const cnt=t=>d.filter(x=>x===t).length; console.log("山",d.length,"枚 つ",cnt("つ"),"ちゅ",cnt("ちゅ"),"お",cnt("お"),"ぉ゛",cnt("ぉ゛"));
// 5) まま♡ → 赤ちゃんプレイ
h=[...W("まま♡"),...W("ちんぽ"),...W("見せちん"),...W("デカぱい"),...H("あん")]; w=G.win14(h);
ok("まま♡で赤ちゃんプレイ(2翻)", w&&w.yaku.some(y=>y.name==="赤ちゃんプレイ"&&y.han===2));
// 6) まめ=くり(別名)
ok("まめ♡の語幹はくり", G.W[G.idx["まめ♡"]].stem==="くり");
h=[...W("まめ♡"),...W("くり舐め"),...W("ちんぽ"),...W("デカぱい"),...H("あん")]; w=G.win14(h);
ok("まめ♡+くり舐め → くり好き(同じ語幹2語)", w&&w.yaku.some(y=>y.name==="くり好き"));
{ const four=["まめ♡","見せちん","ちんぽ","デカぱい"].map(x=>G.idx[x]);
  const y1=G.computeYaku(four,[],{head:"まめ",type:"略称",flavor:"女性器",stem:"くり"}).yaku.map(y=>y.name);
  ok("雀頭まめ+くり系の語1語 → くり一筋", y1.includes("くり一筋"));
  const y2=G.computeYaku(four,[],{head:"くり",type:"略称",flavor:"女性器",stem:"くり"}).yaku.map(y=>y.name); ok("雀頭くりでも くり一筋", y2.includes("くり一筋"));
  const y3=G.computeYaku(four,[],{head:"ちん",type:"略称",flavor:"男性器",stem:"ちん"}).yaku.map(y=>y.name); ok("雀頭ちん+ちん系の語(見せちん・ちんぽ?)→ ちん一筋", y3.includes("ちん一筋")); }
// 7) 命令語の役
h=[...W("なめろ"),...W("まぞ穴"),...W("ちんぽ"),...W("デカぱい"),...H("あん")]; w=G.win14(h);
ok("命令と服従(なめろ+まぞ穴)", w&&w.yaku.some(y=>y.name==="命令と服従"));
h=[...W("なめろ"),...W("せめな"),...W("ちんぽ"),...W("デカぱい"),...H("あん")]; w=G.win14(h);
ok("命令口調(命令語2語)", w&&w.yaku.some(y=>y.name==="命令口調"));
h=[...W("いくな"),...W("いくっ"),...W("ちんぽ"),...W("デカぱい"),...H("あん")]; w=G.win14(h);
ok("命令違反(いくな+いくっ)", w&&w.yaku.some(y=>y.name==="命令違反"));
console.log(ng?("失敗 "+ng):"すべてOK");
