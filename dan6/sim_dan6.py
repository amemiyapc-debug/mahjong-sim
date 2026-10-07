"""dan6 測定: 強CPU(hint)・弱CPU(weak)各2,000ゲーム(MODX 0.05・×2=13・L=12)→ 語呂度・点・段階クリア・役・語の統計。
使い方: python3 dan6/sim_dan6.py [--games 2000]"""
import sys, os, random, argparse, pickle, json, statistics, collections, csv, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim14, goro14 as G
from sim14 import tile_copies, run_games, Game

D6 = os.path.join(ROOT, "dan6")
VARIANTS = {"現状(しきい値3)": {}, "しきい値を一律+1(4)": {"thresh": 4}, "前置き→部位だけしきい値+1": {"thresh_add": {(0, 2): 1}}}
COND_NAMES = {1: "句", 2: "節", 3: "節でテーマ語3", 4: "文", 5: "複合テーマ成立", 6: "文でテーマ語4", 7: "碑文", 8: "碑文でテーマ語5"}


def sat(m, c):
    """1手の指標 m(size,theme_k,composite)が条件 c を満たすか(テーマ語は、手全体での最大の語数。つながりとは独立に数える)"""
    if c == 1: return m["size"] >= 2
    if c == 2: return m["size"] >= 3
    if c == 3: return m["size"] >= 3 and m["theme_k"] >= 3
    if c == 4: return m["size"] >= 4
    if c == 5: return any(k >= 3 for _, k in m["composite"])      # 複合テーマ成立 = 2タグの語を合わせて3語以上(テーマ倍率が付く)。「両方1語以上」だけだと94%で、条件にならない
    if c == 6: return m["size"] >= 4 and m["theme_k"] >= 4
    if c == 7: return m["size"] >= 5
    return m["size"] >= 5 and m["theme_k"] >= 5


def names_of(S, g):
    return [S.W[i]["word"] for i in g["words"]], S.H[g["head"]]["head"]


def pct(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(len(xs) * q))]


def dist(xs):
    xs = sorted(xs); n = len(xs)
    return dict(n=n, median=xs[n // 2], mean=sum(xs) / n, p90=xs[int(n * .9)], p99=xs[int(n * .99)], max=xs[-1])


def stage_sim(games_m, L, runs, rng, max_stage=30):
    """games_m: ゲームの記録 [(result, turn, {thresh: 指標})]。ステージ制: 3ゲーム/ステージ・ライフ3。
    ノーテンは1ゲーム消費、アガリも1ゲーム消費、テンパイ流局は消費なし(連続テンパイ数だけ数える)。"""
    reached, lives_lost, tsumo, seq3, seq_games, per = [], [], [], 0, 0, collections.defaultdict(lambda: [0, 0])
    first_cl, tenpai_runs = 0, 0
    clear_by_ken = collections.defaultdict(lambda: [0, 0])
    for _ in range(runs):
        stage, lives, t, streak, ach = 1, 3, 0, 0, False
        lost = 0
        while lives > 0 and stage <= max_stage:
            cond = min(stage, 8); ks = G.ken_stage(stage); th = G.KEN[ks]
            used, ok = 0, False
            while used < 3 and not ok:
                res, turn, ms = games_m[rng.randrange(len(games_m))]
                t += turn; seq_games += 1
                if res == "tenpai":
                    streak += 1
                    if streak == 3: seq3 += 1; ach = True
                    continue
                streak = 0; used += 1
                if res == "win" and sat(ms[th], cond): ok = True
            per[stage][1] += 1; clear_by_ken[(ks, cond)][1] += 1
            if ok:
                per[stage][0] += 1; clear_by_ken[(ks, cond)][0] += 1; stage += 1
            else:
                lives -= 1; lost += 1
        reached.append(stage); lives_lost.append(lost); tsumo.append(t); tenpai_runs += ach
    return dict(reached=reached, lives_lost=lives_lost, tsumo=tsumo, per=dict(per), by_ken=dict(clear_by_ken),
                seq3_per_game=seq3 / seq_games, tenpai_run_pct=100 * tenpai_runs / runs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2000); ap.add_argument("--L", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20261007); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "results_dan6")); ap.add_argument("--runs", type=int, default=20000)
    ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    copies = tile_copies(D6, "new", 0.05, 13)
    print("山", sum(copies.values()), "枚", flush=True)
    S = sim14.Scorer(D6)
    cache = os.path.join(a.out, "games.pkl")
    if a.reuse and os.path.exists(cache):
        games = pickle.load(open(cache, "rb"))
    else:
        games = {}
        for cpu in ("hint", "weak"):
            t0 = time.time()
            games[cpu] = run_games(D6, "new", a.L, a.games, a.seed, a.procs, cpu, 0.05, 13)
            print(f"  {cpu}: {time.time()-t0:.0f}秒", flush=True)
        pickle.dump(games, open(cache, "wb"))
    NAME = {"hint": "強CPU", "weak": "弱CPU"}
    rep = {}
    rng0 = random.Random(7)
    # ---- 無作為の手(辞書から4語+雀頭を一様に。牌の制約なし) ----
    allw = [w["word"] for w in S.W]; allh = [h["head"] for h in S.H]
    rand_hands = [(rng0.sample(allw, 4), rng0.choice(allh)) for _ in range(a.games)]
    for cpu in ("hint", "weak"):
        wins = [g for g in games[cpu] if g["result"] == "win"]
        hands = [names_of(S, g) for g in wins]
        n = len(games[cpu]); nw = len(wins)
        r = dict(n=n, wins=nw, win_rate=100 * nw / n, tenpai=100 * sum(g["result"] == "tenpai" for g in games[cpu]) / n,
                 noten=100 * sum(g["result"] == "noten" for g in games[cpu]) / n)
        # 変種ごとの語呂度
        for vn, P in VARIANTS.items():
            sc = [G.score(w, h, P) for w, h in hands]
            rs = [G.score(w, h, P) for w, h in rand_hands]
            for lab, X in (("win", sc), ("rand", rs)):
                pts = [x["points"] for x in X]
                r[(vn, lab)] = dict(dist=dist(pts), floor=100 * sum(p == G.FLOOR for p in pts) / len(pts),
                                    size=collections.Counter(x["size"] for x in X), merges=collections.Counter(x["merges"] for x in X),
                                    links=statistics.mean(x["links"] for x in X), raw=statistics.mean(x["raw_links"] for x in X),
                                    theme=collections.Counter(x["theme"] for x in X),
                                    theme_name=collections.Counter(x["theme_name"] for x in X),
                                    ku=collections.Counter(x["links"] for x in X))
        # 語の組の接続率(アガリ手の語5つ内の10組)
        for vn, P in VARIANTS.items():
            pairs = tot = 0
            slotpair = collections.defaultdict(lambda: [0, 0])
            for w, h in hands:
                nodes = [G.node(x) for x in w] + [G.node(h, True)]
                for i in range(5):
                    for j in range(i + 1, 5):
                        a_, b_ = nodes[i], nodes[j]; s = G.link2(a_, b_, P); tot += 1; pairs += bool(s)
                        k = tuple(sorted([a_["slot_no_eff"], b_["slot_no_eff"]])); slotpair[k][1] += 1; slotpair[k][0] += bool(s)
            r[(vn, "pair")] = 100 * pairs / tot; r[(vn, "slotpair")] = {k: 100 * v[0] / v[1] for k, v in slotpair.items()}
            pr = tt = 0
            for w, h in rand_hands:
                nodes = [G.node(x) for x in w] + [G.node(h, True)]
                for i in range(5):
                    for j in range(i + 1, 5):
                        tt += 1; pr += bool(G.link2(nodes[i], nodes[j], P))
            r[(vn, "pair_rand")] = 100 * pr / tt
        # 役の出現
        yc = collections.Counter(y for g in wins for y in g["yaku"])
        r["yaku"] = {m["name"]: 0 for m in S.M}
        names = sorted({y["name"] for y in S.Y})
        r["yaku_rate"] = {nm: 100 * yc.get(nm, 0) / nw for nm in names}
        mc = collections.Counter(m_ for g in wins for m_ in g["merges"])
        r["merge_rate"] = {m["name"]: 100 * mc.get(m["name"], 0) / nw for m in S.M}
        r["merge_any"] = 100 * sum(1 for g in wins if g["merges"]) / nw
        # 語・スロット・後ろ
        wc = collections.Counter(i for g in wins for i in g["words"])
        tot_words = 4 * nw
        part_back = sum(wc[i] for i, w in enumerate(S.W) if G.ROWS[w["word"]]["part"] == "後ろ")
        back_hand = sum(1 for g in wins if any(G.ROWS[S.W[i]["word"]]["part"] == "後ろ" for i in g["words"]))
        r["back_word_share"] = 100 * part_back / tot_words; r["back_hand"] = 100 * back_hand / nw
        slots = []
        for k, nmk in enumerate(G.SLOT_NAMES):
            idx = [i for i, w in enumerate(S.W) if G.ROWS[w["word"]]["slot_no"] == k]
            cnt = sum(wc[i] for i in idx); hh = sum(1 for g in wins if any(i in set(idx) for i in g["words"]))
            slots.append((k, nmk, len(idx), 100 * hh / nw, 100 * cnt / tot_words))
        r["slots"] = slots
        # 段階クリア(ゲームの記録から、3つのしきい値での指標を前計算)
        rec = []
        for g in games[cpu]:
            if g["result"] == "win":
                w, h = names_of(S, g)
                ms = {}
                for th in (2, 3, 4):
                    s_ = G.score(w, h, {"thresh": th}); ms[th] = dict(size=s_["size"], theme_k=s_["theme_k"], composite=s_["composite"])
                rec.append(("win", g["turn"], ms))
            else:
                rec.append((g["result"], g["turn"], None))
        r["stage"] = stage_sim(rec, a.L, a.runs, random.Random(11))
        # 各条件の「1ステージ(3ゲーム)で満たす確率」を、研究♡の段階別にそのまま測る
        cl = {}
        rr = random.Random(5)
        for th in (4, 3, 2):
            for c in range(1, 9):
                ok = 0; N = 10000
                for _ in range(N):
                    used = 0; hit = False
                    while used < 3 and not hit:
                        res, turn, ms = rec[rr.randrange(len(rec))]
                        if res == "tenpai": continue
                        used += 1
                        if res == "win" and sat(ms[th], c): hit = True
                    ok += hit
                cl[(th, c)] = 100 * ok / N
        r["cond_clear"] = cl
        rep[cpu] = r
    pickle.dump(rep, open(os.path.join(a.out, "report.pkl"), "wb"))
    print("→ report.pkl")


if __name__ == "__main__":
    main()
