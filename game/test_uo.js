const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const W=w=>G.W[G.idx[w]].tiles, H=h=>G.H[G.hidx[h]].tiles; let ng=0; const ok=(n,c)=>{ console.log((c?"OK  ":"NG  ")+n); if(!c) ng++; };
for(const [w,fl] of [["うおお","オホ声系"],["あうう","可愛い系"],["うんん","可愛い系"]]) ok(`${w}(3牌)=${fl}の面子`, G.idx[w]!==undefined && G.W[G.idx[w]].flavor===fl && G.W[G.idx[w]].tag==="喘ぎ声");
for(const [h,fl] of [["うお","オホ声系"],["あう","可愛い系"],["うん","可愛い系"]]) ok(`${h}(2牌)=${fl}の雀頭`, G.hidx[h]!==undefined && G.H[G.hidx[h]].flavor===fl);
// 雀頭うおで獣の声、うんで可愛い声
const four=["ちんぽ","見せまん","エロおす","デカぱい"].map(x=>G.idx[x]);
const y1=G.computeYaku(four,[],{head:"うお",type:"喘ぎ声",flavor:"オホ声系",stem:""}).yaku.map(y=>y.name); ok("雀頭うお → 獣の声", y1.includes("獣の声"));
const y2=G.computeYaku(four,[],{head:"うん",type:"喘ぎ声",flavor:"可愛い系",stem:""}).yaku.map(y=>y.name); ok("雀頭うん → 可愛い声", y2.includes("可愛い声"));
// 喘ぎ二重唱: うおお + あうう
const four2=["うおお","あうう","ちんぽ","デカぱい"].map(x=>G.idx[x]); const y3=G.computeYaku(four2,[],{head:"あん",type:"喘ぎ声",flavor:"可愛い系",stem:""}).yaku.map(y=>y.name); ok("うおお+あうう → 喘ぎ二重唱", y3.includes("喘ぎ二重唱"));
// 実際の手でアガる(うんんを使う・雀頭うお)
const h=[...W("うんん"),...W("ちんぽ"),...W("見せまん"),...W("デカぱい"),...H("うお")]; const w=G.win14(h); ok("うんん+雀頭うおでアガれる", !!w); if(w) console.log("  ",w.wordsDisp.join(" "),"/ 雀頭",w.headDisp);
// こうび(う)が専用牌でなくなった
const use={}; G.W.forEach(x=>x.rawKinds.forEach(t=>use[t]=(use[t]||0)+1)); G.H.forEach(x=>x.rawKinds.forEach(t=>use[t]=(use[t]||0)+1));
console.log("う を使う語・雀頭:",use["う"]); ok("うが専用牌でなくなった", use["う"]>=2);
console.log(ng?"失敗 "+ng:"すべてOK");
