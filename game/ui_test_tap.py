"""タップ操作・自動ツモ・アガリ・ヒントの、ブラウザ(playwright・390px幅)での受け入れテスト(UI_SPEC_tap.md §6 の1〜7)。
  python3 ui_test_tap.py            # 先に python3 make_data.py && python3 build.py
"""
import json, random, sys, time
from pw import sync_playwright, launch, HTML
res = []; errs = []
def close_modals(pg):
    for _ in range(4):
        if pg.is_visible('#modal') and pg.locator('#card button[data-i]').count(): pg.click("#card button[data-i='0']"); pg.wait_for_timeout(30)
def ok(n, c, extra=""):
    res.append((n, bool(c))); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))

with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 390, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(200)
    pg.click("#modal button[data-i='0']"); pg.wait_for_timeout(100)
    W = lambda w: pg.evaluate("(w)=>__HM.G.W[__HM.G.idx[w]].tiles", w)
    Hh = lambda h: pg.evaluate("(h)=>__HM.G.H[__HM.G.hidx[h]].tiles", h)
    def setup(tiles, drawn=None):
        pg.evaluate("([t,d])=>__HM.setHand(t,d)", [tiles, drawn])
    def tap(tile, nth=0):   # 組んでいない牌のうち、その字の牌をタップ
        pg.locator(f"#hand > .tile[aria-label='{tile}']").nth(nth).click()
    def labels():
        return pg.eval_on_selector_all("#hand .grp", "els=>els.map(e=>({kind:e.classList[1],label:e.querySelector('.gl').textContent,tiles:[...e.querySelectorAll('.tile')].map(t=>t.getAttribute('aria-label'))}))")
    base = W("ちんぽ") + W("見せまん") + W("エロおす")      # 9枚
    # ---- 受け入れテスト1: ぽ→ち→ん ----
    setup(["ぽ", "ち", "ん", "く", "め", "あ", "お", "ろ", "さ", "い", "け", "り", "う"], "か")
    for t in ("ぽ", "ち", "ん"): tap(t)
    g = labels()
    ok("1. ぽ→ち→ん の順にタップ → 面子「ちんぽ」", len(g) == 1 and g[0]["kind"] == "meld" and g[0]["label"] == "ちんぽ")
    ok("1. 中の並びは ち・ん・ぽ", g and g[0]["tiles"] == ["ち", "ん", "ぽ"])
    # 半枚ぶん前(上)にずれている
    r = pg.evaluate("""()=>{const g=document.querySelector('#hand .grp .tile').getBoundingClientRect(), f=document.querySelector('#hand > .tile').getBoundingClientRect(); return [f.bottom-g.bottom, g.height];}""")
    ok("1. 組んだ牌は、牌半枚ぶん前(上)にずれる", abs(r[0] - r[1] * 0.5) < r[1] * 0.12, f"(ずれ {r[0]:.1f}px / 牌の高さ {r[1]:.1f}px)")
    # ---- 受け入れテスト2: 2枚で雀頭/搭子、解除、13枚で捨てられない ----
    tap("い"); tap("く")
    ok("2. 2枚: [雀頭にする]が押せる(いく)", pg.is_enabled("[data-act='mkhead']"))
    pg.click("[data-act='mkhead']"); g = labels()
    ok("2. 雀頭が組める", any(x["kind"] == "head" and x["label"] == "いく" for x in g))
    setup(["エロ", "す", "い", "く", "ち", "ん", "ぽ", "め", "あ", "お", "ろ", "さ", "け"], None)
    tap("エロ"); tap("す")
    ok("2. 2枚: [搭子にする]が押せる(エロ+す)", pg.is_enabled("[data-act='mktatsu']"))
    pg.click("[data-act='mktatsu']"); g = labels()
    ok("2. 搭子が組める。ラベルは「搭子」だけ", len(g) == 1 and g[0]["kind"] == "tatsu" and g[0]["label"] == "搭子")
    pg.locator("#hand .grp .tile").first.click()
    ok("2. 組んだ牌のタップで解除", len(labels()) == 0)
    tap("い"); ok("2. 13枚では捨てられない(捨てるボタンが押せない)", pg.is_disabled("#bDiscard") and pg.locator("#hand > .tile").count() == 13)
    pg.evaluate("__HM.setHand(__HM.strs().slice(0,13),'か')"); tap("い"); ok("2. 14枚なら捨てられる", pg.is_enabled("#bDiscard"))
    # 組めない3枚
    pg.evaluate("__HM.setHand(['い','く','め','あ','お','ろ','さ','け','り','う','か','き','す'],'こ')")
    tap("い"); tap("め"); tap("こ"); ok("2. 語にならない3枚 → 「語になりません」", "語になりません" in pg.inner_text("#msg") and len(labels()) == 0)
    # ---- 受け入れテスト3: 自動ツモ・上限で流局 ----
    pg.evaluate("__HM.newRun()"); pg.wait_for_timeout(50)
    n0 = pg.evaluate("__HM.game.tiles.length"); d0 = pg.evaluate("__HM.game.draws")
    ok("3. 配牌のあとに自動でツモ(14枚・ツモ1回)", n0 == 14 and d0 == 1)
    ok("3. ツモボタンはない", pg.locator("#bDraw").count() == 0)
    first = pg.locator("#hand > .tile").first; first.click(); pg.click("#bDiscard"); pg.wait_for_timeout(30)
    ok("3. 捨てると、自動でツモして14枚に戻る", pg.evaluate("__HM.game.tiles.length") == 14 and pg.evaluate("__HM.game.draws") == 2)
    L = pg.evaluate("__HM.S.L"); title = None
    for k in range(L):
        if pg.is_visible("#modal"): break
        pg.locator("#hand > .tile").first.click(); pg.click("#bDiscard"); pg.wait_for_timeout(10)
    title = pg.inner_text("#card h2") if pg.is_visible("#modal") else None
    ok("3. ツモ上限を使い切ると流局(既存の処理)", title in ("テンパイ流局", "ノーテン"), f"({title})")
    pg.click("#card button[data-i='0']")
    # ---- 受け入れテスト7: 390px幅でラベルが重ならない ----
    pg.evaluate("__HM.newRun()"); 
    hand = ["ま", "ん", "穴", "デカ", "ぬれ", "♡", "ち", "ん", "舐め", "エロ", "す", "い", "く"]
    setup(hand, "き")
    def build(ts):
        for t in ts: tap(t)
    build(["ま", "ん", "穴"]); build(["デカ", "ぬれ", "♡"]); build(["ち", "ん", "舐め"]); tap("い"); tap("く"); pg.click("[data-act='mkhead']"); tap("エロ"); tap("す"); pg.click("[data-act='mktatsu']")
    g = labels()
    ok("7. 面子3・雀頭1・搭子1 が組める", sorted(x["kind"] for x in g) == ["head", "meld", "meld", "meld", "tatsu"], str([x["label"] for x in g]))
    geo = pg.evaluate("""()=>{
      const out={groups:[],overflow:document.documentElement.scrollWidth>window.innerWidth, hand:null};
      const gs=[...document.querySelectorAll('#hand .grp')];
      gs.forEach(g=>{ const r=g.getBoundingClientRect(), l=g.querySelector('.gl'), lr=l.getBoundingClientRect(); out.groups.push({l:r.left,r:r.right,ll:lr.left,lr:lr.right,sw:l.scrollWidth,cw:l.clientWidth}); });
      const h=document.getElementById('hand'); out.hand={sw:h.scrollWidth,cw:h.clientWidth}; out.tw=document.querySelector('#hand .tile').getBoundingClientRect().width; return out; }""")
    inside = all(x["ll"] >= x["l"] - 0.5 and x["lr"] <= x["r"] + 0.5 for x in geo["groups"])
    no_overlap = all(geo["groups"][i]["r"] <= geo["groups"][i + 1]["l"] + 0.5 for i in range(len(geo["groups"]) - 1))
    ok("7. 390px幅: ラベルが、グループ幅を超えない", inside)
    ok("7. 390px幅: グループ(ラベル)が、隣と重ならない", no_overlap)
    ok("7. 390px幅: 14牌+グループ+ツモ牌が、横にはみ出さない", not geo["overflow"] and geo["hand"]["sw"] <= geo["hand"]["cw"] + 1, f"(牌の幅 {geo['tw']:.1f}px)")
    pg.screenshot(path="/tmp/ui_tap_groups.png")
    # ---- 受け入れテスト6: ヒントOFF/ON ----
    ok("6. ヒントOFF: 役ナビ・完成ボタン・橙色が出ない", pg.locator("#navSec").count() == 0 and pg.locator("#compBar button").count() == 0 and pg.locator("#hand .tile.comp").count() == 0)
    pg.click("#bHint"); pg.wait_for_timeout(50)
    ok("6. ヒントON: 役ナビ・一覧が出る", pg.locator("#navSec").count() == 1 and pg.locator("#candSec").count() == 1)
    ok("6. ヒントON: 完成牌(き=橙色)と、完成ボタンが出る", pg.locator("#hand > .tile.comp[aria-label='き']").count() == 1 and pg.locator("#compBar button").count() >= 1, pg.inner_text("#compBar")[:60].replace("\n", " "))
    pg.screenshot(path="/tmp/ui_tap_hint.png", full_page=True)
    # 完成ボタン: き で エロすき
    pg.click("#compBar button >> nth=0"); pg.wait_for_timeout(30); g = labels()
    ok("6. 完成ボタンで、搭子+牌が面子になる(エロすき)", sum(1 for x in g if x["kind"] == "meld") == 4 and any(x["label"] == "エロすき" for x in g), str([x["label"] for x in g]))
    # ---- 受け入れテスト5(19通り)・4(アガリ) ----
    nparts = pg.evaluate("__HM.G.allPartitions(__HM.strs()).length")
    ok("5. この14牌の分け方は19通り", nparts == 19, f"({nparts})")
    ok("4. 14枚そろえば、アガれる(組んでいなくても)", pg.is_enabled("#bWin"))
    pg.click("#bWin"); pg.wait_for_timeout(300); txt = pg.inner_text("#card")
    ok("5. 4つの面子と雀頭がそのまま残る(5/5・エロすき)", "5/5" in txt and "エロすき" in txt and "まん穴" in txt and "ちん舐め" in txt and "いく" in txt, txt.replace("\n", " ")[:160])
    ok("4. アガリ画面: 合計翻・点・役・分け方の数", "翻 =" in txt and "通りの分け方" in txt)
    pg.screenshot(path="/tmp/ui_tap_win.png")
    pg.click("#card button[data-i='0']")
    if pg.is_visible("#modal"): pg.click("#card button[data-i='0']")
    # ---- 受け入れテスト4: 組んでいなくてもアガリ。組んだ面子が残る ----
    pg.evaluate("__HM.newRun()")
    t14 = W("ちんぽ") + W("見せまん") + W("エロおす") + W("デカぱい") + Hh("あん")
    random.Random(3).shuffle(t14); setup(t14[:13], t14[13])
    ok("4. 組まなくてもアガれる(アガるが押せる)", pg.is_enabled("#bWin"))
    for t in W("ちんぽ"): tap(t)
    ok("4. 手で組んだ面子(ちんぽ)が組める", any(x["label"] == "ちんぽ" for x in labels()))
    pg.click("#bWin"); pg.wait_for_timeout(300); txt = pg.inner_text("#card")
    ok("4. アガリ画面に、手で組んだ面子が残る(ちんぽ・1/5以上)", "ちんぽ" in txt and ("1/5" in txt or "2/5" in txt or "3/5" in txt or "4/5" in txt or "5/5" in txt), txt.replace("\n", " ")[:120])
    pg.click("#card button[data-i='0']")
    if pg.is_visible("#modal"): pg.click("#card button[data-i='0']")
    # ---- 受け入れテスト6(続き): ⓘ・惜しかった役(アガリ/流局)。ヒントON/OFF ----
    pg.evaluate("__HM.newRun()"); pg.evaluate("__HM.hint=true")
    t14 = W("こうび") + W("ちんぽ") + W("見せまん") + W("デカぱい") + Hh("あん")
    setup(t14[:13], t14[13])
    pg.locator("#candSec button.info").first.click(); pg.wait_for_timeout(30)
    ok("6. ⓘで、その語が関わる役(組むと成立/あと1語で成立/ほかに関わる役)が出る", pg.locator("#infoBox").count()==1 and "組むと成立" in pg.inner_text("#infoBox") and "あと1語で成立" in pg.inner_text("#infoBox") and "ほかに関わる役" in pg.inner_text("#infoBox"))
    ok("6. 面子の候補に「▸役名」が付く", pg.locator("#candSec .nav").count() >= 1, pg.locator("#candSec .nav").first.inner_text())
    pg.click("#bWin"); pg.wait_for_timeout(400); txt = pg.inner_text("#card")
    ok("6. ヒントON: アガリ画面に「惜しかった役」(4語のうち1語を替えれば成立)が出る", "惜しかった役" in txt and "→" in txt, txt[txt.find("惜しかった役"):][:70].replace("\n"," "))
    close_modals(pg)
    pg.evaluate("__HM.newRun()"); pg.evaluate("__HM.hint=false"); setup(t14[:13], t14[13]); pg.click("#bWin"); pg.wait_for_timeout(300)
    ok("6. ヒントOFF: アガリ画面に「惜しかった役」が出ない", "惜しかった役" not in pg.inner_text("#card"))
    close_modals(pg)
    pg.evaluate("__HM.newRun()"); pg.evaluate("__HM.hint=true"); pg.evaluate("__HM.game.draws=__HM.S.L")
    setup(["ち","ん","ぽ","見せ","ま","ん","デカ","ぱ","い","か","さ","ろ","ぞ"],"ど"); pg.locator("#hand > .tile[aria-label='ど']").click(); pg.click("#bDiscard"); pg.wait_for_timeout(200)
    t = pg.inner_text("#card h2") if pg.is_visible("#modal") else ""
    ok("6. ヒントON: 流局画面に「惜しかった役(あと1語で成立)」が出る", t in ("テンパイ流局","ノーテン") and "あと1語で成立" in pg.inner_text("#card"), t)
    close_modals(pg)
    pg.evaluate("__HM.hint=false")
    # ---- 性能(PC・ヒントON): 1操作の処理時間 ----
    close_modals(pg)
    pg.evaluate("__HM.hint=true")
    worst = pg.evaluate("""()=>{ let m={hint:0,render:0,op:0}; const H=__HM;
      for(let n=0;n<60;n++){ H.newGame(); const g=H.game;
        // 組む → 解除 → 整理 を繰り返して、ヒントを再計算
        for(let k=0;k<4;k++){ const U=g.tiles.filter(x=>!x.g); const t0=performance.now(); H.onTile(U[0].id); H.onTile(U[1].id); H.onTile(U[2].id); const dt=performance.now()-t0; m.op=Math.max(m.op,dt); m.hint=Math.max(m.hint,H.perf.hint); m.render=Math.max(m.render,H.perf.render); }
        const t1=performance.now(); H.organize(); m.op=Math.max(m.op,performance.now()-t1); }
      return m; }""")
    ok("性能: ヒントONの1操作(3タップ・再計算+描画)が100ms以内", worst["op"] < 100, f"(最大 {worst['op']:.0f}ms / ヒント再計算 最大 {worst['hint']:.0f}ms / 描画 最大 {worst['render']:.0f}ms)")
    # ⓘの処理時間
    inf = pg.evaluate("""()=>{ const H=__HM; H.newGame(); const g=H.game; const hv=H.computeHints(); let m=0; for(const c of hv.cands.slice(0,5)){ const t0=performance.now(); H.G.gainByNext([],null,c.w); H.G.gainBy([],null,c.w); H.G.relatedYaku(c.w); m=Math.max(m,performance.now()-t0);} return m; }""")
    print(f"   ⓘ(関わる役)の計算: 最大 {inf:.0f}ms")
    b.close()
bad = [n for n, c in res if not c]
print("エラー:", errs or "なし")
print("すべてOK" if not bad and not errs else f"失敗 {len(bad)}: {bad}")
sys.exit(1 if bad or errs else 0)
