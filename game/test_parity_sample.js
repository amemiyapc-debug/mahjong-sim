const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const buf=fs.readFileSync("/tmp/sample_combos.bin"); const arr=new Int16Array(buf.buffer,buf.byteOffset,buf.length/2); const T=arr.length/4;
const cntBy={}; let none=0; const t0=Date.now();
for(let k=0;k<T;k++){ const four=[arr[4*k],arr[4*k+1],arr[4*k+2],arr[4*k+3]]; const r=G.computeYaku(four,[],null); if(!r.yaku.length) none++; for(const y of r.yaku) cntBy[y.name]=(cntBy[y.name]||0)+1; }
console.log("抽出",T,"組 役なし",(none/T*100).toFixed(2)+"%","秒",((Date.now()-t0)/1000).toFixed(0));
const lines=fs.readFileSync((process.env.HM_DATA_DIR||require("path").join(__dirname,"..","v13m"))+"/yaku_combo_share.csv","utf8").replace(/^\uFEFF/,"").trim().split("\n").slice(1);
let bad=0; for(const ln of lines){ const f=ln.split(","); const name=f[0], py=parseInt(f[5],10); const js=cntBy[name]||0; if(py!==js){ bad++; if(bad<=6) console.log("不一致",name,"Python",py,"JS",js); } }
console.log("役名",lines.length,"種を比較。不一致",bad);
