// ===== エンディング(20261010-1925 作業6。CLAUDE.md §1-2「エンディング」): 1周目のステージ3クリア後 =====
// a 最終の碑文に、最後に和了した一文が彫られる(アガリ演出の段階2と同じ文字演出)→ b 光とともにモザイクが外れる → c 図鑑の語が1語ずつ連続表示(役割の順)
// → d 役割が切り替わるたびにリナの表情が変わる(プレースホルダ)→ e 最後のセリフ(仮)→ f 1周目の本当の解読点の合計(モザイクなし)。全体 30〜40秒以内。スキップ可。終わったら2周目(研究♡1)
const END_STAGE=3;                                   // 1周目のこのステージをクリアするとエンディング(ステージ数は未決。決まっている条件の最終ステージ)
const FACES=[{id:"face_dohya",t:"ドヤ顔",c:"#ffe08a"},{id:"face_blush",t:"赤面",c:"#ffb4a2"},{id:"face_trouble",t:"赤面・困り顔",c:"#ff9a8b"},{id:"face_angry",t:"赤面・怒り顔",c:"#ff7b7b"},{id:"face_cry",t:"赤面・泣きそうな顔",c:"#ff6a8a"},{id:"face_red_max",t:"いちばん赤い顔",c:"#e8244f"}];
const END_LINE="リナ「……こ、こんな意味だったなんて……。ぜ、ぜんぶ、読めちゃった……っ」";   // 最後のセリフ(仮。未決)
const END_MS={wordMin:300,wordMax:500,wordBudget:21000};   // 1語 0.3〜0.5秒。語の連続表示は、全体で約21秒以内
let pendingEnding=false,endRunning=false,endJump=false,endTok=0;window._endLog=[];window._endTypeLog=[];
function endFace(i){const f=FACES[i];const el=$$("en-face");el.style.background=f.c;el.textContent=f.id+"\n"+f.t;el.dataset.face=f.id;window._endLog.push({face:f.id,t:Math.round(performance.now()-window._endT0)});}
function maybeEnding(){if(pendingEnding&&!endRunning){pendingEnding=false;startEnding();}}
function endWords(){   // 図鑑に入った語(未入手は出さない)を、役割(slot)の順に
  const seen=seenWords(),ws=[];DICT.words.forEach((w,i)=>{if(seen.has(w.name))ws.push({name:String(w.name).split("・")[0],slot:WA[i].slot,i});});
  ws.sort((a,b)=>a.slot-b.slot||a.i-b.i);return ws;
}
async function startEnding(){
  if(endRunning)return;endRunning=true;endJump=false;const tok=++endTok;window._endLog=[];window._endTypeLog=[];window._endT0=performance.now();ensureAudio();
  const root=$$("ending"),pane=$$("en-pane");root.hidden=false;$$("en-next").hidden=true;$$("en-skip").hidden=false;
  const J={};const sl=ms=>new Promise((res,rej)=>setTimeout(()=>tok!==endTok?rej(CANCEL):endJump?rej(J):res(),ms));
  const log=id=>{$$("ending").dataset.stage=id;window._endLog.push({id,t:Math.round(performance.now()-window._endT0)});};
  const sentence=(won&&won.data&&won.data.sentence)||(PLAYLOG.games.slice(-1)[0]&&PLAYLOG.games.slice(-1)[0].result&&PLAYLOG.games.slice(-1)[0].result.sentence)||"";
  const ws=endWords();
  try{
    // a 碑文に彫る
    log("carve");endFace(0);const chars=Array.from(sentence),fit=fitType(Math.max(1,chars.length),268,200);
    pane.innerHTML='<div class="stone big mosaic" id="en-stone"><div class="tw" id="en-type" style="font-size:'+fit.fs+'px;line-height:1.25"></div></div><div class="en-cap" id="en-cap">最終の碑文</div>';
    const su=stoneURL();if(su)$$("en-stone").style.backgroundImage="url("+su+")";
    const ty=$$("en-type");chars.forEach((c,i)=>{if(i>0&&i%fit.c===0)ty.appendChild(document.createElement("br"));const sp=document.createElement("span");sp.textContent=c;sp.style.visibility="hidden";ty.appendChild(sp);});
    for(const sp of ty.querySelectorAll("span")){sp.style.visibility="visible";window._endTypeLog.push(Math.round(performance.now()-window._endT0));kasha();await sl(TYPE_MS);}
    $$("en-stone").classList.add("carved");await sl(700);
    // b 光とともに、意味が流れ込む。モザイクが外れる
    log("light");const fl=$$("shflash");fl.classList.remove("go");void fl.offsetWidth;fl.classList.add("go");gachaSfx();
    $$("en-cap").textContent="意味が、流れ込んでくる……";$$("en-stone").classList.remove("mosaic");endFace(1);await sl(2600);
    // c・d 語が連続で表示され、役割が切り替わるたびに表情が変わる
    log("words");pane.innerHTML='<div class="en-word" id="en-w"></div><div class="en-role" id="en-r"></div>';
    const per=Math.max(Math.min(END_MS.wordMax,END_MS.wordBudget/Math.max(1,ws.length)),Math.min(END_MS.wordMin,END_MS.wordBudget/Math.max(1,ws.length)));
    const cyc=[2,3,4];let role=-1,ri=0;
    for(let k=0;k<ws.length;k++){const w=ws[k];
      if(w.slot!==role){role=w.slot;if(k>0){ri++;endFace(k===ws.length-1?5:cyc[(ri-1)%3]);}}
      if(k===ws.length-1&&ws.length>1)endFace(5);
      $$("en-w").textContent=w.name;$$("en-r").textContent=SLOTN[w.slot]+" ・ "+(k+1)+"/"+ws.length;tone(520+(k%7)*60,.12,"triangle",.07,0);await sl(per);}
    if(!ws.length)endFace(5);
    // e 最後のセリフ
    log("line");endFace(5);pane.innerHTML='<div class="en-line">'+esc2(END_LINE)+'</div>';await sl(3200);
    throw J;
  }catch(e){
    if(e===CANCEL){endRunning=false;return;}
    if(e!==J)throw e;
    // f 1周目の本当の解読点の合計(モザイクなし)
    log("total");endFace(5);const real=RUN.real;
    pane.innerHTML='<div class="en-line">'+esc2(END_LINE)+'</div><div class="en-cap">1周目の解読点(本当の値)</div><div class="reel big" id="en-total">'+Math.round(real).toLocaleString("en-US")+'</div><div class="en-cap">'+(ws.length)+'語を読み解いた</div>';
    $$("en-skip").hidden=true;$$("en-next").hidden=false;endRunning=false;window._endLog.push({id:"end",t:Math.round(performance.now()-window._endT0)});
  }
}
function endToLap2(){   // 終わったら周回数を2にし、研究♡1になる(lap_config.csv)
  $$("ending").hidden=true;RUN.hist=(RUN.hist||[]).concat([{lap:LAP,real:RUN.real}]);const prev=RUN.real;LAP=2;runSetLap(2);RUN.prevReal=prev;saveRun();
  STG.stage=1;STG.lives=3;STG.streak=0;newTry();STG.msg="2周目(研究♡「"+LVN[lvOf(0)]+"」)になった";STG.news="";try{render();}catch(e){}
}
