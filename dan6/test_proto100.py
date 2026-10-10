"""試作HTML(一周版100語。prototype/hiragana_tap_prototype.html)の確認(20261010-1925 作業2):
 語100・雀頭27・山156枚が、data/words_ichishuu100.csv と一致し、エラーなく動く。役・解読点が、Python(yaku14.py・goro14.py。シミュレーションと同じ)と一致する。 python3 dan6/test_proto100.py"""
import os, sys, csv, random, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "game")); sys.path.insert(0, HERE); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu"))
from pw import sync_playwright, launch
import sim_ichishuu as SI
import goro14 as G
from yaku14 import Scorer
URL = "file://" + os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
W100, pairs, usage = SI.load(); v = SI.verify(W100, pairs, usage, SI.rd(os.path.join(SI.D6, "heads.csv")))
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL); pg.wait_for_timeout(400)
    ok("読み込めて、エラーがない", not errs, str(errs[:2]))
    n = pg.evaluate("()=>[DICT.words.length, DICT.heads.length, newDeck().length]")
    ok("語100・雀頭27・山156枚", n == [100, 27, 156], str(n))
    names = pg.evaluate("()=>DICT.words.map(w=>w.name)")
    ok("語が data/words_ichishuu100.csv の100語と同じ", sorted(names) == sorted(w["word"] for w in W100))
    cnt = pg.evaluate("()=>{const c={};newDeck().forEach(l=>c[l]=(c[l]||0)+1);return c;}")
    ok("牌の枚数が、100語の山(40種・156枚。×2=9)と同じ", cnt == v["copies"] and cnt.get("×2") == 9, str({k: (cnt.get(k), v["copies"].get(k)) for k in set(cnt) | set(v["copies"]) if cnt.get(k) != v["copies"].get(k)}))
    heads_html = set(pg.evaluate("()=>DICT.heads.map(h=>h.name)")); ok("雀頭が、シミュレーションと同じ27", heads_html == {h["head"] for h in v["heads"]})
    # 役・解読点の照合(シミュレーションと同じ Scorer(dan6 フル辞書)と、goro14)
    S = Scorer(SI.D6); read = {}
    for i, w in enumerate(S.W):
        for r_ in w["word"].split("・"): read.setdefault(r_, i)
    widx = [read[w["word"]] for w in W100]; hidx = [i for i, h in enumerate(S.H) if h["head"] in heads_html]
    rng = random.Random(20261010)
    def mk(ws, h):
        t = []
        for i in ws: t += S.W[i]["tiles"].split("|")
        return t + S.H[h]["tiles"].split("|")
    hands = [mk(rng.sample(widx, 4), rng.choice(hidx)) for _ in range(300)]
    from judge14 import Judge14
    tmp = os.path.join(ROOT, "ichishuu", "_dict"); SI.write_dict(tmp, W100, v["heads"])
    J = Judge14(os.path.join(tmp, "words.csv"), os.path.join(tmp, "heads.csv"), os.path.join(SI.D6, "tile_variants.csv"))   # シミュレーションと同じ、100語の辞書での分け方
    jn = [w["word"] for w in J.words]; rd_ = {}
    for w in S.W:
        for r_ in w["word"].split("・"): rd_.setdefault(r_, w["word"])
    def cands(h):
        out = []
        for ws, hh, oho, chu in J.partitions(h):
            nm = [rd_[jn[j]] for j in ws]; hd = J.heads[hh]["head"]
            out.append((nm, hd, S.score([S.widx[n] for n in nm], next(k for k, x in enumerate(S.H) if x["head"] == hd), oho)))
        return out
    allc = [cands(h) for h in hands]
    py = [max(({"han": c[2]["han"]} for c in cs), key=lambda x: x["han"]) if cs else None for cs in allc]
    js = pg.evaluate("""(hands)=>hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
        for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true); if(!best||sc.total>best.total)best={total:sc.total}; }
        return best; })""", hands)
    bad = [(i, py[i] and py[i]["han"], js[i]) for i in range(len(hands)) if (py[i] is None) != (js[i] is None) or (py[i] and py[i]["han"] != js[i]["total"])]
    ok(f"淫(形1+役+合体)の最大が、Python(yaku14.py)と試作HTMLで一致({len(hands)}手)", not bad, f"(不一致 {len(bad)}: {bad[:2]})")
    for lv in (0, 1, 2):
        exp = []
        for cs in allc:
            best = None
            for nm, hd, r in cs:
                yin = G.yaku_in(S, r); sc = G.score(nm, hd, G.params(lv), yin); k = (sc["points"], yin)
                if best is None or k > best[0]: best = (k, dict(points=sc["points"], yin=yin))
            exp.append(best[1] if best else None)
        jsp = pg.evaluate("""([hands,lv])=>hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
            for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true);
              const g=g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,lv,sc.yin); if(!best||g.points>best.points||(g.points===best.points&&sc.yin>best.yin))best={points:g.points,yin:sc.yin}; }
            return best; })""", [hands, lv])
        badp = [(i, exp[i]["points"], jsp[i]["points"]) for i in range(len(hands)) if exp[i]["points"] != jsp[i]["points"] or exp[i]["yin"] != jsp[i]["yin"]]
        ok(f"研究♡{lv}: 解読点・淫が、Python(goro14.py)と試作HTMLで一致({len(hands)}手)", not badp, f"(不一致 {len(badp)}: {badp[:2]})")
    ok("ページエラーがない(最後まで)", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
