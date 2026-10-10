"""句バナーとリナの台詞・句の図鑑(20261010-1925 作業5)の確認。画面を操作して、アガリ→バナーを見る。 python3 dan6/test_phrase_banner.py"""
import os, sys, json, csv, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "game"))
from pw import sync_playwright, launch
URL = "file://" + os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
SHOTS = os.path.join(ROOT, "results_dan6", "shots")
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
names = {(r["語A"], r["語B"]): r for r in csv.DictReader(open(os.path.join(ROOT, "data", "phrase_names.csv"), encoding="utf-8-sig"))}
sb = names[("ちんぽ", "まんこ")]
SETUP = """([dk,labels,lap])=>{ LAP=lap; runSetLap(lap); STG.stage=1; STG.game=1; STG.lives=3; STG.streak=0; STG.msg=''; STG.wins=0; newTry(); dealRandom(); RUN.games=5; items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; tsumoId=null; sel=[]; cancelShow(); render(); return flat().length; }"""
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.goto(URL); pg.wait_for_timeout(300)
    def win(labels, lap):
        pg.evaluate(SETUP, [[labels[-1]], labels[:-1], lap]); pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
        if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]')
        pg.wait_for_timeout(600)
        return pg.evaluate("()=>won.data.phrase&&{name:won.data.phrase.name,sub:won.data.phrase.sub,lina:won.data.phrase.lina,n:won.data.phrase.n,kind:won.data.phrase.c.kind,lap1:won.data.phrase.lap1,html:won.data.phrase.html}")
    H_SB = ['ち', 'ん', 'ぽ', 'ま', 'ん', 'こ', 'ぬれ', 'く', 'り', 'い', 'く', 'う', 'あ', 'ん']
    ok("データ: 看板30組・型9種。句は100語版にある", pg.evaluate("()=>[PH.SB.length,Object.keys(PH.TY).length,CFG.PHRASE_CAP,CFG.LINA_EVERY]") == [30, 9, 1, 3])
    pg.evaluate("()=>{localStorage.removeItem('hm-proto-phrasedex');}")
    r1 = win(H_SB, 1)
    ok("1周目: 看板(ちんぽ+まんこ)は『リナ曰く「誤読名」』。名前(交尾)は出ない", r1 and r1["kind"] == "sb" and r1["name"] == "リナ曰く「" + sb["1周目の誤読名"] + "」" and "交尾" not in r1["name"], str(r1)[:200])
    ok("1手に出る句は1つだけ(1手1句。この手には、型の句も複数成立している)", pg.evaluate("()=>{const c=selectPhrases(allPartitions(DICT,flat().map(t=>t.label),500),99);return [c.length, selectPhrases(allPartitions(DICT,flat().map(t=>t.label),500),1).length];}") [1] == 1 and pg.evaluate("()=>won.data.phrase!==null"))
    ok("初めて成立: リナの台詞が必ず出る", r1["n"] == 1 and r1["lina"] != "", r1["lina"])
    lines = [r1["lina"]]
    for k in range(2, 8):
        r = win(H_SB, 1); lines.append(r["lina"] if r else None)
    shown = [i + 1 for i, l in enumerate(lines) if l]
    ok("台詞の頻度: 1回目は必ず、2回目以降は3回に1回(4・7回目)。定数 CFG.LINA_EVERY で変えられる", shown == [1, 4, 7], str(shown))
    pg.evaluate("()=>{CFG.LINA_EVERY=2;}"); r = win(H_SB, 1)   # 8回目: (8-1)%2 != 0 → なし。9回目: あり
    r9 = win(H_SB, 1); pg.evaluate("()=>{CFG.LINA_EVERY=3;}")
    ok("定数(LINA_EVERY)を変えると頻度が変わる(2に変えると、8回目なし・9回目あり)", (r["lina"] == "") and (r9["lina"] != ""), str((r["lina"], r9["lina"])))
    pd = pg.evaluate("()=>JSON.parse(localStorage.getItem('hm-proto-phrasedex'))")
    ok("図鑑には、表示した句だけが記録される(看板1件。型の句は記録されない)", len(pd["sb"]) == 1 and sum(len(v) for v in pd["ty"].values()) == 0 and list(pd["sb"].values())[0]["n"] == 9, str(pd)[:200])
    # エンディング後(2周目以降)
    r2 = win(H_SB, 2)
    ok("2周目以降: 看板は理解後の名前(交尾)。「リナ曰く」は付かない", r2["name"] == sb["名前"] and "リナ曰く" not in r2["name"] and not r2["lap1"], str(r2)[:160])
    # 型の句(看板でない手)を探す
    H_TY = pg.evaluate("""()=>{ let seed=99;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
      for(let k=0;k<20000;k++){const ws=[];while(ws.length<4){const w=DICT.words[Math.floor(rnd()*DICT.words.length)];if(!ws.includes(w))ws.push(w);}
        const hd=DICT.heads[Math.floor(rnd()*DICT.heads.length)];const labels=[];ws.forEach(w=>labels.push(...w.tiles));labels.push(...hd.tiles);
        const parts=allPartitions(DICT,labels,50);if(parts.length!==1)continue;const c=selectPhrases(parts,99);
        if(c.length>=3&&c.every(x=>x.kind==='ty')&&new Set(c.map(x=>x.t)).size>=2)return {labels,types:[...new Set(c.map(x=>x.t))]};}
      return null; }""")
    ok("型の句が複数成立する手(看板なし)が見つかった", H_TY is not None, str(H_TY))
    pg.evaluate("()=>{localStorage.removeItem('hm-proto-phrasedex');}")
    t1 = win(H_TY["labels"], 1)
    freq = pg.evaluate("()=>PH.FREQ")
    least = min(freq[t] for t in H_TY["types"])
    tid = pg.evaluate("()=>won.data.phrase.c.t")
    ok("型の句: 出現回数の少ない型を優先して1つ表示する", t1["kind"] == "ty" and freq[tid] == least, f"型{tid} 出現{freq[tid]} / 候補の型 {H_TY['types']} の最少 {least}")
    ok("1周目の型の句: 型の説明文に語A・語Bを当てはめたリナ調の文(リナ曰く)。点にならない旨も出る", t1["name"].startswith("リナ曰く「") and "解読点にはならない" in t1["html"], t1["name"])
    t2 = win(H_TY["labels"], 2)
    desc = pg.evaluate("()=>PH.TYD[won.data.phrase.c.t].desc")
    ok("2周目以降の型の句: 型の説明文に語A・語Bを当てはめた文(リナ曰くなし)", "リナ曰く" not in t2["name"] and "A" not in t2["name"] and "B" not in t2["name"] and len(t2["name"]) > 8, t2["name"] + " / " + desc)
    pd = pg.evaluate("()=>JSON.parse(localStorage.getItem('hm-proto-phrasedex'))")
    ok("図鑑: 型の句は型ごとのページに、表示した組だけが入る", len(pd["sb"]) == 0 and sum(len(v) for v in pd["ty"].values()) >= 1 and sum(len(v) for v in pd["ty"].values()) <= 2, str(pd)[:160])
    # 画面: 句バナー(アガリ演出の段階4)
    pg.evaluate(SETUP, [["ん"], H_SB[:-1], 1]); pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
    if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]')
    seen = None
    for _ in range(200):
        st = pg.evaluate("()=>document.getElementById('show').dataset.stage")
        if st == "phrase":
            pg.wait_for_timeout(500); seen = pg.evaluate("()=>document.getElementById('sh-pane').innerText"); pg.screenshot(path=os.path.join(SHOTS, "show_phrase_lap1.png")); break
        pg.wait_for_timeout(100)
    ok("アガリ演出の段階4に句バナーが出る(1周目: リナ曰く・点にならない旨・台詞)", seen and "リナ曰く" in seen and "解読点にはならない" in seen, repr(seen))
    pg.evaluate("()=>cancelShow()"); pg.evaluate("()=>{document.getElementById('ingo').open=true;renderIngo();}")
    dex = pg.evaluate("()=>document.getElementById('ingobox').innerText")
    ok("図鑑(淫語集)に「句の図鑑」が出る", "句の図鑑" in dex and "看板" in dex, dex[-200:])
    ok("ページエラーがない", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
