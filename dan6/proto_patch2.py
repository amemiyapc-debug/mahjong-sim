"""試作HTMLへの dan6 追加分(20261007-1040・1105): 翻→淫、点の式(句ボーナス+名前つき役の淫)、語呂度エンジン、研究♡0/1/2、ステージ制、見送り、構造型3役の判定。
make_prototype.py から apply(s) で呼ばれる。何度実行しても同じ結果になる(適用済みなら飛ばす)。"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
G6JS = open(os.path.join(HERE, "proto_g6.js"), encoding="utf-8").read()


def apply(s):
    if "/* dan6:b */" in s:                       # 適用済み(「翻→淫」の置換後は、元の文字列が無いので、全部飛ばす)
        return s
    def sub1(old, new, count=1):
        nonlocal s
        if new in s and (old not in s or old in new):
            return
        assert old in s, "dan6b パッチが当たらない: " + old[:60]
        s = s.replace(old, new, count)

    def region(start, end, new):
        nonlocal s
        i0 = s.index(start)
        if new.strip() and new in s:
            return
        i1 = s.index(end, i0)
        s = s[:i0] + new + s[i1:]

    # --- 説明文 ---
    s = re.sub(r'<p class="note">.*?</p>', '<p class="note">dan6 の語365・雀頭28・山361枚で動く試作。名前つき役は「淫」、解読点 = 500 × 縁 × 連鎖 × テーマ。ステージ制(研究♡0/1/2・見送り)つき(「ランダム配牌」から)。CPUはありません。</p>', s, count=1, flags=re.S)
    # --- 点の表(翻→点)を外し、語呂度エンジンを入れる ---
    if "/* dan6:goro */" not in s:
        i0 = s.index("function pts(h){"); i1 = s.index("\n", i0) + 1
        s = s[:i0] + G6JS + "\n" + s[i1:]
    sub1("const STAGE_WORD=", "const KZ=new Set(DATA.KZ),yv=y=>KZ.has(y.name)?0:y.han;   // 飾りは0淫\nconst STAGE_WORD=")
    # --- scoreHand: 淫(名前つき役の合計。飾りは0、合体は成立した合体1つの淫) ---
    sub1("  return {items:shown,satNames,total,merges:best,actual};",
         "  const yin=shown.reduce((a,x)=>a+((x.merge||!KZ.has(x.name))?x.han:0),0);\n  return {items:shown,satNames,total,yin,merges:best,actual};")
    sub1('mods:a[2]?[...new Set(a[2].split("|"))]:[],', 'mods:a[2]?[...new Set(a[2].split("|"))]:[],modsRaw:a[2]?a[2].split("|"):[],')
    # --- 構造型3役(二色・ばらばら・多色)を、game/core.js・yaku14.py と同じ判定に(20261007-1105 で承認) ---
    def line_of(key):
        i0 = s.index('    case"' + key + '":'); return i0, s.index("\n", i0)
    for key, new in (("distinct_stems", '    case"distinct_stems":{f=(ws,hd,full)=>full&&ws.every(w=>WA[w].stem)&&new Set(ws.map(w=>WA[w].stem)).size===4;break;}'),
                     ("distinct_modifiers", '    case"distinct_modifiers":{f=(ws,hd,full)=>{if(!full||!ws.every(w=>WA[w].modsRaw.length>=1))return false;const tk=[];ws.forEach(w=>WA[w].modsRaw.forEach(m=>tk.push(m)));return new Set(tk).size===tk.length;};break;}'),
                     ("modifier_pairs", '    case"modifier_pairs":{const n=+kv.pairs;f=(ws,hd,full)=>{if(!full||!ws.every(w=>WA[w].modsRaw.length===1))return false;const c={};ws.forEach(w=>{const m=WA[w].modsRaw[0];c[m]=(c[m]||0)+1;});return Object.values(c).filter(v=>v===2).length===n;};break;}')):
        i0, i1 = line_of(key)
        s = s[:i0] + new + s[i1:]
    # --- 状態 ---
    sub1("let DEFER=true,deck=[]", "let choice=false,skipMode=false,pendingWin=null,skipCount=0,practice=true;   // 見送りの選択中・見送ったあとの捨て牌選び・見送ったか・練習配牌\n"
         "const STG={stage:1,game:1,wins:0,lives:3,skips:SKIPN[0],streak:0,news:\"\",msg:\"\"};   // ステージ制(3ゲーム/ステージ・ライフ3)\n"
         "function setLap(v){LAP=+v;newTry();STG.msg=\"周回を\"+LAP+\"周目にした(研究♡「\"+LVN[lvOf(0)]+\"」)\";try{render();}catch(e){}}\n"
         "function newTry(){STG.game=1;STG.wins=0;STG.skips=SKIPN[lvOf(STG.stage)];}\n"
         "function consumeGame(){STG.game++;if(STG.game>3){STG.lives--;if(STG.lives<=0){const st=STG.stage;STG.stage=1;STG.lives=3;newTry();return \" → ライフ0。ゲームオーバー(ステージ\"+st+\"まで)。ステージ1から\";}newTry();return \" → 3ゲーム使い切り。ライフ-1(残り\"+STG.lives+\")。ステージ\"+STG.stage+\"をやり直し\";}return \"(ゲーム \"+(STG.game-1)+\"/3 を消費)\";}\n"
         "function commitWin(gs){const c=Math.min(STG.stage,8),lv=lvOf(STG.stage);STG.streak=0;\n"
         "  if(lv===0){STG.wins++;const need=winsNeeded(STG.stage);let m=\"和了 \"+STG.wins+\"/3(このステージは\"+need+\"回以上でクリア)\";   // 1周目: 条件は和了の回数(data/stage_wins_lap1.csv)\n"
         "    if(STG.wins>=need){const done=STG.stage;STG.stage++;m+=\" → ステージ\"+done+\"クリア!\";newTry();}else m+=consumeGame();STG.msg=m;return m;}\n"
         "  const ok=g6sat(gs,c);let m=\"条件「\"+CONDN[c]+\"」を\"+(ok?\"達成!\":\"満たせなかった\");\n"
         "  if(ok){const done=STG.stage;STG.stage++;const nl=lvOf(STG.stage);m+=\" → ステージ\"+done+\"クリア!\";newTry();if(nl>lv){STG.news=\"研究♡が「\"+LVN[nl]+\"」に上がった! 新しい語呂が見えるようになった\";try{toast(STG.news);}catch(e){}}}\n"
         "  else m+=consumeGame();STG.msg=m;return m;}\n"
         "function isTenpai13(){const labs=flat().map(t=>t.label);for(const l of new Set(deck))if(allPartitions(DICT,labs.concat([l]),1).length)return true;return false;}\n"
         "function onOver(){if(practice)return;let m;if(skipCount>0){STG.streak=0;m=\"見送ったあと、完成しなかったので、ノーテン扱い(0解読点・1ゲーム消費)\"+consumeGame();}\n"
         "  else if(isTenpai13()){STG.streak++;m=\"テンパイ流局(ゲームは消費しない)\"+(STG.streak>=3?\" ・焦らしプレイ \"+STG.streak+\"連続!\":\" ・連続テンパイ \"+STG.streak);}\n"
         "  else{STG.streak=0;m=\"ノーテン(1ゲーム消費)\"+consumeGame();}STG.msg=m;}\n"
         "function stageBarHTML(){if(practice)return '<span class=\"hint\">練習配牌(ステージ制の対象外)。「ランダム配牌」でステージ制が始まります。</span>';const lv=lvOf(STG.stage),c=Math.min(STG.stage,8);\n"
         "  return '<b>ステージ'+STG.stage+'</b> ・<select id=\"lapsel\" onchange=\"setLap(this.value)\" style=\"font-size:.8rem\">'+[1,2,3,4].map(n=>'<option value=\"'+n+'\"'+(n===LAP?' selected':'')+'>'+n+'周目</option>').join('')+'</select> ・研究♡「'+LVN[lv]+'」'+(lv===0?' ・<b class=\"winct\" style=\"font-size:1.05rem\">和了 '+STG.wins+'/3</b>(あと'+Math.max(0,winsNeeded(STG.stage)-STG.wins)+'回)':'')+' ・ゲーム '+STG.game+'/3 ・ライフ '+'♥'.repeat(STG.lives)+' ・見送り 残'+STG.skips+'回<br>条件: '+(lv===0?'3ゲームのうち '+winsNeeded(STG.stage)+'回以上 和了':CONDN[c])+(STG.news?'<br><b class=\"news\">'+STG.news+'</b>':'')+(STG.msg?'<br><small>前のゲーム: '+STG.msg+'</small>':'');}\n"
         "let DEFER=true,deck=[]")
    sub1('<div id="status"></div>', '<div id="status"></div>\n <div id="stagebar" class="hint" style="margin:4px 0"></div>')
    sub1(".hint{font-size:.76rem;color:var(--sub)}", ".hint{font-size:.76rem;color:var(--sub)}.news{color:#ff6ba0}")
    # --- リセット・配牌 ---
    sub1("function reset(){cancelShow();", "function reset(){choice=false;skipMode=false;pendingWin=null;skipCount=0;cancelShow();")
    sub1("function dealRandom(){deck=newDeck();", "function dealRandom(){practice=false;STG.news=\"\";deck=newDeck();")
    sub1("function dealPractice(){\n  deck=newDeck();", "function dealPractice(){\n  practice=true;deck=newDeck();")
    # --- 操作の制限(見送りの選択中) ---
    sub1('function onTile(id){\n  if(won||over)return;', 'function onTile(id){\n  if(won||over||choice)return;')
    sub1('function act(a){\n  if(a==="discard"){', 'function act(a){\n  if(a==="agaru"){if(!choice||!pendingWin)return;const pw=pendingWin;choice=false;finalizeWin(pw.g,pw.keptN);return;}\n'
         '  if(a==="miokuri"){if(!choice||!pendingWin||STG.skips<=0||draws>=LMAX)return;const pw=pendingWin;STG.skips--;skipCount++;choice=false;pendingWin=null;skipMode=true;\n'
         '    items=pw.g.flatMap(x=>x.tiles.map(t=>({k:"tile",tile:t})));sel=[];tsumoId=null;msg="見送りました(残り"+STG.skips+"回)。捨てる牌を1枚タップして、「この牌を捨てる」を押してください。";render();return;}\n'
         '  if(choice)return;\n  if(a==="discard"){')
    sub1('const id=sel[0];const tl=tileById(id);items=items.filter', 'skipMode=false;const id=sel[0];const tl=tileById(id);items=items.filter')
    # --- 流局 ---
    sub1('if(draws>=LMAX){over=true;msg="ツモを使い切りました(流局)。";render();return;}', 'if(draws>=LMAX){over=true;msg="ツモを使い切りました(流局)。";onOver();render();return;}')
    sub1('if(!l){over=true;msg="山がありません(流局)。";render();return;}', 'if(!l){over=true;msg="山がありません(流局)。";onOver();render();return;}')
    # --- アガリ判定: 見送りの選択 ---
    sub1("function checkWin(){\n  const all=flat();if(all.length!==14||won)return;", "function checkWin(){\n  if(choice||skipMode)return;\n  const all=flat();if(all.length!==14||won)return;")
    sub1("  const keptN=sub.length+(keepHead?1:0);\n  items=g;sel=[];tsumoId=null;\n",
         "  const keptN=sub.length+(keepHead?1:0);\n"
         "  if(!practice&&STG.skips>0&&draws<LMAX){items=g;sel=[];tsumoId=null;choice=true;pendingWin={g,keptN};msg=\"\";render();return;}   // 見送りを選べる\n"
         "  finalizeWin(g,keptN);\n}\nfunction finalizeWin(g,keptN){\n  items=g;sel=[];tsumoId=null;choice=false;pendingWin=null;\n")
    # --- 画面 ---
    sub1('  $("#msg").textContent=msg;', '  $("#msg").textContent=msg;$("#stagebar").innerHTML=stageBarHTML();')
    sub1('  if(won||over){ac.innerHTML=over?', '  if(choice&&pendingWin){const pv=previewWin(pendingWin.g);ac.innerHTML=`<span class="hint">アガリです! いまの手: <b>${fmtPts(pv.points)}解読点</b>(${pv.yin}淫・つながり${STAGE_WORD[pv.size]}・条件${pv.ok?"達成":"未達"})。見送ると、1枚捨てて残りのツモで続けます。完成しなければノーテン扱い(0解読点)。</span><button class="b main" data-a="agaru">アガる</button><button class="b" data-a="miokuri">見送る(残り${STG.skips}回)</button>`;}\n'
         '  else if(won||over){ac.innerHTML=over?')
    sub1("function handKeys(){", "function previewWin(g){const ms=g.filter(x=>x.kind===\"meld\"),hg=g.find(x=>x.kind===\"head\");const ws=ms.map(x=>WI.get(x.name)),hd=HI.get(hg.name);const oho=g.flatMap(x=>x.tiles).filter(t=>t.label===\"ぉ゛\").length;\n"
         "  const sc=scoreHand(ws,hd,oho,true),lv=lvOf(STG.stage),gs=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lv,sc.yin);return {points:gs.points,yin:sc.yin,size:gs.size,ok:lv===0?(STG.wins+1>=winsNeeded(STG.stage)):g6sat(gs,Math.min(STG.stage,8))};}\nfunction handKeys(){")
    # --- evalWin: 点・淫 ---
    sub1("if(!best||sc.total>best.sc.total)best={p,ws,hd,sc};", "if(!best||sc.yin>best.sc.yin||(sc.yin===best.sc.yin&&sc.total>best.sc.total))best={p,ws,hd,sc};")
    sub1("const ura=best?Math.max(0,best.sc.total-own.total):0;", "const ura=best?Math.max(0,best.sc.yin-own.yin):0;")
    sub1("const total=own.total+ura;", "const total=own.yin+ura;   // 名前つき役の淫(裏読みを含む)\n  const lvNow=lvOf(STG.stage),gs=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lvNow,total);")
    sub1("const hiR=updateHi(pts(total));", "const hiR=updateHi(gs.points);")
    sub1("han:total,pts:pts(total),", "in:total,han:total,pts:gs.points,")
    sub1("ura,total,hi:hiR,near,", "ura,total,gs,lv:lvNow,hi:hiR,st:(practice?null:commitWin(gs)),near,")
    # --- 表示 ---
    region("function itemsHTML(sc){", "function winHTML(){", '''function itemsHTML(sc){
  if(!sc.items.length)return `<div class="sc">名前つき役なし(0翻)</div>`;
  return sc.items.map(x=>`<div class="sc">${x.merge?"合体 ":""}${x.name} <span class="han">${yv(x)}翻</span>${KZ.has(x.name)?" <small>(飾り。点には加算しない)</small>":""}${x.merge?` <small>(${x.merge.join("+")}の合体)</small>`:""}</div>`).join("");
}
''')
    region("function winHTML(){", "function overHTML(){", '''function winHTML(){
  const d=won.data;
  if(!d)return `<h2>アガリ!</h2><div class="hint">役を数えています…</div>`;
  const g=d.gs;
  let s=`<h2>アガリ! ${fmtPts(g.points)}解読点</h2><div class="hint">ハイスコア ${fmtPts(d.hi.hi)}解読点${d.hi.isNew?" ★更新!":""}</div><div class="hint">解読点 = 500 × 縁 ${g.bonus}(1 + つながり ${g.linkBonus} + 名前つき役 ${g.yin}翻) × 連鎖 ${g.chain.toFixed(g.chainN?2:0)}(連鎖${g.chainN}) × テーマ ${g.theme}(${g.themeName})。つながりは「${STAGE_WORD[g.size]}」。${LAP}周目・研究♡「${LVN[d.lv]}」(語を結ぶしきい値 ${thOf(d.lv)})。${d.lv<2?"まだ読み解けていない項目は解読点に入りません: "+(d.lv<1?"縁(つながり)・名前つき役の淫・句・":"")+"連鎖・テーマ"+(d.lv<1?"(基本点の500のみ)":"")+"。":""}</div>`;
  s+=`<div class="sc" style="margin-top:6px;font-size:1.1rem;font-weight:900">「${d.sentence}」</div><div class="ig-meta"><span class="ig-lab ${gcls(d.gl.name)}">${d.gl.name}</span>${d.gl.text}${d.linkPairs.length?" ・ しりとり成立! "+d.linkPairs.join(" "):""}</div>`;
  s+=`<div class="sh-btns" style="justify-content:flex-start;margin:6px 0"><button class="b" id="star2">☆ 傑作にする</button><button class="b" id="copy2">コピー</button></div><div class="hint">淫語集に保存しました。</div>`;
  s+=`<div style="margin-top:6px">${itemsHTML(d.own.sc)}</div>`;
  if(d.ura>0)s+=`<div class="sc">裏読みボーナス <span class="han">+${d.ura}翻</span> <small>(同じ14牌は「${d.best.p.melds.map(m=>readingOf(m.word,m.assigned).split("・")[0]).join("・")}+${d.best.p.head.name}」とも読める)</small></div>`;
  if(d.st)s+=`<div class="sc">ステージ: ${d.st}</div>`;
  if(won.kept<won.total)s+=`<div class="hint" style="margin-top:6px">手で組んだ形のうち ${won.kept}/${won.total} をそのまま使い、残りは自動で組みました。</div>`;
  if(hint&&d.near.length)s+=`<div class="miss" style="margin-top:8px"><b>惜しかった役</b>(1語を替えれば成立)<br>${d.near.slice(0,5).map(e=>e.name+"("+e.han+"翻) ← 「"+DICT.words[e.ex[0].from].name+"」を「"+DICT.words[e.ex[0].to].name+"」に").join("<br>")}</div>`;
  s+=`<div class="sh-btns" style="margin-top:8px"><button class="b" id="replay">演出をもう一度</button></div>`;
  return s;
}
''')
    sub1('let s=`<h2 style="color:var(--sub)">流局</h2><div class="hint">ツモを使い切りました。</div>`;', 'let s=`<h2 style="color:var(--sub)">流局</h2><div class="hint">ツモを使い切りました。</div>${STG.msg&&!practice?`<div class="sc">ステージ: ${STG.msg}</div>`:""}`;')
    # --- 演出 ---
    s = s.replace('const RANK=t=>t>=13?"役満!!":t>=11?"三倍満!":t>=8?"倍満!":t>=6?"跳満!":t>=5?"満貫!":"";\n', "")
    sub1("let shown=1;const total=sc.total;", "let shown=0;const total=d.total;")
    sub1("役なし<small>形の1翻のみ</small>", "名前つき役なし<small>0翻</small>")
    s = s.replace('e.innerHTML=y.name+"<small>"+y.han+"翻</small>";', 'e.innerHTML=y.name+"<small>"+yv(y)+"翻</small>"+(KZ.has(y.name)?"":"");').replace("shown+=y.han;", "shown+=yv(y);")
    region("  // 6) 合計\n", '  skipShow=false;showRunning=false;$$("sh-skip").hidden=true', '''  // 6) 合計(点)
  const T=d.total,g=d.gs;
  for(let i=shown;i<=T&&!skipShow;i++){setTotal(i);SFX.tick();await sl(60);}
  $$("sh-total").innerHTML='<span class="big bigpop" style="display:inline-block">'+fmtPts(g.points)+'解読点</span><br><small>500 × 縁 '+g.bonus+' × 連鎖 '+(g.chainN?g.chain.toFixed(2):1)+' × テーマ '+g.theme+'</small>'+(d.st?'<br><small>'+d.st+'</small>':'');
  if(T>=5||mergeItems.length||g.points>=100000){SFX.fan();flashScreen();shakeBox();confetti(40);}else SFX.jan(Math.max(1,T));
''')
    # --- 「翻」を「淫」に(DATA の行は触らない) ---
    out = []
    for ln in s.split("\n"):
        out.append(ln if ln.startswith("const DATA=") else ln.replace("翻", "淫"))
    s = "\n".join(out).replace("/* dan6:goro */", "/* dan6:goro *//* dan6:b */", 1)
    s = s.replace("名前つき役なし(0淫)", "名前つき役なし(0淫)")
    return s
