// core.js の役判定を、辞書から等間隔に選んだ40語の全組み合わせ(C(40,4)=91,390組・雀頭なし)で、Python(yaku14.Scorer)と全数照合する。
// (旧版は、全語の全組み合わせ(247語で約1.5億組)を Python の全数CSVと比べていたが、語が342語になり、全数は現実的でないため、部分集合の全数に変更)
const fs=require("fs"), cp=require("child_process"), path=require("path"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
const dir=process.env.HM_DIRNAME||"dan5", f=process.env.HM_PARITY_SUBSET||"/tmp/parity_subset.json";
if(!fs.existsSync(f)||process.env.HM_REGEN) cp.execSync(`python3 ${path.join(__dirname,"..","tests","make_parity_sample.py")} --dir ${dir} --mode subset --out ${f}`,{stdio:"inherit"});
const S=JSON.parse(fs.readFileSync(f,"utf8")); let bad=0; const t0=Date.now();
for(const s of S){ const r=G.computeYaku(s.four,[],null), a=[...new Set(r.raw)].sort().join("|"), b=s.raw.slice().sort().join("|");
  if(a!==b){ bad++; if(bad<=5) console.log("不一致",s.four.map(i=>G.W[i].word).join(","),"JS",a,"Python",b); } }
console.log("全数",S.length,"組(40語)。不一致",bad,"秒",((Date.now()-t0)/1000).toFixed(1));
console.log(bad===0?"すべてOK":"失敗");
