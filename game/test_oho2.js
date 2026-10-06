const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles;
let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
// 1) ぉ゛を使わない手(オホ声なし)
let h=[...W("ちんぽ"),...W("見せまん"),...W("ちん♡"),...W("おまめ"),...H("あん")];
let w=G.win14(h); ok("おまめでアガる(ぉ゛なし): オホ声なし", w&&!w.yaku.some(y=>y.name.startsWith("オホ声")));
// 2) おまめのお をぉ゛に替える → オホ声 1翻、表示は ぉ゛まめ
h=h.map(t=>t==="お"?"ぉ゛":t); w=G.win14(h);
ok("ぉ゛まめでアガれる(ぉ゛はおとして使える)", !!w);
ok("オホ声が1翻で付く", w&&w.yaku.some(y=>y.name==="オホ声"&&y.han===1)&&!w.yaku.some(y=>y.name==="オホ声・二"));
ok("語の表示が ぉ゛まめ になる", w&&w.wordsDisp.includes("ぉ゛まめ"));
// 3) ぉ゛を2枚(おまめ+おす♡)→ オホ声・二(2翻だけ。オホ声とは重ならない)
h=[...W("ちんぽ"),...W("見せまん"),...W("おす♡"),...W("おまめ"),...H("あん")].map(t=>t==="お"?"ぉ゛":t); w=G.win14(h);
ok("ぉ゛2枚: オホ声・二(2翻)のみ", w&&w.yaku.some(y=>y.name==="オホ声・二"&&y.han===2)&&!w.yaku.some(y=>y.name==="オホ声"));
// 4) 雀頭(おっ)にぉ゛
h=[...W("ちんぽ"),...W("見せまん"),...W("ちん♡"),...W("デカぱい"),"ぉ゛","っ"];
// v1.3m: 新語(ぽっち など)で、ほかの分け方のほうが翻が高くなるので、雀頭 おっ の分け方を、全分割から選んで確かめる
{ const ps=G.allPartitions(h), p=ps.find(p=>G.H[p.head].tiles.join("")==="おっ"); const dn=p&&G.displayNames(p.four.map(x=>({name:G.W[x].word,tiles:G.W[x].tiles})).concat([{name:G.H[p.head].head,tiles:G.H[p.head].tiles}]),h);
  const r=p&&G.scorePartition(h,p);
  ok("雀頭 ぉ゛っ でアガれる/表示(オホ声は、合体 完全オホ声 に吸収されうるので、成立した役 raw で見る)", p&&dn[4]==="ぉ゛っ"&&r.raw.includes("オホ声")); }
// 5) テンパイ: おの待ちは、おとぉ゛の両方
h=[...W("ちんぽ"),...W("見せまん"),...W("ちん♡"),...W("デカぱい"),"っ"]; const wc={}; G.buildDeck().forEach(t=>wc[t]=(wc[t]||0)+1);
const ws=G.tenpaiWaits(h,wc); ok("おっ待ち: おとぉ゛の両方が待ち", ws.includes("お")&&ws.includes("ぉ゛"));
// 6) 山の枚数
const d=G.buildDeck(); const cnt=t=>d.filter(x=>x===t).length; console.log("山",d.length,"枚 お",cnt("お"),"ぉ゛",cnt("ぉ゛"));
ok("ぉ゛は4枚", cnt("ぉ゛")===4);
// 7) 手牌のぉ゛で、お語が作れる扱い
const st=G.wordStatus2(["ぉ゛","ま","め"],wc); ok("手牌の ぉ゛・ま・め で おまめ が作れる", st.done.includes("おまめ"));
console.log(ng?("失敗 "+ng):"すべてOK");
