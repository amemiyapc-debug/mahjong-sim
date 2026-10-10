"""試作HTMLへの追加(20261010-1925 作業5): 句バナーとリナの台詞・句の図鑑。make_prototype.py から apply(s)。適用済み(/* dan6:g */)なら飛ばす。
1手に表示・記録する句は PHRASE_CAP_PER_HAND(data/phrase_config.csv。既定1)。看板優先、なければ出現回数の少ない型(ichishuu/phrase_types.py の select_phrases と同じ)。100語版だけ(CFG.PH)。"""

PHJS = r'''// ===== 句(20261010-1925 作業5): 成立した句のうち、表示・記録する句だけを選び、バナーとリナの台詞を出す =====
const PH=CFG.PH||null;
const PD_KEY="hm-proto-phrasedex";
function loadPD(){try{return JSON.parse(localStorage.getItem(PD_KEY)||"null")||{sb:{},ty:{}};}catch(e){return {sb:{},ty:{}};}}
function savePD(d){try{localStorage.setItem(PD_KEY,JSON.stringify(d));}catch(e){}}
const wnm=i=>String(DICT.words[i].name).split("・")[0];
function fillAB(t,a,b){return String(t).replace(/\{A\}/g,wnm(a)).replace(/\{B\}/g,wnm(b));}
// 1手で成立した句(2語が、同じ分け方に入る)から、表示・記録する句を cap 個選ぶ
function selectPhrases(parts,cap){
  if(!PH||!cap)return [];
  const cand=[],seen=new Set();
  for(const p of parts){const ids=new Set(p.melds.map(m=>WI.get(m.word.name)));
    PH.SB.forEach((x,k)=>{if(ids.has(x[0])&&ids.has(x[1])){const key="sb"+k;if(!seen.has(key)){seen.add(key);cand.push({kind:"sb",k,a:x[0],b:x[1]});}}});
    for(const [t,l] of Object.entries(PH.TY))l.forEach(x=>{if(ids.has(x[0])&&ids.has(x[1])){const key="ty"+t+"|"+Math.min(x[0],x[1])+"|"+Math.max(x[0],x[1]);if(!seen.has(key)){seen.add(key);cand.push({kind:"ty",t,a:x[0],b:x[1]});}}});}
  const rest=cand.slice(),out=[],pick=a=>a[Math.floor(Math.random()*a.length)];
  for(let n=0;n<cap&&rest.length;n++){
    const sb=rest.filter(c=>c.kind==="sb");let c;
    if(sb.length)c=pick(sb);
    else{const byT={};rest.forEach(x=>{(byT[x.t]=byT[x.t]||[]).push(x);});const least=Math.min(...Object.keys(byT).map(t=>PH.FREQ[t]));
      const t=pick(Object.keys(byT).filter(t=>PH.FREQ[t]===least));c=pick(byT[t]);}
    out.push(c);rest.splice(rest.indexOf(c),1);
  }
  return out;
}
// バナーとリナの台詞。1周目(研究♡0)は「リナ曰く」の誤読。エンディング後(2周目以降)は理解後の名前(「リナ曰く」は付けない)。点にはならない(句の倍率 PHRASE_MULT は未決)
function phraseView(c,lap1){
  const A=wnm(c.a),B=wnm(c.b);let name,sub;
  if(c.kind==="sb"){const x=PH.SB[c.k];name=lap1?"リナ曰く「"+x[3]+"」":(x[2]||(A+"+"+B));sub=A+" + "+B;}
  else{const T=PH.TYD[c.t];name=lap1?fillAB(T.lap1,c.a,c.b):T.desc.replace(/A/g,A).replace(/B/g,B);sub=T.name+"の句 ・ "+A+" + "+B;}
  return {name,sub};
}
function linaLine(c,n,lap1){   // n: その句が成立した回数(今回を含む)。初めては必ず。2回目以降は LINA_EVERY 回に1回
  if(!(n===1||(n-1)%CFG.LINA_EVERY===0))return "";
  const L=PH.LINES,pre=lap1?"":"after_",kind=(c.kind==="sb"?"sb_":"ty_")+(n===1?"first":"again"),t=L[pre+kind];if(!t)return "";
  const M=c.kind==="sb"?(lap1?PH.SB[c.k][3]:(PH.SB[c.k][2]||wnm(c.a)+"+"+wnm(c.b))):"";
  return fillAB(t,c.a,c.b).replace(/\{M\}/g,M);
}
function pickPhrase(parts,record){
  const sel=selectPhrases(parts,CFG.PHRASE_CAP);if(!sel.length)return null;
  const c=sel[0],lap1=lvOf(0)===0;let n=1;
  if(record){const d=loadPD();
    if(c.kind==="sb"){const e=d.sb[c.k]=d.sb[c.k]||{n:0,lap:LAP};n=++e.n;}
    else{const T=d.ty[c.t]=d.ty[c.t]||{};const k=Math.min(c.a,c.b)+"|"+Math.max(c.a,c.b);const e=T[k]=T[k]||{n:0,a:c.a,b:c.b};n=++e.n;}
    savePD(d);}
  const v=phraseView(c,lap1),lina=linaLine(c,n,lap1);
  return {c,lap1,name:v.name,sub:v.sub,lina,n,html:'<div class="pn">'+esc2(v.name)+'</div><div class="ps">'+esc2(v.sub)+'</div>'+(lap1?'<div class="ps">(解読点にはならない)</div>':'')+(lina?'<div class="pl">'+esc2(lina)+'</div>':'')};
}
function phraseDexHTML(){
  if(!PH)return "";const d=loadPD();let s='<h3 style="font-size:.85rem;margin:12px 0 4px">句の図鑑(表示した句だけ)</h3>';
  const sbs=Object.keys(d.sb);s+='<div class="hint">看板 '+sbs.length+'/'+PH.SB.length+'</div>';
  sbs.forEach(k=>{const x=PH.SB[k],e=d.sb[k];s+='<div class="ig-meta">'+esc2(wnm(x[0])+" + "+wnm(x[1]))+' … 1周目: 「'+esc2(x[3])+'」'+(RUN.lap>1||e.lap<LAP?' / 理解後: '+esc2(x[2]||(wnm(x[0])+"+"+wnm(x[1]))):"")+'('+e.n+'回)</div>';});
  Object.keys(PH.TYD).forEach(t=>{const T=d.ty[t]||{},ks=Object.keys(T);s+='<div class="ig-meta"><b>'+esc2(PH.TYD[t].name)+'</b> '+ks.length+'/'+PH.TY[t].length+(ks.length?' … '+ks.slice(0,8).map(k=>esc2(wnm(T[k].a)+"+"+wnm(T[k].b))).join("・")+(ks.length>8?" …":""):"")+'</div>';});
  return s;
}
'''


def apply(s):
    if "/* dan6:g */" in s:
        return s

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6g パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    sub1("function itemsHTML(sc){", PHJS + "function itemsHTML(sc){")
    sub1("  const near=nearSwap(ws,hd,oho,own.satNames);", "  const near=nearSwap(ws,hd,oho,own.satNames);\n  const phrase=pickPhrase(parts,!practice);")
    sub1("ura,total,gs,gsReal:", "phrase,ura,total,gs,gsReal:")
    sub1('''${d.linkPairs.length?" ・ しりとり成立! "+d.linkPairs.join(" "):""}</div>`;''', '''${d.linkPairs.length?" ・ しりとり成立! "+d.linkPairs.join(" "):""}</div>`;
  if(d.phrase)s+=`<div class="phb">${d.phrase.html}</div>`;''')
    sub1("  box.innerHTML=s;\n}\nconst esc2=", "  s+=phraseDexHTML();\n  box.innerHTML=s;\n}\nconst esc2=")
    sub1(".sh-btns[hidden]{display:none}", ".sh-btns[hidden]{display:none}\n.pn{font-size:1.15rem}.ps{font-size:.75rem;opacity:.8;margin-top:4px}.pl{margin-top:8px;padding:6px 10px;border-radius:10px;background:#2a1b4d;font-size:.85rem;font-weight:700}\n.phb{margin:8px 0;padding:8px 12px;border-radius:10px;background:linear-gradient(135deg,#3a1d5c,#7a2a74);border:2px solid #f15bb5;color:#fff;font-weight:800}")
    s = s.replace("/* dan6:f */", "/* dan6:f *//* dan6:g */", 1)
    return s
