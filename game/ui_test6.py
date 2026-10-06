"""ブラウザでの確認(旧 ui_test6.py を、タップ操作の画面に合わせて書き直したもの)。ぉ゛・語の組み方・通しプレイ。
  python3 make_data.py && python3 build.py && python3 ui_test6.py
"""
from pw import sync_playwright, launch, HTML
errs=[]; res=[]
def ok(n,c): res.append((n,bool(c)))
with sync_playwright() as p:
    b=launch(p); pg=b.new_page(viewport={"width":390,"height":900})
    pg.on("pageerror",lambda e: errs.append(str(e)))
    pg.goto(HTML); pg.wait_for_timeout(200)
    pg.click("#modal button[data-i='0']"); pg.wait_for_timeout(100)
    W=lambda w: pg.evaluate("(w)=>__HM.G.W[__HM.G.idx[w]].tiles",w)
    H=lambda h: pg.evaluate("(h)=>__HM.G.H[__HM.G.hidx[h]].tiles",h)
    def setup(tiles13,drawn): pg.evaluate("([t,d])=>__HM.setHand(t,d)",[tiles13,drawn])
    # ぉ゛まめ(おまめのおをぉ゛にした手)でアガる
    t=[x if x!="お" else "ぉ゛" for x in W("おまめ")]+W("ちんぽ")+W("見せまん")+W("ちん♡")+["あ"]
    setup(t,"ん")
    ok("手牌にぉ゛の牌が出る", pg.locator("#hand .tile.k-oho").count()==1)
    ok("アガれる", pg.is_enabled("#bWin"))
    pg.evaluate("__HM.hint=true"); ok("ヒントONで、ぉ゛・ま・めの『おまめ』が面子の候補に出る", pg.locator("#candSec [data-act='meld']", has_text="おまめ").count()==1)
    pg.evaluate("__HM.hint=false")
    pg.screenshot(path="/tmp/ui6_oho.png",full_page=True)
    pg.click("#bWin"); pg.wait_for_timeout(300); txt=pg.inner_text("#card"); print(txt.replace("\n"," / ")[:220])
    ok("アガリ画面に『ぉ゛まめ』と『オホ声』が出る", "ぉ゛まめ" in txt and "オホ声" in txt)
    pg.screenshot(path="/tmp/ui6_win.png")
    pg.click("#card button[data-i='0']")
    if pg.is_visible("#modal"): pg.click("#card button[data-i='0']")
    # ぉ゛・ま・めの3枚タップ → 面子「ぉ゛まめ」(ぉ゛の牌のまま)
    setup(t,"ん")
    for x in ("ぉ゛","ま","め"): pg.locator(f"#hand > .tile[aria-label='{x}']").first.click()
    ok("3枚タップで、ぉ゛まめが組まれる(ぉ゛の牌のまま)", pg.locator("#hand .grp.meld .tile.k-oho").count()==1 and "ぉ゛まめ" in pg.inner_text("#hand .grp.meld .gl"))
    # 通して遊ぶ
    pg.evaluate("document.querySelector('#bApply').click()"); pg.wait_for_timeout(100)
    if pg.is_visible("#modal"): pg.click("#card button[data-i='0']")
    pg.click("#bHint"); steps=0; titles=[]; inv=True
    while steps<1500:
        steps+=1
        if pg.is_visible("#modal"):
            tt=pg.inner_text("#card h2"); titles.append(tt)
            if tt=="ゲームオーバー": break
            pg.click("#card button[data-i='0']"); continue
        n=pg.evaluate("__HM.strs().length")
        if n not in (13,14): inv=False
        if pg.is_enabled("#bWin"): pg.click("#bWin"); pg.wait_for_timeout(30); continue
        pg.locator("#hand > .tile").first.click()
        pg.click("#bDiscard")
    ok("ゲームオーバーまで通して動く","ゲームオーバー" in titles); ok("牌の総数がずっと13/14枚",inv)
    b.close()
for n,c in res: print(("OK  " if c else "NG  ")+n)
print("エラー:",errs or "なし")
