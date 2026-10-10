/* dan6:goro */
// ===== 語呂度・連鎖・テーマ・点(dan6/goro14.py の移植。解読点(内部名: points) = 500 × 句ボーナス × 連鎖倍率 × テーマ倍率。研究♡で解禁された項目だけが入る) =====
const G6={BASE:{"0,1":1,"0,2":3,"0,3":1,"1,2":2,"1,3":2,"1,5":1,"1,6":1,"2,3":3,"2,4":2,"2,5":2,"2,6":1,"3,4":2,"3,5":3,"3,6":1,"4,5":2,"4,6":1,"5,6":3},
 SAME:{"高まり|絶頂・結末":2,"感情・状況|命令・誘い":1,"行為|キス・吸い":1},
 MODS:["見せ","デカ","エロ","ぬれ","媚び","舐め","コキ","穴","♡","×2"],ALIAS:{"まめ":"くり","おまめ":"くり","すじ":"くり"},
 COMP:[["くりでイく","くり","絶頂"],["まんでイく","部位:女性器","絶頂"],["ちんでイく","部位:男性器","絶頂"],["胸でイく","部位:胸","絶頂"],["お尻でイく","部位:後ろ","絶頂"],["口でイく","部位:口","絶頂"],["ラブキス","キス","ラブ"],["調教","SM","態度"],["命令調教","SM","命令"],["濡れ濡れ","ぬれ","水音"],["見せつけ","見せ","絶頂"]],
 CL:{1:1,2:1,3:2,4:4,5:8},FLOOR:500};
const LVN=["無知","恥ずかしい","すけべ"],KEN=[4,3,2],SKIPN=[1,2,3];   // 研究♡0/1/2: 旧方式の語呂のしきい値 KEN(削除しない)・見送り回数(仮)
const KEN_MODE="table",KEN_CONST=3;                                       // data/score_config.csv。table=研究♡ごとのKEN(4/3/2。20261010-1210で決定)、const=一定(KEN_CONST)
const thOf=lv=>KEN_MODE==="table"?KEN[lv]:KEN_CONST;
const UNLOCK={base:[1,1,1],en:[0,1,1],yaku:[0,1,1],phrase:[0,1,1],chain:[0,0,1],theme:[0,0,1]};   // data/score_unlock.csv(研究♡0/1/2)
const LAP_KEN=[[1,0],[2,1],[3,2]];                                         // data/lap_config.csv: 周回数 -> 研究♡(3周目以降=2)
function kenLap(lap){let k=LAP_KEN[0][1];for(const [l,v] of LAP_KEN)if(lap>=l)k=v;return k;}
let LAP=1;try{const q=+new URLSearchParams(location.search).get("lap");if(q>=1)LAP=Math.floor(q);}catch(e){}   // 周回数。?lap=2 で指定
const STAGE_WINS=[[1,1],[2,2],[3,2]];                                      // data/stage_wins_lap1.csv: 1周目のステージ条件(3ゲームのうち必要な和了の回数)。表にないステージは最後の行
function winsNeeded(st){let n=STAGE_WINS[0][1];for(const [a,b] of STAGE_WINS)if(st>=a)n=b;return n;}
const lvOf=_stage=>kenLap(LAP);   // 研究♡は周回数で決まる。ステージ番号では変わらない(20261008-2250)
const G6ROW=new Map();
function g6mk(name,r){
  const kind=r[7],slotNo=r[0],sub=r[2],part=r[4],tone=r[5];
  const o={word:name,kind,slotNo,slot:r[1],sub,reading:r[3],part,tone,target:r[6]};
  o.eff=(kind==="雀頭"&&sub.includes("略称"))?6:slotNo;
  let n=name.replace("【雀頭】","").split("・")[0];for(const m of G6.MODS)n=n.split(m).join("");n=n.split("っ").join("つ");n=G6.ALIAS[n]||n;o.stem=n.length>=2?n.slice(0,2):n;
  o.theme=(part&&!part.includes("|"))?part:(o.eff===5||o.eff===6)?"感じる":(tone==="SM"||tone==="ラブ")?tone:"";
  const t=new Set(),nm=name.replace("【雀頭】","");
  if(part&&!part.includes("|"))t.add("部位:"+part);
  if(sub==="絶頂・結末"||sub==="雀頭・快感")t.add("絶頂");
  if(o.stem==="くり")t.add("くり");
  if(sub==="キス・吸い")t.add("キス");
  if(tone==="ラブ")t.add("ラブ");
  if(tone==="SM")t.add("SM");
  if(sub==="命令・誘い")t.add("命令");
  if(sub==="態度")t.add("態度");
  if(o.slot==="音")t.add("水音");
  if(nm.includes("ぬれ"))t.add("ぬれ");
  if(nm.includes("見せ"))t.add("見せ");
  o.tags=t;return o;
}
for(const [k,v] of Object.entries(DATA.GR))G6ROW.set(k,g6mk(k,v));
const g6word=n=>G6ROW.get(n),g6head=n=>G6ROW.get("【雀頭】"+n);
function g6ps(a,b){const A=a?new Set(a.split("|")):new Set(),B=b?new Set(b.split("|")):new Set();if(!A.size||!B.size)return 0;for(const x of A)if(B.has(x))return 2;
  const bd=["女性器","後ろ","口"];if((A.has("穴")&&bd.some(x=>B.has(x)))||(B.has("穴")&&bd.some(x=>A.has(x))))return 1;return null;}
function g6link(a,b,th){
  let sa=a.eff,sb=b.eff;if(sa>sb){[a,b]=[b,a];[sa,sb]=[sb,sa];}
  let base;
  if(sa===sb){const sub=r=>r.sub.replace("雀頭・","");base=G6.SAME[sub(a)+"|"+sub(b)];if(base===undefined)base=G6.SAME[sub(b)+"|"+sub(a)];if(base===undefined)base=1;}
  else base=G6.BASE[sa+","+sb]||0;
  for(const [x,y] of [[a,b],[b,a]])if(x.target&&x.eff<y.eff&&x.target===y.slot)base=Math.max(base,3);
  if(base===0)return 0;
  const p=g6ps(a.part,b.part);if(p===null)return 0;
  let t=0;if(a.tone&&b.tone){if(a.tone===b.tone)t=1;else if((a.tone==="ラブ"&&b.tone==="SM")||(a.tone==="SM"&&b.tone==="ラブ"))return 0;}
  const ra=a.reading,rb=b.reading;const ph=(ra.slice(-1)===rb.slice(0,1)||rb.slice(-1)===ra.slice(0,1)||ra.slice(0,1)===rb.slice(0,1)||ra.slice(-1)===rb.slice(-1))?1:0;
  const sc=base+p+t+ph;
  if(sa===sb&&p===0&&base<2)return 0;
  return sc>=th?sc:0;
}
function g6link2(a,b,th){
  let s=g6link(a,b,th);const same=a.eff===b.eff;
  if(a.tone&&b.tone&&((a.tone==="ラブ"&&b.tone==="SM")||(a.tone==="SM"&&b.tone==="ラブ")))return 0;
  if(same){if(a.stem===b.stem&&a.stem)s=Math.max(s,4);else if(a.theme&&a.theme===b.theme)s=Math.max(s,3);}
  else{if(a.stem===b.stem&&a.stem)s=s?s+2:3;}
  return s;
}
function g6uf(names){const par={};names.forEach(n=>par[n]=n);const f=x=>{while(par[x]!==x){par[x]=par[par[x]];x=par[x];}return x;};return {par,f};}
function g6collapse(nodes,L){
  const slot={};nodes.forEach(n=>slot[n.word]=n.eff);const u=g6uf(nodes.map(n=>n.word));
  const inner=L.filter(([a,b])=>slot[a]===slot[b]);inner.forEach(([a,b])=>{u.par[u.f(a)]=u.f(b);});
  const seen=new Map();
  for(const [a,b,s] of L){if(slot[a]===slot[b])continue;const k=[u.f(a),u.f(b)].sort().join("\u0001");seen.set(k,Math.max(seen.get(k)||0,s));}
  return inner.concat([...seen].map(([k,s])=>{const [x,y]=k.split("\u0001");return [x,y,s];}));
}
function g6chain(nodes,C){
  const u=g6uf(nodes.map(n=>n.word));C.forEach(([a,b])=>{u.par[u.f(a)]=u.f(b);});
  const comp=new Map();nodes.forEach(n=>{const r=u.f(n.word);const c=comp.get(r)||[0,0];c[0]++;comp.set(r,c);});
  C.forEach(([a,b])=>{comp.get(u.f(a))[1]++;});
  let m=0,size=1;for(const [n,e] of comp.values()){m+=Math.max(0,e-1);size=Math.max(size,n);}
  return {m,size};
}
const g6mult=m=>{let x=1;for(let k=1;k<=m;k++)x*=1+0.5*k;return x;};
function g6theme(nodes){
  const c1={},c2={};nodes.forEach(n=>{if(n.stem)c1[n.stem]=(c1[n.stem]||0)+1;if(n.theme)c2[n.theme]=(c2[n.theme]||0)+1;});
  let best=[1,"なし",0];
  for(const [nm,cnt] of Object.entries(c1).concat(Object.entries(c2)))if((G6.CL[cnt]||1)>best[0])best=[G6.CL[cnt]||1,"単:"+nm,cnt];
  let k1=Math.max(0,...Object.values(c1),...Object.values(c2));const comp=[];
  for(const [nm,A,B] of G6.COMP){const a=nodes.filter(n=>n.tags.has(A)),b=nodes.filter(n=>n.tags.has(B));
    if(a.length&&b.length){const k=new Set(a.concat(b).map(n=>n.word)).size;comp.push([nm,k]);if((G6.CL[k]||1)>best[0])best=[G6.CL[k]||1,"複合:"+nm,k];}}
  return {mult:best[0],name:best[1],k:k1,comp};
}
// words: 語名4つ、head: 雀頭名、lv: 研究♡(0/1/2)、yin: 名前つき役の淫の合計(裏読みを含む)
function g6score(words,head,lv,yin){
  const th=thOf(lv),u=k=>UNLOCK[k][lv],nodes=words.map(g6word).concat([g6head(head)]),L=[];
  for(let i=0;i<5;i++)for(let j=i+1;j<5;j++){const s=g6link2(nodes[i],nodes[j],th);if(s)L.push([nodes[i].word,nodes[j].word,s]);}
  const C=g6collapse(nodes,L),ch=g6chain(nodes,C),mult=g6mult(ch.m),th2=g6theme(nodes);
  const linkFull=C.reduce((s,x)=>s+Math.min(3,x[2]-2),0),link=linkFull*u('en'),yinA=yin*u('yaku'),bonus=1+link+yinA,chA=u('chain')?mult:1,tmA=u('theme')?th2.mult:1;
  return {lv,linkFull,chainFull:mult,themeFull:th2.mult,yinApplied:yinA,links:C.length,rawLinks:L.length,chainN:ch.m,chain:chA,bonus,linkBonus:link,yin,theme:tmA,themeName:th2.name,themeK:th2.k,composite:th2.comp,size:ch.size,pairs:C,points:u('base')?G6.FLOOR*bonus*chA*tmA:0};
}
const STAGE_WORD=["","語","句","節","文","碑文"];
const CONDN={1:"句を作る(2語がつながる)",2:"節を作る(3語がつながる)",3:"節で、テーマ語3つ",4:"文を作る(4語がつながる)",5:"複合テーマ成立(2タグの語3つ以上)",6:"文で、テーマ語4つ",7:"碑文を作る(5語全部つながる)",8:"碑文で、テーマ語5つ"};
function g6sat(g,c){
  if(c===1)return g.size>=2;if(c===2)return g.size>=3;if(c===3)return g.size>=3&&g.themeK>=3;if(c===4)return g.size>=4;
  if(c===5)return g.composite.some(x=>x[1]>=3);if(c===6)return g.size>=4&&g.themeK>=4;if(c===7)return g.size>=5;return g.size>=5&&g.themeK>=5;
}
/* /dan6:goro */
