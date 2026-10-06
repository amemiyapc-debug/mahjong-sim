// core.js の役判定を、Python(yaku14.Scorer)の判定と、乱数で抽出した4語+雀頭の組で照合する(旧版: 標本のbinと全数CSVがあった v1.3 までの照合を置き換え)
//   python3 ../tests/make_parity_sample.py --dir dan5 --mode sample --n 30000 --out /tmp/parity_sample.json  を、自動で実行する
const fs=require("fs"), cp=require("child_process"), path=require("path"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const dir=process.env.HM_DIRNAME||"dan5", f=process.env.HM_PARITY_SAMPLE||"/tmp/parity_sample.json";
if(!fs.existsSync(f)||process.env.HM_REGEN) cp.execSync(`python3 ${path.join(__dirname,"..","tests","make_parity_sample.py")} --dir ${dir} --mode sample --n 30000 --out ${f}`,{stdio:"inherit"});
const S=JSON.parse(fs.readFileSync(f,"utf8")); let bad=0,badHan=0; const t0=Date.now();
for(const s of S){ const head=s.head>=0?G.headObj(G.H[s.head]):null, tiles=Array(s.oho).fill("ぉ゛");
  const r=G.computeYaku(s.four,tiles,head), a=[...new Set(r.raw)].sort().join("|"), b=s.raw.slice().sort().join("|");
  if(a!==b){ bad++; if(bad<=5) console.log("役の不一致",s.four.map(i=>G.W[i].word).join(","),"JS",a,"Python",b); }
  if(r.han!==s.han){ badHan++; if(badHan<=3) console.log("翻の不一致",r.han,s.han); } }
console.log("抽出",S.length,"組 役の不一致",bad,"/ 翻(合体なし)の不一致",badHan,"秒",((Date.now()-t0)/1000).toFixed(1));
console.log(bad+badHan===0?"すべてOK":"失敗");
