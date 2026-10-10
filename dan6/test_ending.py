"""エンディング(作業6)と図鑑の研究メモ(作業7)の確認(20261010-1925)。1周目のステージ3をクリアして、エンディングが流れ、モザイクなしの合計が出て、周回数が2になる。図鑑のメモがエンディング前後で切り替わる。
  python3 dan6/test_ending.py"""
import os, sys, csv, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "game")); sys.path.insert(0, HERE)
from pw import sync_playwright, launch
import goro14 as G
URL = "file://" + os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
SHOTS = os.path.join(ROOT, "results_dan6", "shots")
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
memos = {r["word"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data", "lina_memos_100.csv"), encoding="utf-8-sig"))}
H = ['ち', 'ん', 'ぽ', 'ま', 'ん', 'こ', 'ぬれ', 'く', 'り', 'い', 'く', 'う', 'あ', 'ん']
SETUP = """([dk,labels,stage,wins])=>{ LAP=1; runSetLap(1); STG.stage=stage; STG.game=1; STG.lives=3; STG.streak=0; STG.msg=''; newTry(); STG.wins=wins; dealRandom(); RUN.games=5; items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; tsumoId=null; sel=[]; cancelShow(); render(); return flat().length; }"""
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.goto(URL); pg.wait_for_timeout(300)
    # 図鑑に語を入れる(入手した語)。未入手は出ない
    seen = [w for w in list(memos)[::2]]   # 100語のうち半分(全役割にまたがる)
    pg.evaluate("(s)=>{localStorage.setItem(SEEN_KEY,JSON.stringify(s));localStorage.removeItem('hm-proto-run');}", seen); pg.reload(); pg.wait_for_timeout(300)
    # 図鑑の研究メモ(1周目)
    pg.evaluate("()=>{document.getElementById('ingo').open=true;slotOpen=2;renderIngo();}")
    html1 = pg.evaluate("()=>document.getElementById('ingobox').innerHTML"); txt1 = pg.evaluate("()=>document.getElementById('ingobox').innerText")
    got = [w for w in seen if memos[w]["slot"] == "部位"]
    ok("図鑑(1周目): 入手した部位の語に、1周目の研究メモが付く。取り消し線・訂正後は出ない", all(memos[w]["1周目の研究メモ"] in txt1 for w in got) and "<s>" not in html1 and 'class="red"' not in html1 and len(got) > 0, f"{len(got)}語")
    ok("図鑑: 未入手の語は出ない(「ちんぽ」入手済み・「あなる」など未入手の語のメモは出ない)", all(memos[w]["1周目の研究メモ"] not in txt1 for w in memos if w not in seen and memos[w]["slot"] == "部位"))
    # 1周目: ステージ3(3回すべて和了)の3回目の和了 → エンディング
    pg.evaluate(SETUP, [["ん"], H[:-1], 3, 2]); pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
    if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]')
    pg.wait_for_timeout(700)
    ok("1周目のステージ3クリアで、エンディングの予約が入る(条件: 3回すべて和了)", pg.evaluate("()=>pendingEnding") is True and pg.evaluate("()=>STG.stage") == 4)
    real = pg.evaluate("()=>RUN.real"); ok("1周目の本当の解読点の合計が記録されている", real > 500, str(real))
    # アガリ演出の最後(リザルト)まで待ち、「とじる」を押す → エンディング
    for _ in range(300):
        if pg.evaluate("()=>!showRunning") and pg.evaluate("()=>document.getElementById('show').dataset.stage")=="result": break
        pg.wait_for_timeout(100)
    pg.click("#sh-close"); t0 = pg.evaluate("()=>performance.now()"); pg.wait_for_timeout(300)
    ok("『とじる』のあと、エンディングが始まる", pg.evaluate("()=>!document.getElementById('ending').hidden"))
    seq, shots = [], {}
    for _ in range(600):
        st = pg.evaluate("()=>document.getElementById('ending').dataset.stage||null")
        if st and (not seq or seq[-1] != st):
            seq.append(st)
            pg.wait_for_timeout(700); pg.screenshot(path=os.path.join(SHOTS, f"ending_{len(seq)}_{st}.png"))
        if st == "total": break
        pg.wait_for_timeout(100)
    tend = pg.evaluate("()=>performance.now()")
    lg = pg.evaluate("()=>window._endLog"); total_s = [x["t"] for x in lg if x.get("id") == "end"][0] / 1000
    ok("エンディングの流れ: 碑文に彫る → 光(モザイクが外れる)→ 語の連続表示 → 最後のセリフ → 合計", seq == ["carve", "light", "words", "line", "total"], str(seq))
    ok(f"全体の長さが30〜40秒以内(測定 {total_s:.1f}秒。語 {len(seen)}語の連続表示を含む)", total_s <= 40, f"{total_s:.1f}秒")
    faces = [x["face"] for x in lg if "face" in x]
    ok("表情が変わる: ドヤ顔 → 赤面 → …(役割が切り替わるたび)→ いちばん赤い顔で終わる", faces[0] == "face_dohya" and faces[1] == "face_blush" and faces[-1] == "face_red_max" and len(set(faces)) >= 5, str(faces))
    tl = pg.evaluate("()=>window._endTypeLog"); rate = (len(tl) - 1) / ((tl[-1] - tl[0]) / 1000)
    ok(f"碑文の文字演出は、アガリ演出の段階2と同じ速さ(1秒に {rate:.2f}文字)", 5.0 <= rate <= 5.4, f"{rate:.2f}")
    words = pg.evaluate("()=>endWords().length"); per = (lg[[i for i, x in enumerate(lg) if x.get("id") == "line"][0]]["t"] - lg[[i for i, x in enumerate(lg) if x.get("id") == "words"][0]]["t"]) / max(1, words)
    ok(f"語の連続表示: 1語 0.3〜0.5秒(測定 {per:.0f}ms/語・{words}語)", 290 <= per <= 560, f"{per:.0f}")
    tot = pg.evaluate("()=>document.getElementById('en-total').innerText.replace(/,/g,'')")
    ok("最後に、1周目の本当の解読点の合計が、モザイクなしで出る", int(tot) == round(real) and "█" not in pg.evaluate("()=>document.getElementById('en-pane').innerText"), tot)
    pg.click("#en-next"); pg.wait_for_timeout(300)
    ok("終わったら周回数が2になり、研究♡1になる(lap_config.csv)。ステージは1から", pg.evaluate("()=>[LAP,lvOf(0),RUN.lap,STG.stage]") == [2, 1, 2, 1] and G.ken_lap(2) == 1, str(pg.evaluate("()=>[LAP,lvOf(0),RUN.lap,STG.stage,RUN.real]")))
    # 図鑑の研究メモ(エンディング後)
    pg.evaluate("()=>{document.getElementById('ingo').open=true;slotOpen=2;renderIngo();}")
    html2 = pg.evaluate("()=>document.getElementById('ingobox').innerHTML"); txt2 = pg.evaluate("()=>document.getElementById('ingobox').innerText")
    ok("図鑑(エンディング後): 1周目のメモが消えず、取り消し線と、訂正後(赤字)が続く", all(memos[w]["1周目の研究メモ"].split("。")[0][:8] in txt2 for w in got) and html2.count("<s>") >= len(got) and html2.count('class="red"') >= len(got) and all(memos[w]["訂正後(赤字)"] in txt2 for w in got), f"取り消し線 {html2.count('<s>')} / 赤字 {html2.count('class=' + chr(34) + 'red' + chr(34))}")
    pg.screenshot(path=os.path.join(SHOTS, "zukan_memo_after.png"), full_page=False)
    # スキップ
    pg.evaluate("()=>{LAP=1;runSetLap(1);RUN.real=1234567;pendingEnding=false;}"); pg.evaluate("()=>{startEnding();}"); pg.wait_for_timeout(1500); pg.click("#en-skip"); pg.wait_for_timeout(600)
    ok("スキップできる(すぐに最後の画面。合計が出る)", pg.evaluate("()=>document.getElementById('ending').dataset.stage") == "total" and pg.evaluate("()=>document.getElementById('en-total').innerText") == "1,234,567" and not pg.evaluate("()=>document.getElementById('en-next').hidden"))
    ok("ページエラーがない", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
