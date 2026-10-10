"""作業4(20261010-1925)の確認: B 1周の本当の解読点の合計 / C 見本の仕込み / D 1周目のステージ条件(案A・設定) / F プレイの記録(JSON・要約)。画面を操作して確認する。 python3 dan6/test_work4.py"""
import os, sys, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "game")); sys.path.insert(0, HERE)
from pw import sync_playwright, launch
import goro14 as G
URL = "file://" + os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
with sync_playwright() as p:
    b = launch(p); ctx = b.new_context(viewport={"width": 320, "height": 800}, accept_downloads=True); pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.goto(URL); pg.wait_for_timeout(300)
    # C 見本の仕込み
    smp = pg.evaluate("()=>CFG.SAMPLE")
    ok("設定(data/sample_seed.csv): 仕込みオン・語 ちんぽ|まんこ・1周目だけ", smp == {"on": True, "words": ["ちんぽ", "まんこ"], "lapMax": 1}, str(smp))
    cnt = 0
    for i in range(30):
        pg.evaluate("()=>{LAP=1;RUN.games=0;dealRandom();}")
        h = pg.evaluate("()=>flat().map(t=>t.label)")
        need = ["ち", "ん", "ぽ", "ま", "ん", "こ"]; hh = list(h)
        okh = True
        for t in need:
            if t in hh: hh.remove(t)
            else: okh = False
        cnt += okh
    ok("1周目の最初の1ゲームの配牌(13牌+ツモ)に、ちんぽ・まんこの牌(ち・ん・ぽ・ま・ん・こ)が必ず入る(30回)", cnt == 30, f"{cnt}/30")
    two = pg.evaluate("()=>{LAP=1;RUN.games=0;dealRandom();RUN.games=1;return sampleLabels();}")
    lap2 = pg.evaluate("()=>{LAP=2;RUN.games=0;const r=sampleLabels();LAP=1;return r;}")
    ok("2ゲーム目・2周目は仕込まない", two is None and lap2 is None)
    off = pg.evaluate("()=>{CFG.SAMPLE.on=false;LAP=1;RUN.games=0;const r=sampleLabels();CFG.SAMPLE.on=true;return r;}")
    ok("設定でオフにすると仕込まない", off is None)
    # D 案A
    r = pg.evaluate("()=>[1,2,3,4].map(winsNeeded)"); ok("1周目のステージ条件(案A): 1回以上 / 2回以上 / 3回すべて(設定 data/stage_wins_lap1.csv と同じ)", r == [1, 2, 3, 3] == [G.wins_needed(i) for i in (1, 2, 3, 4)], str(r))
    ok("積み点は、試作に無い(廃止)", "積み点" not in open(os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html"), encoding="utf-8").read())
    # B と F: 1ゲーム遊ぶ(手を組み、和了)
    pg.evaluate("()=>{localStorage.clear();}"); pg.reload(); pg.wait_for_timeout(300)
    lab = ['ち', 'ん', 'ぽ', 'ま', 'ん', 'こ', 'ぬれ', 'く', 'り', 'あ', 'ん', 'い', 'く']
    # ちんぽ・まんこ・ぬれくり・(いく)+あん。いくう で和了
    pg.evaluate("""([dk,labels])=>{ LAP=1; runSetLap(1); STG.stage=1; STG.game=1; STG.lives=3; newTry(); dealRandom(); items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; tsumoId=null; sel=[]; render(); }""", [["う"], lab])
    for grp in (["ち", "ん", "ぽ"], ["ま", "ん", "こ"], ["ぬれ", "く", "り"]):
        for l in grp:
            i = pg.evaluate("""(l)=>{const t=[...document.querySelectorAll('#hand > .tile:not(.sel)')].find(x=>x.textContent===l);return t?+t.dataset.id:null;}""", l); pg.click(f'#hand > .tile[data-id="{i}"]')
    pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
    if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]')
    pg.wait_for_timeout(800)
    d = pg.evaluate("()=>({real:won.data.gsReal.points,pts:won.data.gs.points,run:RUN.real,lv:won.data.lv})")
    ok("B: 1周目の和了は500解読点で、本当の解読点(研究♡1の解禁表)の合計が、周回の記録(RUN.real)に溜まる", d["pts"] == 500 and d["real"] > 500 and d["run"] == d["real"], str(d))
    stored = pg.evaluate("()=>JSON.parse(localStorage.getItem('hm-proto-run'))")
    ok("B: 記録は保存される(再読み込みしても残る)", stored["real"] == d["real"] and stored["lap"] == 1, str(stored))
    pl = json.loads(pg.evaluate("()=>exportPlaylog()")); g0 = pl["games"][-1]
    ok("F: ゲームの記録に、配牌・ツモ・組み・結果(句と縁・解読点)がある", g0["deal"] and any(e["type"] == "draw" for e in g0["events"]) and any(e["type"] == "group" for e in g0["events"]) and g0["result"]["kind"] == "win" and g0["result"]["points"] == 500 and g0["result"]["real"] == d["real"] and "pairs" in g0["result"] and "en" in g0["result"], str({k: g0["result"].get(k) for k in ("kind", "points", "real", "en")}))
    ok("F: 各手の時間(イベントごとの t)と、ゲーム全体の時間(result.ms)が入っている", all("t" in e for e in g0["events"]) and g0["result"]["ms"] > 0)
    pg.evaluate("()=>cancelShow()")
    with pg.expect_download() as dl: pg.click("#b-log")
    path = dl.value.path(); dj = json.load(open(path, encoding="utf-8"))
    ok("F: ボタン「記録を書き出す」で JSON が書き出せる", len(dj["games"]) >= 1)
    tmp = os.path.join(tempfile.mkdtemp(), "log.json"); json.dump(dj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    out = subprocess.run([sys.executable, os.path.join(HERE, "summarize_playlog.py"), tmp], capture_output=True, text=True)
    ok("F: 要約スクリプトが、時間と、判断が結果に効かなかった場面を出す", out.returncode == 0 and "1手(ツモ→次の操作)の時間" in out.stdout and "判断が結果に効かなかった場面" in out.stdout, out.stdout[-300:] + out.stderr[-200:])
    print(out.stdout)
    ok("ページエラーがない", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
