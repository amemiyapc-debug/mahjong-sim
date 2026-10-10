/* dan6:show2 */
// ===== アガリ演出(20261010-1925 作業3): 段階ごとの画面。1画面にその段階の情報だけを出す =====
// 段階: 1 宣言 → 2 タイトル文字(金文字・石碑・1秒に5.2文字・ジングル。1周目は軽いモザイク)→ 3 縮んで語の位置へ → 4 句バナー(句が成立した手だけ)
//       → 5 淫 → 6 縁(北斗七星風) → 7 倍率と解読点リール(5〜7 は研究♡で解禁された項目だけ。1周目は出さない)→ 8 リザルト。1周目は、5〜7 の代わりに「解読点 +500」とモザイクの本当の解読点
const SHOW_CAP_MS=15000;                 // 全体の上限(仮)。打つ文字とジングルは削らず、ほかの段階を縮める
const TYPE_CPS=5.2, TYPE_MS=Math.round(1000/TYPE_CPS);   // 1秒に約5.2文字(1文字 約192ms)
const JUMP={};
let showFF=false, showJump=false, showT0=0;
window._typeLog=[];window._stageLog=[];
function mosaicNum(p){const s=Math.round(p).toLocaleString("en-US");let first=true;return s.replace(/\d/g,c=>{if(first){first=false;return c;}return "█";});}
function fitType(n,W,H){   // n文字を W×H に収める文字サイズと1行の文字数
  let best={fs:12,c:Math.max(1,n)};
  for(let r=1;r<=10;r++){const c=Math.ceil(n/r),fs=Math.floor(Math.min(46,W/c));if(fs*1.25*r<=H&&fs>best.fs)best={fs,c};}
  return best;
}
window._panes={};
function stageLabel(id,txt){const prev=$$("show").dataset.stage;if(prev&&prev!==id)window._panes[prev]=$$("sh-pane").innerText;   // 段階を離れるときの画面の文字(試験用の記録)
  const el=$$("sh-stage");el.textContent=txt;$$("show").dataset.stage=id;window._stageLog.push({id,t:Math.round(performance.now()-showT0)});}
function setPane(html){const p=$$("sh-pane");p.innerHTML=html;p.classList.remove("in");void p.offsetWidth;p.classList.add("in");return p;}
const SLOTCOL=["#E6E1EA","#FFB8D4","#FFD3C2","#F0A0DC","#BFD4FF","#CDB0F5","#FFF0A6"];
function wordsRow(d){return '<div class="sh-words">'+d.own.ws.map((w,i)=>'<span class="sw" style="background:'+SLOTCOL[WA[w].slot]+'">'+String(d.own.melds[i]).split("・")[0]+'</span>').join("")+'<span class="sw hd">'+d.own.head+'</span></div>';}
function planStages(d){
  const lv=d.lv,g=d.gs,S=["declare","title","shrink"];
  if(d.phrase)S.push("phrase");
  if(lv>=1){
    if(d.own.sc.items.some(x=>x.merge||!KZ.has(x.name)))S.push("yin");
    if(g.pairs.some(p=>p[2]-2>=1))S.push("en");
    if(showSteps(d).length)S.push("reel");
  }else S.push("base");
  S.push("result");return S;
}
function showSteps(d){   // リールの掛け算(解禁された項目だけ)
  const g=d.gs,lv=d.lv,u=k=>UNLOCK[k][lv],st=[];
  if(g.bonus>1)st.push({nm:"縁",f:g.bonus});                       // 句ボーナス(1+縁+淫)。表示名は「縁」(20261008-2130)
  if(u("phrase")&&typeof PHRASE_MULT!=="undefined"&&PHRASE_MULT&&d.phrase)st.push({nm:"句",f:PHRASE_MULT});
  if(u("chain")&&g.chain>1)st.push({nm:"連鎖",f:g.chain});
  if(u("theme")&&g.theme>1)st.push({nm:"テーマ",f:g.theme});
  return st;
}
const STAR_POS=[[64,114],[106,124],[152,94],[198,66],[244,34]];   // 北斗七星風(仮。星の並びの細部は未決)
const LNAME={1:"並",2:"良",3:"絶妙"};
function linkSnd2(k){const f=[523.25,659.25,880][k-1];tone(f,.22,"triangle",.1+.03*k,0,f*1.5);if(k>=2)tone(f*1.5,.3,"sine",.05*k,.05);if(k>=3){tone(f*2,.4,"sine",.06,.1);nzs(.2,.08,.1,6000,"highpass");}}
async function playShow(){
  if(!SHOW||!won||!won.data||showRunning)return;
  const d=won.data,g=d.gs,lv=d.lv;showRunning=true;skipShow=false;showFF=false;showJump=false;ensureAudio();const tok=++showTok;showT0=performance.now();window._typeLog=[];window._stageLog=[];window._panes={};$$("show").dataset.stage="";
  const sl=ms=>new Promise((res,rej)=>{const go=()=>tok!==showTok?rej(CANCEL):showJump?rej(JUMP):res();(skipShow||showJump)?go():setTimeout(go,showFF?ms/4:ms);});
  slShow=sl;
  const stages=planStages(d),typeN=Array.from(d.sentence).length;
  const fixed=typeN*TYPE_MS+1300+700, nvar=stages.filter(s=>!["title","result"].includes(s)).length;   // 打つ時間・ジングル・縮む時間は削らない
  const varBase=900*nvar+(g.pairs?g.pairs.length*300:0)+showSteps(d).length*600;
  const scale=Math.max(.4,Math.min(1,(SHOW_CAP_MS-fixed)/Math.max(1,varBase)));
  const T=ms=>Math.round(ms*scale);
  const root=$$("show");root.hidden=false;root.classList.remove("noanim");$$("sh-ingo").hidden=true;$$("sh-skip").hidden=false;$$("sh-close").hidden=true;
  try{
    for(const id of stages){
      showFF=false;
      if(id==="declare"){stageLabel(id,"① アガリ");setPane('<div class="sh-big"><span class="bigpop" style="display:inline-block">アガリ!</span></div>');SFX.pon&&SFX.pon(3);await sl(T(800));}
      else if(id==="title"){
        stageLabel(id,"② 淫語");const fit=fitType(typeN,268,230),chars=Array.from(d.sentence);
        let h='<div class="stone big'+(lv===0?' mosaic':'')+'" id="sh-stone"><div class="tw" id="sh-type" style="font-size:'+fit.fs+'px;line-height:1.25"></div></div>';
        setPane(h);const ty=$$("sh-type"),stone=$$("sh-stone");const su=stoneURL();if(su)stone.style.backgroundImage="url("+su+")";
        chars.forEach((c,i)=>{if(i>0&&i%fit.c===0)ty.appendChild(document.createElement("br"));const sp=document.createElement("span");sp.className="ch";sp.textContent=c;sp.style.visibility="hidden";ty.appendChild(sp);});
        const sps=ty.querySelectorAll(".ch");
        for(let i=0;i<sps.length;i++){sps[i].style.visibility="visible";window._typeLog.push(Math.round(performance.now()-showT0));kasha();await sl(TYPE_MS);}
        jingle();await sl(1300);
      }
      else if(id==="shrink"){
        stageLabel(id,"③ 語");const old=$$("sh-pane").innerHTML;
        setPane('<div class="stone big'+(lv===0?' mosaic':'')+'" id="sh-stone2"><div class="tw" id="sh-type2" style="font-size:'+Math.min(46,fitType(typeN,268,230).fs)+'px;line-height:1.25">'+$$("sh-type").innerHTML+'</div></div>'+wordsRow(d).replace('class="sh-words"','class="sh-words hid" id="sh-w"'));
        const st2=$$("sh-stone2"),su=stoneURL();if(su)st2.style.backgroundImage="url("+su+")";
        await sl(60);st2.classList.add("shrunk");$$("sh-type2").style.fontSize="13px";$$("sh-w").classList.remove("hid");SFX.pon&&SFX.pon(1);await sl(700);
      }
      else if(id==="phrase"){stageLabel(id,"④ 句");setPane('<div class="sh-phrase"><div class="pb">'+d.phrase.html+'</div></div>');SFX.pon&&SFX.pon(4);await sl(T(1700));}
      else if(id==="yin"){
        stageLabel(id,"⑤ 淫");const items=d.own.sc.items.filter(x=>x.merge||!KZ.has(x.name)).slice().sort((a,b)=>b.han-a.han);
        const p=setPane('<div class="sh-list" id="sh-yl"></div><div class="sh-sum" id="sh-ys"></div>');let sum=0;
        for(const x of items.slice(0,6)){const e=document.createElement("div");e.className="sh-li";e.innerHTML=(x.merge?'<small>合体</small> ':'')+x.name+' <b>+'+x.han+'淫</b>'+(x.merge?' <small>('+x.merge.join("+")+')</small>':'');$$("sh-yl").appendChild(e);sum+=x.han;SFX.pon&&SFX.pon(2);await sl(T(380));}
        if(items.length>6){const e=document.createElement("div");e.className="sh-li";e.textContent="…ほか "+(items.length-6)+" 件";$$("sh-yl").appendChild(e);sum=items.reduce((a,x)=>a+x.han,0);}
        $$("sh-ys").textContent="淫 合計 "+sum;await sl(T(600));
      }
      else if(id==="en"){
        stageLabel(id,"⑥ 縁");const names=d.own.ws.map(w=>DICT.words[w].name).concat(["【雀頭】"+DICT.heads[d.own.hd].name]),labs=d.own.melds.concat([d.own.head]);
        setPane('<div class="sh-graph2" id="sh-g2"><svg id="sh-svg2" viewBox="0 0 300 150" preserveAspectRatio="none"></svg><div id="sh-nodes2"></div></div><div class="sh-sum" id="sh-es">縁 +0</div>');
        const gr=$$("sh-g2"),svg=$$("sh-svg2"),nodes=$$("sh-nodes2"),pos=STAR_POS;
        names.forEach((n,i)=>{const e=document.createElement("div");e.className="nd";e.style.left=(pos[i][0]/3)+"%";e.style.top=(pos[i][1]/1.5)+"%";e.textContent="★ "+String(labs[i]).split("・")[0];nodes.appendChild(e);});
        const PC=["#9b5de5","#c94ad8","#f15bb5"];let sum=0;
        for(const [a,b,s] of g.pairs.slice().sort((x,y)=>x[2]-y[2])){
          const k=Math.min(3,s-2);if(k<1)continue;const ia=names.indexOf(a),ib=names.indexOf(b);if(ia<0||ib<0)continue;sum+=k;const col=PC[k-1];
          const ln=document.createElementNS("http://www.w3.org/2000/svg","line");ln.setAttribute("x1",pos[ia][0]);ln.setAttribute("y1",pos[ia][1]);ln.setAttribute("x2",pos[ib][0]);ln.setAttribute("y2",pos[ib][1]);
          ln.setAttribute("stroke",col);ln.setAttribute("stroke-width",String(1.5+k*1.2));ln.setAttribute("stroke-linecap","round");ln.setAttribute("data-k",k);svg.appendChild(ln);
          [ia,ib].forEach(i=>{const e=nodes.children[i];e.classList.add("on");e.style.setProperty("--pc",col);e.classList.remove("near");void e.offsetWidth;e.classList.add("near");});
          gr.style.boxShadow="0 0 "+(6+sum*5)+"px "+col+", inset 0 0 "+(8+sum*6)+"px "+col+"88";gr.style.background="rgba(155,93,229,"+(0.08+sum*0.03)+")";
          $$("sh-es").innerHTML="縁 +"+sum+' <small>('+LNAME[k]+')</small>';linkSnd2(k);await sl(T(360+k*120));
        }
        await sl(T(500));
      }
      else if(id==="reel"){
        stageLabel(id,"⑦ 解読点");const steps=showSteps(d);setPane('<div class="sh-mults" id="sh-mults"></div><div class="sh-total2"><div class="reel" id="sh-reel" data-points="500">500解読点</div></div>');
        const MC=["#7b2cbf","#b5179e","#f72585","#ff4d6d"];let cur=G6.FLOOR;
        for(let i=0;i<steps.length;i++){const {nm,f}=steps[i];const e=document.createElement("span");e.className="mc";e.style.setProperty("--mc",MC[i%4]);e.textContent=nm+" ×"+fx(f);$$("sh-mults").appendChild(e);multSnd(i);
          const nv=cur*f;await reelTo(cur,nv,Math.round((f>1?420:140)*scale));cur=nv;}
        await sl(T(500));
      }
      else if(id==="base"){
        stageLabel(id,"⑤ 解読点");const real=d.gsReal.points;
        setPane('<div class="sh-base"><div class="reel" id="sh-reel" data-points="500">解読点 +500</div><div class="sh-mosaic" id="sh-mos">'+mosaicNum(real)+'</div><small>リナには読めない数値</small></div>');SFX.pon&&SFX.pon(2);await sl(T(2200));
      }
      else if(id==="result"){await showResult(d,false);}
    }
  }catch(e){
    if(e===JUMP){skipShow=true;await showResult(d,true);}
    else if(e!==CANCEL)throw e;
  }
}
async function showResult(d,jumped){
  const g=d.gs,lv=d.lv;showFF=false;stageLabel("result","⑧ リザルト");
  const lines=[];lines.push("基本点 "+G6.FLOOR);
  if(lv>=1){lines.push("縁 ×"+g.bonus+' <small>(1 + 縁 '+g.linkBonus+' + 淫 '+g.yinApplied+')</small>');if(g.chain>1||UNLOCK.chain[lv])if(UNLOCK.chain[lv])lines.push("連鎖 ×"+fx(g.chain));if(UNLOCK.theme[lv])lines.push("テーマ ×"+g.theme+(g.themeName?' <small>('+g.themeName+')</small>':''));}
  const big=lv===0?'<div class="reel big bigpop" id="sh-reel" data-points="'+Math.round(g.points)+'">解読点 +'+fmtPts(g.points)+'</div><div class="sh-mosaic" id="sh-mos">'+mosaicNum(d.gsReal.points)+'</div><small>リナには読めない数値</small>':'<div class="reel big bigpop" id="sh-reel" data-points="'+Math.round(g.points)+'">'+fmtPts(g.points)+'解読点</div>';
  setPane('<div class="sh-result">'+big+'<div class="sh-break">'+lines.join("<br>")+'</div>'+(d.st?'<div class="sh-st"><small>'+d.st+'</small></div>':'')+'</div>');
  $$("sh-close").hidden=false;$$("sh-skip").hidden=true;$$("sh-ingo").hidden=false;refreshStar();
  if(!jumped){gachaSfx();flashScreen();shakeBox();confetti(40);await sl2(600);}
  skipShow=false;showRunning=false;
}
const sl2=ms=>new Promise(r=>setTimeout(r,ms));
