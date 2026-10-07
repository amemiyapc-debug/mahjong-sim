"""試作HTML(prototype/hiragana_tap_prototype.html)の確認(依頼 C): スロット別の色・ちゅ代替の削除・320px幅に14牌。
  python3 dan6/test_prototype.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "game"))
from pw import sync_playwright, launch
URL = "file://" + os.path.abspath(os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html"))
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
COL = ["#E6E1EA", "#FFB8D4", "#FFD3C2", "#F0A0DC", "#BFD4FF", "#CDB0F5", "#FFF0A6"]
rgb = lambda h: "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    ok("読み込めて、エラーがない(語365・山361枚)", not errs and pg.evaluate("DICT.words.length")==365 and pg.evaluate("newDeck().length")==361, str(errs[:1]))
    # ちゅ→つ の代用の削除
    r = pg.evaluate("""()=>({a:!!findWord(DICT,['け','ちゅ','穴']), b:!!findWord(DICT,['け','っ','穴']), c:!!findWord(DICT,['け','つ','穴']),
        d:!!findWord(DICT,['ちゅ','っ','ちゅ']), e:okTile('ちゅ','つ'), f:okTile('っ','つ'), g:okTile('ぉ゛','お')})""")
    ok("ちゅは、つ・っの代わりにならない(け・ちゅ・穴 は けつ穴 にならない)", not r["a"] and not r["e"])
    ok("つ=っ の互換は残る(け・っ・穴 / け・つ・穴 = けつ穴)、ちゅっちゅ・ぉ゛=お も使える", r["b"] and r["c"] and r["d"] and r["f"] and r["g"])
    # 手牌を作る: 面子3(部位・行為・反応)+雀頭1+搭子1+ツモ牌 = 14牌
    pg.evaluate("""()=>{ reset(); let id=1000; const T=l=>({id:id++,label:l});
      const grp=(kind,name,labs)=>({k:'group',kind,name,text:name,tiles:labs.map(T)});
      items=[ grp('meld','ちんぽ',['ち','ん','ぽ']), grp('meld','くちゅっ',['く','ちゅ','っ']), grp('meld','デカぬれ♡',['デカ','ぬれ','♡']),
              grp('meld','あんあん',['あ','ん','×2']), grp('head','いく',['い','く']), ];
      tsumoId=items[items.length-1].tiles[1].id; render(); }""")
    n = pg.evaluate("flat().length"); ok("14牌を並べた(面子4・雀頭1・牌)", n == 14, str(n))
    geo = pg.evaluate("""()=>{ const t=document.querySelector('#hand .tile'), w=document.getElementById('handwrap'), h=document.getElementById('hand');
      const r=t.getBoundingClientRect(); const gs=[...document.querySelectorAll('#hand .grp')].map(g=>{const a=g.getBoundingClientRect(), l=g.querySelector('.lab').getBoundingClientRect(); return [a.left,a.right,l.left,l.right];});
      return {tw:r.width,th:r.height,wrapOver:w.scrollWidth>w.clientWidth+0.5,docOver:document.documentElement.scrollWidth>window.innerWidth,handW:h.scrollWidth,vw:window.innerWidth,gs}; }""")
    ok("牌が 21×30px", abs(geo["tw"] - 21) < 0.6 and abs(geo["th"] - 30) < 0.6, f"({geo['tw']:.1f}×{geo['th']:.1f})")
    ok("320px幅で、14牌+グループが、横にはみ出さない", not geo["wrapOver"] and not geo["docOver"], f"(手牌 {geo['handW']}px / 画面 {geo['vw']}px)")
    ok("グループのラベルが、グループ幅を超えない・隣と重ならない", all(g[2] >= g[0] - 0.5 and g[3] <= g[1] + 0.5 for g in geo["gs"]) and all(geo["gs"][i][1] <= geo["gs"][i + 1][0] + 0.5 for i in range(len(geo["gs"]) - 1)))
    cols = pg.evaluate("""()=>[...document.querySelectorAll('#hand .grp.meld')].map(g=>getComputedStyle(g.querySelector('.tile')).backgroundColor)""")
    ok("完成した面子の牌が、スロット別の色(ちんぽ=部位 #FFD3C2 / くちゅっ=音 #BFD4FF / デカぬれ♡=前置き #E6E1EA / あんあん=喘ぎ声 #FFF0A6)",
       cols == [rgb(COL[2]), rgb(COL[4]), rgb(COL[0]), rgb(COL[6])], str(cols))
    pg.evaluate("""()=>{ let id=2000; const T=l=>({id:id++,label:l}); const grp=(kind,name,labs)=>({k:'group',kind,name,text:name,tiles:labs.map(T)});
      items=[ grp('meld','ちんぽ',['ち','ん','ぽ']), grp('meld','くちゅっ',['く','ちゅ','っ']), grp('meld','デカぬれ♡',['デカ','ぬれ','♡']), grp('head','いく',['い','く']),
              {k:'tile',tile:T('き')}, {k:'tile',tile:T('エロ')}, {k:'tile',tile:T('ぉ゛')}]; tsumoId=items[items.length-1].tile.id; render(); }""")
    ok("(未完成の牌の確認用)14牌: 面子3・雀頭1・牌3", pg.evaluate("flat().length")==14 and not pg.evaluate("document.getElementById('handwrap').scrollWidth>document.getElementById('handwrap').clientWidth+0.5"))
    loose = pg.evaluate("""()=>[...document.querySelectorAll('#hand > .tile')].map(t=>getComputedStyle(t).backgroundColor)""")
    hd = pg.evaluate("""()=>getComputedStyle(document.querySelector('#hand .grp.head .tile')).backgroundColor""")
    ok("未完成の牌・雀頭は、色が付かない(白いまま)", len(set(loose)) == 1 and loose[0] == hd and loose[0] not in [rgb(c) for c in COL], loose[0])
    # 搭子のラベル重複・リストの不一致(つ=っ・ぉ゛=お は同じ牌)
    r = pg.evaluate("""()=>{ reset(); let id=3000; const T=l=>({id:id++,label:l});
      items=['エロ','お','ぉ゛','い','く','っ','つ','き','す','け','ち','ん','ろ','あ'].map(l=>({k:'tile',tile:T(l)})); tsumoId=null; render();
      const nz=x=>x==='っ'?'つ':(x==='ぉ゛'?'お':x); const H=computeHints();
      const keys=H.dazis.map(d=>d.tiles.map(t=>nz(t.label)).sort().join('|'));
      return {n:H.dazis.length, dupKeys:keys.length-new Set(keys).size, dupWaits:H.dazis.filter(d=>d.waits.some(w=>w==='っ'||w==='ぉ゛')||new Set(d.waits).size!==d.waits.length).length,
        remainOk:H.dazis.every(d=>d.remain===deck.filter(t=>d.waits.some(w=>okTile(t,w))).length), sorted:H.dazis.every((d,i,a)=>i===0||a[i-1].remain>=d.remain), top:H.dazis.slice(0,3).map(d=>d.tiles.map(t=>t.label).join('+')+' 待ち'+d.waits.join('・')+' 残'+d.remain)}; }""")
    ok("搭子の候補に、同じ牌の組(エロ+お と エロ+ぉ゛ など)の重複がない", r["n"] > 0 and r["dupKeys"] == 0, str(r["top"]))
    ok("搭子の待ち牌が、つ・っ/お・ぉ゛ で重複しない。残り枚数は、待ち牌(互換を含む)の山の枚数と一致し、多い順", r["dupWaits"] == 0 and r["remainOk"] and r["sorted"])
    # ---- dan6 の追加 ----
    html = open(os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html"), encoding="utf-8").read()
    ok("はじめての語ボーナスが、どこにもない(計算・表示・演出カード・保存データ)", "newWords" not in html and "はじめての語" not in html and "NEW</span>" not in html)
    body = "\n".join(l for l in html.split("\n") if not l.startswith("const DATA="))
    ok("画面・演出・図鑑・コメントに「翻」の文字が残っていない(検索)", "翻" not in body and "翻" not in html, "")
    ok("点の表(翻→点)・満貫制の記述が残っていない", "function pts(" not in html and "満貫" not in html and "RANK(" not in html)
    f = pg.evaluate("()=>[fmtPts(500),fmtPts(12345),fmtPts(99999),fmtPts(32e8),fmtPts(77e12),fmtPts(1e17),fmtPts(123e8)]")
    ok("大きな点の表示(万・億・兆・京)", f == ["500", "1.2万", "9.9万", "32億", "77兆", "10京", "123億"], str(f))
    r = pg.evaluate("""()=>{ localStorage.removeItem(HI_KEY); const a=updateHi(8000), b=updateHi(5000), c=updateHi(12000); return [a,b,c,loadHi()]; }""")
    ok("ハイスコアが記録され、高い点でだけ更新される", r[0]["hi"]==8000 and not r[1]["isNew"] and r[1]["hi"]==8000 and r[2]["hi"]==12000 and r[3]==12000, str(r))
    ok("研究♡の呼び名 0=無知 / 1=恥ずかしい / 2=すけべ、しきい値 4/3/2、ステージ 1-2→0 / 3-5→1 / 6〜→2、見送り 1/2/3回",
       pg.evaluate("()=>[LVN,KEN,SKIPN,[1,2,3,5,6,9].map(lvOf)]") == [["無知", "恥ずかしい", "すけべ"], [4, 3, 2], [1, 2, 3], [0, 0, 1, 1, 2, 2]])
    # ---- Python(yaku14.py・goro14.py)と、試作HTMLの照合 ----
    import random, itertools, csv, collections
    sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
    from yaku14 import Scorer
    import goro14 as G6
    S = Scorer(HERE)
    rng = random.Random(20261007)
    def mk(ws, h):
        t = []
        for i in ws: t += S.W[i]["tiles"].split("|")
        t += S.H[h]["tiles"].split("|")
        return t
    hands = [mk(rng.sample(range(len(S.W)), 4), rng.randrange(len(S.H))) for _ in range(400)]
    byslot = collections.defaultdict(list)
    for i, w in enumerate(S.W): byslot[w["part"]].append(i)
    for part, ids in byslot.items():
        if len(ids) >= 4 and part:
            for _ in range(40): hands.append(mk(rng.sample(ids, 4), rng.randrange(len(S.H))))
    py = []
    for hnd in hands:
        r_ = S.best(hnd); py.append(None if not r_ else [r_["han"], sorted(set(r_["yaku"]))])
    js = pg.evaluate("""(hands)=>hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
        for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true); if(!best||sc.total>best.total)best={total:sc.total,names:sc.items.map(x=>x.name)}; }
        return best; })""", hands)
    bad = [(i, py[i], js[i]) for i in range(len(hands)) if (py[i] is None) != (js[i] is None) or (py[i] and js[i] and py[i][0] != js[i]["total"])]
    ok(f"構造型3役(二色・ばらばら・多色)を含め、Python(yaku14.py)と試作HTMLの最大(形1+役+合体)が一致({len(hands)}手)", not bad, f"(不一致 {len(bad)}: {bad[:2]})")
    covered = set(y for p_ in py if p_ for y in p_[1])
    print("   照合した手で成立した役の種類:", len(covered), "/ 87")
    # 淫・点: 点が最大の分割(Python goro14.best_hand)と、試作HTMLの全分割の最大が、研究♡0/1/2で一致
    exp = {lv: [G6.best_hand(S, h, {"thresh": G6.KEN[lv]}) for h in hands] for lv in (0, 1, 2)}
    jsp = pg.evaluate("""(hands)=>[0,1,2].map(lv=>hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
        for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true);
          const g=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lv,sc.yin); const k=[g.points,sc.yin]; if(!best||k[0]>best.points||(k[0]===best.points&&k[1]>best.yin))best={points:g.points,yin:sc.yin,size:g.size,chainN:g.chainN,theme:g.theme}; }
        return best; }))""", hands)
    for lv in (0, 1, 2):
        badp = [(i, exp[lv][i]["points"], jsp[lv][i]["points"]) for i in range(len(hands)) if exp[lv][i]["points"] != jsp[lv][i]["points"] or exp[lv][i]["yin"] != jsp[lv][i]["yin"]]
        ok(f"研究♡{lv}(しきい値{G6.KEN[lv]}): 点・淫が、Python(goro14.py)と試作HTMLで一致({len(hands)}手)", not badp, f"(不一致 {len(badp)}: {badp[:2]})")
    # 受け入れ例: つながり(強さ4→+2)が1本、名前つき役が2淫と1淫の手 → 句ボーナス = 1+2+3 = 6 → 連鎖・テーマが無ければ 500×6 = 3,000点
    cand = None
    for _ in range(200000):
        ws = rng.sample([w["word"] for w in S.W], 4); h = rng.choice([x["head"] for x in S.H])
        x = G6.score(ws, h, {"thresh": 3}, 0)
        if x["links"] == 1 and x["linkBonus"] if False else (x["links"] == 1 and x["bonus"] == 3 and x["chain"] == 1.0 and x["theme"] == 1):
            cand = (ws, h); break
    ws, h = cand
    x3 = G6.score(ws, h, {"thresh": 3}, 3)
    j3 = pg.evaluate("([ws,h])=>{const g=g6score(ws,h,1,3);return [g.bonus,g.points];}", [ws, h])
    ok(f"受け入れ例: つながり(強さ4→+2)1本+淫3(2淫+1淫) → 句ボーナス 6 → 3,000点(Python {x3['bonus']}・{x3['points']:.0f} / 試作HTML {j3[0]}・{j3[1]})",
       x3["bonus"] == 6 and x3["points"] == 3000 and j3 == [6, 3000], str(ws) + h)
    ok("名前つき役が無い手は、淫0 → 従来(dan6)の式と同じ点(Python・試作HTML)", G6.score(ws, h, {"thresh": 3}, 0)["points"] == 500 * 3 and pg.evaluate("([ws,h])=>g6score(ws,h,1,0).points", [ws, h]) == 1500)
    # ---- ステージ制・見送り(手作りの例) ----
    SETUP = """([dk,labels])=>{ STG.stage=1; STG.game=1; STG.lives=3; STG.streak=0; STG.msg=''; newTry(); dealRandom(); items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; render(); draw(); return {choice,won:!!won,skips:STG.skips,stage:STG.stage}; }"""
    base13 = ['ち', 'ん', 'ぽ', 'ぬれ', 'ま', 'ん', 'ぱ', 'こ', '×2', 'い', 'く', 'あ', 'ん']      # ちんぽ・ぬれまん・ぱこぱこ + 雀頭あん + いく(う待ち)
    st = pg.evaluate(SETUP, [['う', 'う', 'う'], base13])
    ok("見送りの選択: アガリ形になると「アガる/見送る」が出る(研究♡0=見送り1回。まだアガリ画面は出ない)", st["choice"] and not st["won"] and st["skips"] == 1, str(st))
    ok("選択中の画面に ボタン「アガる」「見送る(残り1回)」と、いまの点が出る", pg.evaluate("()=>{const t=document.getElementById('actions').textContent;return t.includes('アガる')&&t.includes('見送る(残り1回)')&&t.includes('点');}"))
    # 見送り→再アガリ: 「う」を捨て、次の「う」でまたアガる(見送り回数は0なので、そのままアガリ)
    pg.evaluate("()=>{ act('miokuri'); }")
    r = pg.evaluate("()=>({skipMode, n:flat().length, skips:STG.skips, skipCount, choice, msg})")
    ok("見送る→手牌が14枚のままほどけて、捨て牌の選択になる(見送り残り0)", r["skipMode"] and r["n"] == 14 and r["skips"] == 0 and r["skipCount"] == 1 and not r["choice"], str(r))
    pg.evaluate("()=>{ const t=flat().find(x=>x.label==='う'); sel=[t.id]; act('discard'); }")
    pg.wait_for_timeout(300)
    r = pg.evaluate("()=>({won:!!won, data:!!(won&&won.data), st:won&&won.data&&won.data.st, pts:won&&won.data&&won.data.gs.points, stage:STG.stage, skipCount})")
    ok("見送り→再アガリ: 次のツモ(う)でまたアガリ。点が計算され、ステージが更新される", r["won"] and r["data"] and r["pts"] >= 500 and r["skipCount"] == 1, str(r))
    # 見送り→流局→ノーテン扱い
    st = pg.evaluate(SETUP, [['う'] + ['ほ'] * 20, base13])
    pg.evaluate("()=>{ act('miokuri'); const t=flat().find(x=>x.label==='う'); sel=[t.id]; act('discard'); for(let i=0;i<40&&!over;i++){ const t=tileById(tsumoId); if(!t)break; sel=[t.id]; act('discard'); } }")
    r = pg.evaluate("()=>({over, won:!!won, msg:STG.msg, game:STG.game, streak:STG.streak, draws, html:document.getElementById('win').innerHTML})")
    ok("見送り→流局: ノーテン扱い(0点・1ゲーム消費・連続テンパイはリセット)", r["over"] and not r["won"] and "ノーテン扱い" in r["msg"] and r["game"] == 2 and r["streak"] == 0 and "ノーテン扱い" in r["html"], str(r)[:200])
    # 「アガる」を選ぶ(つながりのある手: ぬれくり・まんこ・見せべろ・うしろ+あっ。り待ち)
    link13 = ['ぬれ', 'く', 'ま', 'ん', 'こ', '見せ', 'べ', 'ろ', 'う', 'し', 'ろ', 'あ', 'っ']
    st = pg.evaluate(SETUP, [['り'], link13])
    ok("つながりのある手でも、アガリ形で選択が出る(見送り1回)", st["choice"] and st["skips"] == 1, str(st))
    pg.evaluate("()=>act('agaru')"); pg.wait_for_timeout(300)
    r = pg.evaluate("()=>({won:!!won, st:won&&won.data&&won.data.st, game:STG.game, stage:STG.stage, size:won&&won.data&&won.data.gs.size, pts:won&&won.data&&won.data.gs.points})")
    clear = r["size"] is not None and r["size"] >= 2
    ok("アガる: アガリ画面が出て、条件(句=2語以上つながる)の判定とステージの更新が一致する", r["won"] and r["pts"] >= 500 and (("クリア" in r["st"]) == clear) and (r["stage"] == (2 if clear else 1)), str(r))
    # 見送れない: ツモ上限(残りツモ0)・練習配牌
    st = pg.evaluate("""()=>{ dealRandom(); items=%s.map(l=>({k:'tile',tile:mk(l)})); deck=['う']; draws=LMAX-0; won=null; over=false; choice=false; render(); draw(); return {choice,over,won:!!won}; }""" % str(base13).replace("'", '"'))
    ok("ツモ上限(残りのツモ0)では、そもそもツモできず流局(見送りは選べない)", st["over"] and not st["choice"], str(st))
    st = pg.evaluate("""()=>{ dealPractice(); items=%s.map(l=>({k:'tile',tile:mk(l)})); deck=['う']; draws=0; won=null; over=false; choice=false; render(); draw(); return {choice,won:!!won,practice}; }""" % str(base13).replace("'", '"'))
    ok("練習配牌では見送りの選択は出ない(ステージ制の対象外)", st["won"] and not st["choice"] and st["practice"], str(st))
    # 研究♡が上がったときの表示(ステージ2クリア→3で 0→1)
    r = pg.evaluate("""()=>{ dealRandom(); STG.stage=2; STG.game=1; STG.lives=3; newTry(); const gs={size:5,themeK:3,composite:[]}; const m=commitWin(gs); return {stage:STG.stage,news:STG.news,bar:stageBarHTML()}; }""")
    ok("研究♡が上がる(無知→恥ずかしい): 「新しい語呂が見えるようになった」が表示される", r["stage"] == 3 and "新しい語呂が見えるようになった" in r["news"] and "恥ずかしい" in r["bar"] and "新しい語呂が見えるようになった" in r["bar"], r["news"])
    pg.screenshot(path="/tmp/proto_320.png")
    b.close()
print("エラー:", errs or "なし"); print("すべてOK" if all(res) and not errs else "失敗")
sys.exit(0 if all(res) and not errs else 1)
