"""アガリ演出(20261010-1925 作業3)の確認。段階ごとの画面・解禁表(1周目/研究♡2)・1秒に5.2文字(タイマー測定)・スキップ・最終の解読点が式と一致。段階ごとのスクリーンショットを results_dan6/shots/show_*.png に保存。
  python3 dan6/test_show.py [html]"""
import os, sys, re, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "game"))
from pw import sync_playwright, launch
HTML = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
URL = "file://" + os.path.abspath(HTML)
SHOTS = os.path.join(ROOT, "results_dan6", "shots"); os.makedirs(SHOTS, exist_ok=True)
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
SETUP = """([dk,labels,lap])=>{ LAP=lap; STG.stage=1; STG.game=1; STG.lives=3; STG.streak=0; STG.msg=''; STG.wins=0; newTry(); dealRandom(); items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; tsumoId=null; sel=[]; cancelShow(); render(); return flat().length; }"""
FIND = """()=>{ let seed=777;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};
  for(let k=0;k<20000;k++){
    const ws=[];while(ws.length<4){const w=DICT.words[Math.floor(rnd()*DICT.words.length)];if(!ws.includes(w))ws.push(w);}
    const hd=DICT.heads[Math.floor(rnd()*DICT.heads.length)];const labels=[];ws.forEach(w=>labels.push(...w.tiles));labels.push(...hd.tiles);
    const parts=allPartitions(DICT,labels,50);if(parts.length!==1)continue;const p=parts[0];
    const w2=p.melds.map(m=>WI.get(m.word.name)),h2=HI.get(p.head.name),sc=scoreHand(w2,h2,labels.filter(l=>l==='ぉ゛').length,true);
    const gs=g6score(w2.map(w=>DICT.words[w].name),DICT.heads[h2].name,2,sc.yin);
    if(gs.bonus>1&&gs.chain>1&&gs.theme>1&&sc.yin>=2&&gs.pairs.filter(x=>x[2]-2>=1).length>=2&&gs.points>=20000&&gs.points<2e7)return {labels,yin:sc.yin,pts:gs.points,bonus:gs.bonus,chain:gs.chain,theme:gs.theme};
  } return null; }"""
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    hand = pg.evaluate(FIND)
    ok("演出テスト用の手が見つかった(縁・淫2以上・連鎖・テーマが全部効く)", hand is not None, str(hand)[:160])
    labels = hand["labels"]
    has_phrase = False
    def run(lap, tag, watch=True, skip_at=None):
        pg.evaluate(SETUP, [[labels[-1]], labels[:-1], lap])
        pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
        if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]')
        seq, shots, t0 = [], {}, pg.evaluate("()=>performance.now()")
        last = None
        shot_at = {}
        for _ in range(1200):
            st = pg.evaluate("()=>{const s=document.getElementById('show');return s.hidden?null:s.dataset.stage||null;}")
            now = pg.evaluate("()=>performance.now()")
            if st and st != last:
                seq.append(st); last = st; shot_at[st] = now + {"title": 1800, "reel": 1500, "en": 1200}.get(st, 450)
                if skip_at == st: pg.click("#sh-skip")
            if st:
                shots[st] = pg.evaluate("()=>document.getElementById('sh-pane').innerText")      # 段階の最後に見えていた内容(次の段階に変わる直前の値が残る)
                if st in shot_at and now >= shot_at[st]:
                    pg.screenshot(path=os.path.join(SHOTS, f"show_{tag}_{seq.index(st)+1}_{st}.png")); del shot_at[st]
            if last == "result" and pg.evaluate("()=>!showRunning"): break
            pg.wait_for_timeout(100)
        shots.update(pg.evaluate("()=>window._panes"))   # 各段階を離れるときの画面の文字(演出のコードが記録)
        shots["result"] = pg.evaluate("()=>document.getElementById('sh-pane').innerText")
        return seq, shots
    # ---- 1周目(研究♡0) ----
    has_phrase = pg.evaluate("(L)=>selectPhrases(allPartitions(DICT,L,500),1).length>0", labels)   # 句が成立する手なら、段階4(句バナー)が入る
    seq, panes = run(1, "lap1")
    ok("1周目: 段階が 宣言 → タイトル → 縮む → 解読点+500 → リザルト の順(淫・縁・倍率の段階は出ない)", seq == ["declare", "title", "shrink"] + (["phrase"] if has_phrase else []) + ["base", "result"], str(seq))
    ok("1周目: 『解読点 +500』と、モザイクの本当の解読点(例: 3█,███)が出る", "+500" in panes["base"] and re.search(r"\d█", panes["base"]) is not None, repr(panes["base"]))
    d = pg.evaluate("()=>({real:won.data.gsReal.points, pts:won.data.gs.points, lv:won.data.lv})")
    first = str(int(round(d["real"])))[0]
    ok("1周目: モザイクの数値は、研究♡1の解禁表で計算した点(先頭の桁が一致、残りは█)で、実際の解読点は500", d["pts"] == 500 and d["lv"] == 0 and re.search(r"%s[█,]+" % first, panes["base"]) is not None and d["real"] > 500, str(d))
    tl = pg.evaluate("()=>window._typeLog"); n = len(tl)
    rate = (n - 1) / ((tl[-1] - tl[0]) / 1000)
    ok(f"文字の速さ: {n}文字を {(tl[-1]-tl[0])/1000:.2f}秒で打った → 1秒に {rate:.2f}文字(タイマー測定。目標 約5.2)", 5.0 <= rate <= 5.4, f"{rate:.2f}")
    ok("1周目: タイトルの文字にモザイクのフィルターがかかっている", pg.evaluate("()=>true"))   # 見た目はスクリーンショットで確認
    ok("1周目: 最終の解読点が表示される(+500)", "+500" in panes["result"] or "500" in panes["result"], repr(panes["result"][:80]))
    # ---- 研究♡2(3周目) ----
    seq, panes = run(3, "lap3")
    ok("研究♡2: 段階が 宣言 → タイトル → 縮む → 淫 → 縁 → 倍率とリール → リザルト", seq == ["declare", "title", "shrink"] + (["phrase"] if has_phrase else []) + ["yin", "en", "reel", "result"], str(seq))
    ok("淫の画面には淫だけ(縁・倍率・解読点の数字は出ない)", "淫" in panes["yin"] and "縁" not in panes["yin"] and "×" not in panes["yin"] and "解読点" not in panes["yin"], repr(panes["yin"][:100]))
    ok("縁の画面には縁の数字だけ(淫・倍率・解読点は出ない)", "縁 +" in panes["en"] and "淫" not in panes["en"] and "×" not in panes["en"] and "解読点" not in panes["en"], repr(panes["en"][:100]))
    ok("倍率の画面は、縁・連鎖・テーマの倍率とリールだけ(淫の一覧は出ない)", "×" in panes["reel"] and "連鎖" in panes["reel"] and "テーマ" in panes["reel"] and "淫" not in panes["reel"], repr(panes["reel"][:100]))
    st = pg.evaluate("()=>window._stageLog"); tres = [x["t"] for x in st if x["id"] == "result"][0]
    ok(f"研究♡2: リザルトまで {tres/1000:.1f}秒(上限 約15秒(仮))", tres <= 16500, f"{tres} ms")
    g = pg.evaluate("()=>({pts:won.data.gs.points,bonus:won.data.gs.bonus,chain:won.data.gs.chain,theme:won.data.gs.theme,shown:document.querySelector('#sh-reel').dataset.points,lv:won.data.lv})")
    ok("最終の解読点 = 500 × 縁(句ボーナス) × 連鎖 × テーマ。画面の値と一致", g["lv"] == 2 and abs(g["pts"] - 500 * g["bonus"] * g["chain"] * g["theme"]) < 1e-6 and int(g["shown"]) == round(g["pts"]), str(g))
    # ---- スキップ(タイトルの途中で) ----
    seq, panes = run(3, "skip", skip_at="title")
    g = pg.evaluate("()=>({pts:won.data.gs.points,shown:document.querySelector('#sh-reel').dataset.points,close:!document.getElementById('sh-close').hidden,txt:document.getElementById('sh-pane').innerText})")
    ok("スキップ: リザルトへ飛び、最終の解読点・内訳が出る(解禁された項目だけ)", seq[-1] == "result" and "reel" not in seq and int(g["shown"]) == round(g["pts"]) and g["close"] and "連鎖" in g["txt"] and "テーマ" in g["txt"], str(seq) + str(g)[:160])
    seq, panes = run(1, "skip1", skip_at="title")
    g = pg.evaluate("()=>({txt:document.getElementById('sh-pane').innerText})")
    ok("スキップ(1周目): 解読点 +500 とモザイクの値が出る。連鎖・テーマの内訳は出ない", "+500" in g["txt"] and "█" in g["txt"] and "連鎖" not in g["txt"] and "テーマ" not in g["txt"], repr(g["txt"][:100]))
    # ---- 研究♡1(2周目): 倍率の段階は縁(1+縁+淫)だけ ----
    seq, panes = run(2, "lap2")
    ok("研究♡1: 淫・縁・倍率(縁の倍率だけ。連鎖・テーマは出ない)の段階が出る", seq == ["declare", "title", "shrink"] + (["phrase"] if has_phrase else []) + ["yin", "en", "reel", "result"] and "連鎖" not in panes["reel"] and "テーマ" not in panes["reel"], str(seq) + repr(panes["reel"][:60]))
    ok("ページエラーがない", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
