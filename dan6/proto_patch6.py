"""試作HTMLへの追加(20261010-1925 作業4): B 1周の本当の解読点の合計・C 見本の仕込み・D 1周目のステージ条件(案A。設定ファイル)・F プレイの記録(JSON)。
make_prototype.py から apply(s)。適用済み(/* dan6:f */)なら飛ばす。設定は data/*.csv(make_prototype.py が DATA.CFG として渡す)。"""

RUNJS = r'''// ===== 周回の記録(20261010-1925 B): 周回数・1周のゲーム数・1周の本当の解読点の合計(モザイク前) =====
const RUN_KEY="hm-proto-run";let RUN={lap:1,games:0,real:0};
try{const r=JSON.parse(localStorage.getItem(RUN_KEY)||"null");if(r&&r.lap>=1)RUN=Object.assign(RUN,r);}catch(e){}
function saveRun(){try{localStorage.setItem(RUN_KEY,JSON.stringify(RUN));}catch(e){}}
try{if(!new URLSearchParams(location.search).get("lap"))LAP=RUN.lap;}catch(e){}
function runSetLap(l){RUN.lap=l;RUN.games=0;RUN.real=0;saveRun();}
// 見本の仕込み(C): 1周目(SAMPLE.lapMax まで)の最初の1ゲームの配牌に、見本の語の牌を含める。data/sample_seed.csv
function sampleLabels(){const S=CFG.SAMPLE;if(!S||!S.on||LAP>S.lapMax||RUN.games>0)return null;const out=[];
  S.words.forEach(n=>{const w=DICT.words.find(x=>x.name===n||x.name.split("・").includes(n));if(w)w.tiles.forEach(t=>out.push(t));});return out.length?out:null;}
// ===== プレイの記録(F): ゲームごとに、配牌・ツモと捨て牌・各手の時間・結果・句と縁・解読点(モザイク前)。JSONで書き出す =====
const PL_KEY="hm-proto-playlog";let PLAYLOG={v:1,games:[]},PLG=null;
try{const r=JSON.parse(localStorage.getItem(PL_KEY)||"null");if(r&&r.games)PLAYLOG=r;}catch(e){}
function savePL(){try{PLAYLOG.games=PLAYLOG.games.slice(-60);localStorage.setItem(PL_KEY,JSON.stringify(PLAYLOG));}catch(e){}}
function logStart(deal,sample){PLG={no:PLAYLOG.games.length+1,lap:LAP,lv:lvOf(0),stage:STG.stage,game:STG.game,sample:!!sample,t0:Date.now(),deal:deal.slice(),events:[],result:null};PLAYLOG.games.push(PLG);}
function logEv(type,o){if(PLG&&!PLG.result)PLG.events.push(Object.assign({t:Date.now()-PLG.t0,type},o||{}));}
function logResult(kind,o){if(PLG&&!PLG.result){PLG.result=Object.assign({kind,ms:Date.now()-PLG.t0},o||{});savePL();}}
window.exportPlaylog=()=>JSON.stringify(PLAYLOG,null,1);
function downloadPlaylog(){const b=new Blob([exportPlaylog()],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="hm-playlog.json";document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500);}
'''


def apply(s):
    if "/* dan6:f */" in s:
        return s

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6f パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    # 状態(STG の直後)
    sub1("let DEFER=true,deck=[]", RUNJS + "let DEFER=true,deck=[]")
    # 周回を変えたとき
    sub1('function setLap(v){LAP=+v;newTry();', 'function setLap(v){LAP=+v;runSetLap(LAP);newTry();')
    # 配牌: 見本の仕込み・記録の開始・1周のゲーム数
    sub1('function dealRandom(){practice=false;STG.news="";deck=newDeck();items=deck.splice(0,13).map(l=>({k:"tile",tile:mk(l)}));reset();autoDraw();}',
         'function dealRandom(){practice=false;STG.news="";deck=newDeck();const smp=sampleLabels();let labs;\n'
         '  if(smp){smp.forEach(removeFromDeck);labs=shuffle(smp.concat(deck.splice(0,13-smp.length)));}else labs=deck.splice(0,13);\n'
         '  items=labs.map(l=>({k:"tile",tile:mk(l)}));RUN.games++;saveRun();logStart(labs,!!smp);reset();autoDraw();}')
    # 記録: ツモ・捨て牌・組み
    sub1('const t=mk(l);items.push({k:"tile",tile:t});tsumoId=t.id;draws++;', 'const t=mk(l);items.push({k:"tile",tile:t});tsumoId=t.id;draws++;logEv("draw",{tile:l});')
    sub1('skipMode=false;const id=sel[0];const tl=tileById(id);', 'const wasSkip=skipMode;skipMode=false;const id=sel[0];const tl=tileById(id);logEv("discard",{tile:tl.label,tsumogiri:id===tsumoId,afterSkip:wasSkip});')
    sub1("function formGroup(kind,tiles,text,name){", 'function formGroup(kind,tiles,text,name){logEv("group",{kind,text:String(text),tiles:tiles.map(t=>t.label)});')
    sub1('function ungroup(idx){', 'function ungroup(idx){logEv("ungroup",{});')
    # 記録: 結果。流局(onOver)・和了(evalWin)
    sub1('m="ノーテン(1ゲーム消費)"+consumeGame();}STG.msg=m;}', 'm="ノーテン(1ゲーム消費)"+consumeGame();}STG.msg=m;logResult(/テンパイ流局/.test(m)?"tenpai":"nowin",{msg:m});}')
    sub1("ura,total,gs,gsReal:", "runReal:(RUN.real+=(lvNow===0?g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,1,total):gs).points,saveRun(),RUN.real),ura,total,gs,gsReal:")
    sub1("  return {own:{ws,hd,sc:own,names:melds.map(g=>g.name),melds:reads,head:headRead},",
         '  logResult("win",{sentence,lv:lvNow,points:gs.points,real:(lvNow===0?g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,1,total):gs).points,yin:total,en:gs.linkFull,pairs:gs.pairs.map(x=>[x[0],x[1],x[2]]),chain:gs.chainFull,theme:gs.themeFull,kept:won?won.kept:null,user:won?won.user:null,rearr:won?won.rearr:""});\n'
         "  return {own:{ws,hd,sc:own,names:melds.map(g=>g.name),melds:reads,head:headRead},")
    # 書き出しボタン
    sub1('<button class="b" id="b-show">演出: ON</button>', '<button class="b" id="b-show">演出: ON</button>\n <button class="b" id="b-log">記録を書き出す</button>')
    sub1('$$("b-show").onclick=', '$$("b-log").onclick=()=>{downloadPlaylog();};\n$$("b-show").onclick=')
    s = s.replace("/* dan6:e */", "/* dan6:e *//* dan6:f */", 1)
    return s
