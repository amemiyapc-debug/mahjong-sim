/* dan6:show */
// ===== アガリ演出(20261007-1345・1350): タイプライター(4文字/秒・金文字・石碑)→ ジングル → パワー溜め → 点リール → 最終(ガチャ風・碑文に刻む) =====
let STONE_URL=null;
function stoneURL(){
  if(STONE_URL!==null)return STONE_URL;
  try{const w=160,h=120,c=document.createElement("canvas");c.width=w;c.height=h;const g=c.getContext("2d");
    g.fillStyle="#7d9d96";g.fillRect(0,0,w,h);
    let sd=7;const rnd=()=>{sd=(sd*16807)%2147483647;return sd/2147483647;};
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){const r=rnd();if(r<.12){g.fillStyle="#6a8982";g.fillRect(x,y,1,1);}else if(r>.92){g.fillStyle="#98b8b0";g.fillRect(x,y,1,1);}}
    g.fillStyle="rgba(40,70,66,.16)";for(let k=0;k<14;k++)g.fillRect(Math.floor(rnd()*w),0,1+(k%2),10+Math.floor(rnd()*46));
    g.fillStyle="#b4d0c8";g.fillRect(0,0,w,2);g.fillRect(0,0,2,h);g.fillStyle="#3f5a56";g.fillRect(0,h-2,w,2);g.fillRect(w-2,0,2,h);
    STONE_URL=c.toDataURL();}catch(e){STONE_URL="";}
  return STONE_URL;
}
function nzs(d,g,when,cut,type){try{if(!AC||!SOUND||skipShow)return;const n=Math.floor(AC.sampleRate*d),b=AC.createBuffer(1,n,AC.sampleRate),x=b.getChannelData(0);for(let i=0;i<n;i++)x[i]=(Math.random()*2-1)*(1-i/n);const s=AC.createBufferSource(),f=AC.createBiquadFilter(),a=AC.createGain();s.buffer=b;f.type=type||"lowpass";f.frequency.value=cut||1800;a.gain.value=g||.2;s.connect(f);f.connect(a);a.connect(AC.destination);s.start(AC.currentTime+(when||0));}catch(e){}}
const m2f=n=>440*Math.pow(2,(n-69)/12);
// 1文字ごとの「カシャ」(タイプライター)。行末のベルは鳴らさない
function kasha(){nzs(.03,.3,0,3500,"highpass");tone(2300,.025,"square",.05,0,1500);nzs(.06,.16,.04,2200,"bandpass");tone(700,.035,"triangle",.06,.045,380);}
function mar(f,when,dur,g){tone(f,dur,"sine",g||.16,when);tone(f*4,dur*.35,"sine",(g||.16)*.35,when);nzs(.012,.05,when,5000,"highpass");}
function bell(f,when,dur,g){[1,2.76,5.4,8.9].forEach((m,i)=>tone(f*m,dur/(1+i*.6),"sine",(g||.12)/(1+i*1.3),when));}
// 打ち終わりのジングル(新作。Dドリアン+ブルーノート(Ab)、マリンバ+ベル、ウォーキングベース1小節。約2.8秒)
function jingle(){
  const B=60/104;
  [[38,0],[41,1],[45,2],[48,3]].forEach(([n,b])=>{tone(m2f(n),B*.9,"triangle",.2,b*B);tone(m2f(n)*2,B*.45,"sine",.05,b*B);});
  [[50,0],[53,0],[57,0],[60,0],[50,2.5],[57,2.5],[60,2.5]].forEach(([n,b])=>tone(m2f(n+12),.35,"triangle",.045,b*B));
  [[74,0,.5],[77,.67,.33],[76,1,.5],[72,1.5,.5],[68,2,.33],[69,2.33,.33],[72,2.67,.33]].forEach(([n,b,d])=>mar(m2f(n),b*B,d*B*1.6,.17));
  bell(m2f(74),3*B,1.1,.14);mar(m2f(62),3*B,.6,.1);
}
function linkSnd(s){const f=s>=5?880:s===4?659.25:523.25;tone(f,.2,"triangle",.12,0,f*1.5);if(s>=5)tone(f*1.5,.25,"sine",.06,.05);}
function multSnd(i){tone(330+i*110,.35,"sawtooth",.06,0,660+i*220);tone(165+i*55,.35,"sine",.1,0);}
function gachaSfx(){tone(200,.55,"sawtooth",.07,0,1800);for(let i=0;i<16;i++)tone(2000+Math.random()*3500,.08,"sine",.05,Math.random()*.9);[74,78,81,86].forEach((n,i)=>bell(m2f(n),.5+i*.05,1.1,.12));nzs(.5,.25,.5,6000,"highpass");}
const fx=x=>String(Math.round(x*100)/100);
async function reelTo(a,b,ms){
  const el=$$("sh-reel");if(!el)return;
  const steps=skipShow?1:Math.max(3,Math.round(ms/40));
  for(let i=1;i<=steps;i++){const e=1-Math.pow(1-i/steps,3);const v=i===steps?b:a*Math.pow(b/a,e);let t=fmtPts(v);
    if(i<steps)t=t.replace(/\d(?=\D*$)/,()=>String(Math.floor(Math.random()*10)));
    el.textContent=t+"点";if(!skipShow)SFX.tick();await slShow(40);}
  el.dataset.points=String(Math.round(b));el.textContent=fmtPts(b)+"点";
}
let slShow=()=>Promise.resolve();
async function playShow(){
  if(!SHOW||!won||!won.data||showRunning)return;
  const d=won.data,g=d.gs,sc=d.own.sc;showRunning=true;skipShow=false;ensureAudio();const tok=++showTok;
  const sl=ms=>new Promise((res,rej)=>{const go=()=>tok!==showTok?rej(CANCEL):res();skipShow?go():setTimeout(go,ms);});
  slShow=sl;
  try{
  const root=$$("show");root.hidden=false;root.classList.remove("noanim");
  ["sh-title","sh-type","sh-svg","sh-nodes","sh-mults","sh-total"].forEach(i=>$$(i).innerHTML="");
  $$("sh-ingo").hidden=true;$$("sh-skip").hidden=false;$$("sh-close").hidden=true;
  const st=$$("sh-stone"),gr=$$("sh-graph");st.classList.remove("carved");gr.style.boxShadow="";gr.style.background="";
  const su=stoneURL();if(su)st.style.backgroundImage="url("+su+")";
  $$("sh-title").innerHTML='<span class="bigpop" style="display:inline-block">アガリ!</span>';
  // 1) タイプライター: 完成した淫語(全文)→ 点に効く名前つき役(+N淫)。1文字 約250ms(1秒に4文字)。打っている間は「カシャ」だけ(メロディなし)
  const typ=$$("sh-type"),lines=[{t:d.sentence,c:"ln"}];
  const ys=sc.items.filter(x=>x.merge||!KZ.has(x.name)).slice().sort((a,b)=>b.han-a.han).map(x=>({t:x.name+" +"+x.han+"淫",c:"ln yk"}));
  if(d.ura>0)ys.unshift({t:"裏読み +"+d.ura+"淫",c:"ln yk"});
  const BUD=30;let used=d.sentence.length;      // 打つ文字数の上限(約7.5秒。「…他N」の3文字ぶんを残す。全体を約12秒に収めるため)
  for(let i=0;i<ys.length;i++){const more=ys.length-i-1>0?3:0;if(used+ys[i].t.length+more<=BUD){lines.push(ys[i]);used+=ys[i].t.length;}else{lines.push({t:"…他"+(ys.length-i),c:"ln yk"});break;}}
  for(const L of lines){const el=document.createElement("span");el.className=L.c;typ.appendChild(el);
    for(const ch of Array.from(L.t)){el.textContent+=ch;kasha();await sl(250);}}
  // 2) ジングル(約2.8秒)。途中からパワー溜めに入る
  jingle();await sl(1100);
  // 3) パワー溜め: 句(つながり)が1本できるたびに、語と語が線でつながり、光が強くなる(紫→ピンク)
  const names=d.own.ws.map(w=>DICT.words[w].name).concat(["【雀頭】"+DICT.heads[d.own.hd].name]),labs=d.own.melds.concat([d.own.head]);
  const nodes=$$("sh-nodes"),svg=$$("sh-svg"),pos=[];
  names.forEach((n,i)=>{const a=(-90+i*72)*Math.PI/180,x=150+105*Math.cos(a),y=75+52*Math.sin(a);pos.push([x,y]);
    const e=document.createElement("div");e.className="nd";e.style.left=(x/3)+"%";e.style.top=(y/1.5)+"%";e.textContent=String(labs[i]).split("・")[0];nodes.appendChild(e);});
  const PC=["#9b5de5","#b44be8","#c94ad8","#e04ac0","#f15bb5","#ff7ac8","#ff9ad5"];let lvl=0;
  for(const [a,b,s] of g.pairs.slice().sort((x,y)=>x[2]-y[2])){
    const ia=names.indexOf(a),ib=names.indexOf(b);if(ia<0||ib<0)continue;lvl++;const col=PC[Math.min(PC.length-1,lvl)];
    const ln=document.createElementNS("http://www.w3.org/2000/svg","line");
    ln.setAttribute("x1",pos[ia][0]);ln.setAttribute("y1",pos[ia][1]);ln.setAttribute("x2",pos[ib][0]);ln.setAttribute("y2",pos[ib][1]);ln.setAttribute("stroke",col);ln.setAttribute("stroke-width",String(1.5+s*.5));ln.setAttribute("stroke-linecap","round");svg.appendChild(ln);
    [ia,ib].forEach(i=>{const e=nodes.children[i];e.classList.add("on");e.style.setProperty("--pc",col);e.classList.remove("near");void e.offsetWidth;e.classList.add("near");});
    gr.style.boxShadow="0 0 "+(8+lvl*6)+"px "+col+", inset 0 0 "+(10+lvl*8)+"px "+col+"88";gr.style.background="rgba(155,93,229,"+(0.08+lvl*0.05)+")";
    linkSnd(s);await sl(270);
  }
  // 掛け算: 句ボーナス → 連鎖倍率 → テーマ倍率。点リールが、掛け算のたびに回る
  const T=$$("sh-total");T.innerHTML='<div class="reel" id="sh-reel" data-points="500">500点</div>';
  const MC=["#7b2cbf","#b5179e","#f72585"],steps=[["句ボーナス",g.bonus],["連鎖",g.chain],["テーマ",g.theme]];let cur=G6.FLOOR;
  for(let i=0;i<3;i++){const [nm,f]=steps[i];const e=document.createElement("span");e.className="mc";e.style.setProperty("--mc",MC[i]);e.textContent=nm+" ×"+fx(f);$$("sh-mults").appendChild(e);multSnd(i);
    const nv=cur*f;await reelTo(cur,nv,f>1?350:120);cur=nv;}
  // 4) 最終: ガチャ風のキラキラ。最終の点が確定し、金文字の全文が碑文に刻み込まれる
  gachaSfx();flashScreen();shakeBox();confetti(40);
  T.innerHTML='<div class="reel big bigpop" id="sh-reel" data-points="'+Math.round(g.points)+'">'+fmtPts(g.points)+'点</div><small>500 × 句ボーナス '+g.bonus+' × 連鎖 '+fx(g.chain)+' × テーマ '+g.theme+'</small>'+(d.st?'<br><small>'+d.st+'</small>':'');
  st.classList.add("carved");await sl(1000);
  skipShow=false;showRunning=false;$$("sh-skip").hidden=true;$$("sh-close").hidden=false;$$("sh-ingo").hidden=false;refreshStar();
}catch(e){if(e!==CANCEL)throw e;}
}
/* /dan6:show */
