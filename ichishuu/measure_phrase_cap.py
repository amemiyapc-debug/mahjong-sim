"""句の出すぎ対策(20261008-2100)の再測定と、句の固定点の材料(20261008-2110)。測定のみ。点の計算には句を入れない。
強CPU(既存の hint)・1,000試合・seed 20261008+i・残りツモ12。 python3 ichishuu/measure_phrase_cap.py"""
import json, os, sys, itertools, hashlib, random, statistics, csv
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu")); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim_ichishuu as S
import phrase_types as PT
import goro14 as G
from judge14 import Judge14
from yaku14 import Scorer

GAMES, SEED, L = 1000, 20261008, 12
CONDS = {"a'_看板のみ+上限1": ("1", ()), "c'_看板+9型+上限1": (None, ("1", "2", "3", "4", "5", "6", "7", "8", "10")), "d_看板+型1,5,6,7,8,10+上限1": (None, ("1", "5", "6", "7", "8", "10"))}
circ = {"1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤", "6": "⑥", "7": "⑦", "8": "⑧", "10": "⑩"}


def main():
    cfg = PT.load_config(); freq = PT.load_type_frequency(); cap = cfg["PHRASE_CAP_PER_HAND"]
    W100, pairs, usage = S.load(); heads_all = S.rd(os.path.join(S.D6, "heads.csv"))
    v = S.verify(W100, pairs, usage, heads_all); heads = v["heads"]; copies = v["copies"]
    tmp = os.path.join(ROOT, "ichishuu", "_dict")
    games = S.play_all(W100, heads, copies, L, GAMES, SEED, 4, "hint", tmp)
    digest = hashlib.sha256(json.dumps([(g["result"], g["turn"], g.get("hand")) for g in games], ensure_ascii=False).encode()).hexdigest()[:16]
    J = Judge14(os.path.join(tmp, "words.csv"), os.path.join(tmp, "heads.csv"), os.path.join(S.D6, "tile_variants.csv"))
    names = [w["word"] for w in J.words]; book = PT.PhraseBook()
    win_idx = [i for i, g in enumerate(games) if g["result"] == "win"]
    parts = {i: J.partitions(games[i]["hand"]) for i in win_idx}
    out = dict(games=GAMES, wins=len(win_idx), win_rate=100 * len(win_idx) / GAMES, digest=digest, same_games_as_before=(digest == "e4eadad994d27ee3"), cap=cap, freq=freq, conds={})
    allpairs = lambda ps: {frozenset(c) for c in itertools.combinations(sorted(names[i] for i in ps), 2)}
    # ---- 句の再測定 ----
    chosen_by_cond = {}
    for cname, (only, tids) in CONDS.items():
        S_ = book.phrases(True, tids)
        shown, labels, seen, sb_seen, per_type_seen = {}, Counter(), set(), set(), Counter()
        for i in win_idx:
            cand = set().union(*[allpairs(p[0]) & S_ for p in parts[i]])
            rng = random.Random(SEED + i + 1_000_000)
            sel = PT.select_phrases(cand, book, tids, rng, cap, freq)
            shown[i] = sel
            for ph in sel:
                lab = PT.classify(ph, book, tids); labels[lab] += 1; seen.add(ph)
                if lab == "看板": sb_seen.add(ph)
        chosen_by_cond[cname] = shown
        nshown = sum(len(x) for x in shown.values()); nw = len(win_idx)
        out["conds"][cname] = dict(defined=len(S_), win_with_shown=100 * sum(1 for x in shown.values() if x) / nw, shown_total=nshown, per_game=nshown / GAMES, per_9=9 * nshown / GAMES,
                                   distinct=len(seen), signboard_share=100 * labels["看板"] / max(1, nshown), labels=dict(labels), signboard_distinct=len(sb_seen),
                                   types_never=[t for t in tids if labels.get(t, 0) == 0], max_per_hand=max(len(x) for x in shown.values()))
    # ---- 和了点(句の点は入れない)。100語の分け方ごとに、dan6 の役・語呂度で点を数え、点が最大の分け方を採用 ----
    Sc = Scorer(S.D6)
    d6 = {w["word"]: w for w in S.rd(os.path.join(S.D6, "words.csv"))}; read = {}
    for w in d6.values():
        for r in w["word"].split("・"): read.setdefault(r, w["word"])
    pts = {0: [], 1: [], 2: []}
    for i in win_idx:
        for lv in (0, 1, 2):
            best = 0
            for ws, h, oho, chu in parts[i]:
                nm = [read[names[j]] for j in ws]; hd = J.heads[h]["head"]
                r = Sc.score([Sc.widx[n] for n in nm], next(k for k, x in enumerate(Sc.H) if x["head"] == hd), oho)
                best = max(best, G.score(nm, hd, G.params(lv), G.yaku_in(Sc, r))["points"])
            pts[lv].append(best)
    out["points"] = {}
    for lv in (0, 1, 2):
        x = pts[lv]; tot = sum(x)
        xs = sorted(x); k = max(1, len(xs) // 100)
        out["points"][lv] = dict(n=len(x), mean=statistics.mean(x), median=statistics.median(x), min=min(x), max=max(x), total_per_game=tot / GAMES, per_9=9 * tot / GAMES,
                                 p90=xs[int(len(xs) * .9)], p99=xs[int(len(xs) * .99)], mean_without_top1pct=statistics.mean(xs[:-k]), top1pct_share_of_total=100 * sum(xs[-k:]) / tot, top3=xs[-3:])
        out["points"][lv]["increase"] = {}
        for cname in CONDS:
            ns = out["conds"][cname]["shown_total"]
            out["points"][lv]["increase"][cname] = {str(p): dict(fixed=p / 100 * statistics.mean(x), pct=100 * ns * (p / 100 * statistics.mean(x)) / tot) for p in (5, 10, 20, 30)}
    json.dump(out, open(os.path.join(ROOT, "ichishuu", "results_phrase_cap_20261008.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("games", "wins", "win_rate", "digest", "same_games_as_before", "cap")}, ensure_ascii=False))
    for c, r in out["conds"].items(): print(c, r)
    for lv, r in out["points"].items(): print("lv", lv, {k: (round(x, 1) if isinstance(x, float) else x) for k, x in r.items() if k != "increase"})


if __name__ == "__main__":
    main()
