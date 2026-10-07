"""dan6 測定: 強CPU(hint)・弱CPU(weak)・点を狙うCPU(hint+見送り) → 語呂度・点・名前つき役(淫)・段階クリア・見送り・役・語の統計。
  python3 dan6/sim_dan6.py --phase pool   # 強・弱CPU 各2,000ゲーム(見送りなし)を、研究♡0/1/2で評価
  python3 dan6/sim_dan6.py --phase live   # 3種のCPUで、段階クリアを実際に遊ぶ(挑戦 --runs 回)
結果は results_dan6/ の pool.pkl・live.pkl。表示とCSVは dan6/report_dan6.py。
条件を狙い直すCPU(seek): 同じ見送り回数で、そのステージの条件を満たさないアガリを見送り、条件を狙い直す(満たすアガリは取る)。
点を狙うCPU(仮): 見送りを使える(研究♡ごとの回数。1ステージの1回の挑戦=3ゲームで共有)。アガリが、そのステージの条件を満たしていて、かつ
  点が LOW(50,000点)未満のときだけ「見送る」。条件を満たさないアガリは見送らず、そのまま取る。捨て牌は、強CPU(牌効率のヒント)と同じ選び方。"""
import sys, os, random, argparse, pickle, collections, time
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim14, goro14 as G
from sim14 import tile_copies, run_games, Game

D6 = os.path.join(ROOT, "dan6")
LOW = 50000
MAXS = 30
KINDS = {"strong": "hint", "weak": "weak", "aim": "hint", "seek": "hint"}


def sat(m, c):
    """1手の指標 m(size,theme_k,composite)が条件 c を満たすか(テーマ語は、手全体での最大の語数。つながりとは独立に数える)"""
    if c == 1: return m["size"] >= 2
    if c == 2: return m["size"] >= 3
    if c == 3: return m["size"] >= 3 and m["theme_k"] >= 3
    if c == 4: return m["size"] >= 4
    if c == 5: return any(k >= 3 for _, k in m["composite"])      # 複合テーマ成立 = 2タグの語を合わせて3語以上(テーマ倍率が付く)
    if c == 6: return m["size"] >= 4 and m["theme_k"] >= 4
    if c == 7: return m["size"] >= 5
    return m["size"] >= 5 and m["theme_k"] >= 5


# ---------------- 段階クリア(実際に遊ぶ) ----------------
_g = None


def _init(kind):
    global _g
    cp = tile_copies(D6, "new", 0.05, 13)
    _g = (Game(D6, cp, 12, cpu=KINDS[kind]), kind)


def challenge(seed):
    Gm, kind = _g; S = Gm.S; rng = random.Random(seed)
    stage, lives, tsumo, streak, ach = 1, 3, 0, 0, False
    attempts, games, seq3 = [], [], 0
    while lives > 0 and stage <= MAXS:
        cond = min(stage, 8); lv = G.ken_stage(stage); P = {"thresh": G.KEN[lv]}
        ctx = {"skips": G.SKIPS[lv] if kind in ("aim", "seek") else 0}
        used, ok = 0, False
        while used < 3 and not ok:
            ev = []

            def skip(hand, turn, r):
                if ctx["skips"] <= 0: return False
                b = G.best_hand(S, hand, P)
                if kind == "aim":                                   # 点を狙う: 条件を満たしていて、点が低いアガリを見送る
                    take = b and sat(b, cond) and b["points"] < LOW
                else:                                               # seek(条件を狙い直す): 条件を満たさないアガリを見送る
                    take = b and not sat(b, cond)
                if take:
                    ctx["skips"] -= 1; ev.append(b["points"]); return True
                return False
            g = Gm.play(rng, skip if kind in ("aim", "seek") else None)
            tsumo += g["turn"]
            rec = dict(stage=stage, lv=lv, cond=cond, result=g["result"], turn=g["turn"], skips=ev, skipfail=bool(g.get("skipfail")))
            if g["result"] == "tenpai":
                streak += 1
                if streak == 3: seq3 += 1; ach = True
                games.append(rec); continue
            streak = 0; used += 1
            if g["result"] == "win":
                b = G.best_hand(S, g["hand"], P)
                m = dict(size=b["size"], theme_k=b["theme_k"], composite=b["composite"])
                rec.update(points=b["points"], points_noyaku=b["points_noyaku"], yin=b["yin"], size=b["size"], theme_k=b["theme_k"], links=b["links"],
                           raw_links=b["raw_links"], chain=b["merges"], theme=b["theme"], yaku=b["yaku"], yaku_merges=b["yaku_merges"], sat=sat(m, cond))
                if rec["sat"]: ok = True
            else:
                rec["points"] = 0
            games.append(rec)
        attempts.append((stage, ok))
        if ok: stage += 1
        else: lives -= 1
    return dict(reached=stage, attempts=attempts, tsumo=tsumo, games=games, seq3=seq3, ach=ach)


def run_live(kind, n, seed, procs):
    with Pool(procs, initializer=_init, initargs=(kind,)) as p:
        out = []
        for i, r in enumerate(p.imap(challenge, [seed + i for i in range(n)], chunksize=4)):
            out.append(r)
            if (i + 1) % 100 == 0: print(f"    {kind}: {i+1}/{n} 挑戦", flush=True)
    return out


# ---------------- 強・弱CPU 見送りなし 2,000ゲーム ----------------
def run_pool(a):
    S = sim14.Scorer(D6)
    cp = tile_copies(D6, "new", 0.05, 13); print("山", sum(cp.values()), "枚", flush=True)
    out = {}
    for kind in ("strong", "weak"):
        t0 = time.time()
        games = run_games(D6, "new", 12, a.games, a.seed, a.procs, KINDS[kind], 0.05, 13)
        res = dict(games=[{k: v for k, v in g.items() if k != "hand"} for g in games], lv={})
        wins = [g for g in games if g["result"] == "win"]
        for lv in (0, 1, 2):
            res["lv"][lv] = [G.best_hand(S, g["hand"], {"thresh": G.KEN[lv]}) for g in wins]
        out[kind] = res
        print(f"  {kind}: {time.time()-t0:.0f}秒 アガリ {len(wins)}/{len(games)}", flush=True)
    rng0 = random.Random(7)
    allw = [w["word"] for w in S.W]; allh = [h["head"] for h in S.H]
    rh = [(rng0.sample(allw, 4), rng0.choice(allh)) for _ in range(a.games)]
    out["rand"] = {lv: [G.score(w, h, {"thresh": G.KEN[lv]}) for w, h in rh] for lv in (0, 1, 2)}
    out["variants"] = {}
    VAR = {"現状(しきい値3)": {}, "しきい値を一律+1(4)": {"thresh": 4}, "前置き→部位だけしきい値+1": {"thresh_add": {(0, 2): 1}}}
    for kind in ("strong", "weak"):
        # しきい値の変種は、アガリ手の4語+雀頭を使って評価(前回の測定と同じ。名前つき役の淫は加えない)
        hs = [(g["words"], g["head"]) for g in out[kind]["lv"][1]]
        out["variants"][kind] = {vn: [G.score(w, h, P) for w, h in hs] for vn, P in VAR.items()}
    out["variants"]["rand"] = {vn: [G.score(w, h, P) for w, h in rh] for vn, P in VAR.items()}
    pickle.dump(out, open(os.path.join(a.out, "pool.pkl"), "wb"))
    print("→ pool.pkl")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="pool", choices=["pool", "live"])
    ap.add_argument("--games", type=int, default=2000); ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261007); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "results_dan6")); ap.add_argument("--kinds", default="strong,weak,aim")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    if a.phase == "pool":
        run_pool(a)
    else:
        path = os.path.join(a.out, "live.pkl")
        live = pickle.load(open(path, "rb")) if os.path.exists(path) else {}
        for kind in a.kinds.split(","):
            t0 = time.time(); live[kind] = run_live(kind, a.runs, a.seed, a.procs)
            pickle.dump(live, open(path, "wb")); print(f"  {kind}: {time.time()-t0:.0f}秒", flush=True)
        print("→ live.pkl")


if __name__ == "__main__":
    main()
