const fs=require("fs"); const HM=require("./core.js");
const data=JSON.parse(fs.readFileSync("data.json","utf8")); const G=HM.setup(data);
const n=G.W.length; const cntBy={}; let total=0, none=0; const t0=Date.now();
for(let a=0;a<n;a++)for(let b=a+1;b<n;b++)for(let c=b+1;c<n;c++)for(let d=c+1;d<n;d++){
  const r=G.computeYaku([a,b,c,d]); total++; if(r.yaku.length===0) none++;
  for(const y of r.yaku) cntBy[y.name]=(cntBy[y.name]||0)+1;
}
console.log("組",total,"役なし",(none/total*100).toFixed(2)+"%","秒",((Date.now()-t0)/1000).toFixed(1));
// Pythonの全数計算(yaku_combo_share.csv)と比較
const lines=fs.readFileSync((process.env.HM_DATA_DIR||require("path").join(__dirname,"..","v13m"))+"/yaku_combo_share.csv","utf8").replace(/^\uFEFF/,"").trim().split("\n").slice(1);
let bad=0;
for(const ln of lines){ const f=ln.split(","); const name=f[0], py=parseInt(f[5],10); const js=cntBy[name]||0; if(py!==js){bad++; console.log("不一致",name,"Python",py,"JS",js);} }
console.log("役名",lines.length,"種を比較。不一致",bad);
