"""解読点の解禁表(20261008-2250・2230)の測定。強CPU(hint)・seed 20261008+i・残りツモ12・一周版100語。
 1,000試合(= 前回までと同じ試合。digest で確認)+ ステージ条件用に先の2,000試合を足した3,000試合(先頭1,000は同じ)。
 句の倍率(PHRASE_MULT)は未決のため点に入れていない。python3 ichishuu/measure_score_unlock.py"""
import json, os, sys, hashlib, statistics, copy
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu")); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim_ichishuu as S
import goro14 as G
from judge14 import Judge14
from yaku14 import Scorer

GAMES, TOTAL, SEED, L = 1000, 3000, 20261008, 12
BASE_U = copy.deepcopy(G.UNLOCK)
def U(**ov):
    u = copy.deepcopy(BASE_U)
    for k, v in ov.items(): u[k] = dict(zip((0, 1, 2), v))
    return u
VARIANTS = {   # 名前: (研究♡, 解禁表, しきい値方式 or None=全項目・旧)
    "lv0": (0, BASE_U, "const"), "lv1": (1, BASE_U, "const"), "lv2": (2, BASE_U, "const"),
    "lv1_a_縁だけ": (1, U(yaku=(0, 0, 1), phrase=(0, 0, 1)), "const"),
    "lv2_a_縁だけ": (2, U(yaku=(0, 0, 1), phrase=(0, 0, 1)), "const"),
    "KEN_lv0": (0, BASE_U, "table"), "KEN_lv1": (1, BASE_U, "table"), "KEN_lv2": (2, BASE_U, "table"),
    "旧(KEN・全項目)_lv0": (0, None, "table"), "旧(KEN・全項目)_lv1": (1, None, "table"), "旧(KEN・全項目)_lv2": (2, None, "table"),
}

def main():
    W100, pairs, usage = S.load(); heads_all = S.rd(os.path.join(S.D6, "heads.csv"))
    v = S.verify(W100, pairs, usage, heads_all); heads = v["heads"]; copies = v["copies"]
    tmp = os.path.join(ROOT, "ichishuu", "_dict")
    games = S.play_all(W100, heads, copies, L, TOTAL, SEED, 4, "hint", tmp)
    g1 = games[:GAMES]
    digest = hashlib.sha256(json.dumps([(g["result"], g["turn"], g.get("hand")) for g in g1], ensure_ascii=False).encode()).hexdigest()[:16]
    J = Judge14(os.path.join(tmp, "words.csv"), os.path.join(tmp, "heads.csv"), os.path.join(S.D6, "tile_variants.csv"))
    names = [w["word"] for w in J.words]
    Sc = Scorer(S.D6)
    d6 = {w["word"]: w for w in S.rd(os.path.join(S.D6, "words.csv"))}; read = {}
    for w in d6.values():
        for r in w["word"].split("・"): read.setdefault(r, w["word"])
    win_idx = [i for i, g in enumerate(g1) if g["result"] == "win"]
    pts = {k: [] for k in VARIANTS}; extra = {"lv2_chain>1": 0, "lv2_theme>1": 0, "lv2_en>0": 0, "yin>0": 0}
    for i in win_idx:
        cand = []
        for ws, h, oho, chu in J.partitions(g1[i]["hand"]):
            nm = [read[names[j]] for j in ws]; hd = J.heads[h]["head"]
            r = Sc.score([Sc.widx[n] for n in nm], next(k for k, x in enumerate(Sc.H) if x["head"] == hd), oho)
            cand.append((nm, hd, G.yaku_in(Sc, r)))
        best_full = None
        for name, (lv, u, mode) in VARIANTS.items():
            G.UNLOCK = u if u is not None else BASE_U
            P = G.params(lv, mode) if u is not None else dict(thresh=G.thresh_of(lv, mode))   # u=None: lv を渡さない = 全項目解禁(旧式)
            pts[name].append(max(G.score(nm, hd, P, yin)["points"] for nm, hd, yin in cand))
        G.UNLOCK = BASE_U
        sc = max((G.score(nm, hd, G.params(2), yin) for nm, hd, yin in cand), key=lambda x: x["points"])
        extra["lv2_chain>1"] += sc["chain"] > 1; extra["lv2_theme>1"] += sc["theme"] > 1; extra["lv2_en>0"] += sc["en"] > 0; extra["yin>0"] += sc["yin"] > 0
    out = dict(games=GAMES, wins=len(win_idx), win_rate=100 * len(win_idx) / GAMES, digest=digest, same_games_as_before=(digest == "e4eadad994d27ee3"), dist={}, extra=extra)
    for name, x in pts.items():
        xs = sorted(x); n = len(xs)
        out["dist"][name] = dict(n=n, mean=statistics.mean(x), median=statistics.median(x), p90=xs[int(n * .9)], max=xs[-1], min=xs[0], at500=100 * sum(1 for y in x if y == 500) / n)
    # ステージ条件(1周目): 3ゲームのうち N 回以上和了。先頭3,000試合を3つずつ(1,000組)
    triples = [sum(1 for g in games[3 * k:3 * k + 3] if g["result"] == "win") for k in range(TOTAL // 3)]
    out["stage"] = dict(trials=len(triples), win_rate_3000=100 * sum(1 for g in games if g["result"] == "win") / TOTAL,
                        clear={str(n): 100 * sum(1 for t in triples if t >= n) / len(triples) for n in (1, 2, 3)},
                        tenpai_rate=100 * sum(1 for g in games if g["result"] == "tenpai") / TOTAL)
    json.dump(out, open(os.path.join(ROOT, "ichishuu", "results_score_unlock_20261008.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))

if __name__ == "__main__":
    main()
