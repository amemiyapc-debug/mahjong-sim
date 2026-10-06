"""dan5: 軽量シミュレーション(新辞書342語・×2牌・7スロット)。条件ごとに、強CPU(牌効率のヒント)で自動プレイする。
  python3 dan5/sim_dan5.py --games 2000 --out results_dan5
条件(MODX, ×2の枚数): (0.1,13) (0.05,13) (0,13) (0.1,12) (0.1,14)。L=12。
出力(results_dan5/): summary.csv(条件ごとの数字) / slots_*.csv / yaku_*.csv / merge_*.csv / words_*.csv / tiles_*.csv / stage_proposal_*.csv
"""
import argparse, csv, os, random, sys, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
import sim14
from sim14 import Game, tile_copies, run_games, summarize, write_condition_csvs, write_csv, points

def slot_stats(G, games):
    S = G.S; wins = [g for g in games if g["result"] == "win"]; nw = len(wins)
    slot = [int(w["slot_no"]) for w in S.W]; typ = [w["type"] for w in S.W]
    names = {0: "前置き", 1: "感情・誘い", 2: "部位", 3: "行為", 4: "音", 5: "反応", 6: "喘ぎ声"}
    rows = []
    for k in range(7):
        cnt = [sum(1 for w in g["words"] if slot[w] == k) for g in wins]
        rows.append([k, names[k], sum(1 for x in slot if x == k), f"{100 * sum(1 for c in cnt if c) / nw:.2f}", f"{sum(cnt) / nw:.3f}", f"{100 * sum(cnt) / (4 * nw):.2f}"])
    x2 = [sum(1 for w in g["words"] if typ[w] == "×2") for g in wins]
    return rows, dict(x2_share=100 * sum(x2) / (4 * nw), x2_hand=100 * sum(1 for c in x2 if c) / nw,
                      pre_share=rows[0][5], pre_hand=rows[0][3], x2_words=sum(1 for t in typ if t == "×2"))

def stage_sim(games, init, mult, N=5, lives=3, runs=20000, seed=1, cap=30):
    """ゲームの結果(アガリの点・テンパイ流局・ノーテン)を再抽選して、ステージ制のランを再現する(CLAUDE.md §2。積み点500×連続テンパイ、5連続まで)。"""
    rng = random.Random(seed)
    outs = [("w", points(g["han"])) if g["result"] == "win" else ("t", 0) if g["result"] == "tenpai" else ("n", 0) for g in games]
    reached = []
    for _ in range(runs):
        stage, lv, score, used, streak, safety = 1, lives, 0, 0, 0, 0
        while stage <= cap:
            tgt = round(init * mult ** (stage - 1) / 100) * 100
            k, v = outs[rng.randrange(len(outs))]
            if k == "t" and safety < 30:
                streak += 1; safety += 1; continue
            safety = 0
            if k == "w": score += v + min(streak, 5) * 500; used += 1; streak = 0
            else: used += 1; streak = 0
            if score >= tgt: stage += 1; score = used = 0; streak = 0; continue
            if used >= N:
                lv -= 1; score = used = 0; streak = 0
                if lv <= 0: break
        reached.append(min(stage, cap))
    reached.sort(); n = len(reached)
    return dict(mean=sum(reached) / n, p10=reached[n // 10], p50=reached[n // 2], p90=reached[9 * n // 10], first=100 * sum(1 for r in reached if r >= 2) / n)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=2000); ap.add_argument("--L", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20261030); ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "results_dan5")); ap.add_argument("--dir", default=os.path.join(ROOT, "dan5"))
    ap.add_argument("--conds", default="0.1:13,0.05:13,0:13,0.1:12,0.1:14")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    summ, order = {}, []
    for c in a.conds.split(","):
        modx, x2 = float(c.split(":")[0]), int(c.split(":")[1]); tag = f"m{modx:g}_x{x2}"; order.append(tag)
        copies = tile_copies(a.dir, "new", modx, x2); t0 = time.time()
        print(f"条件 MODX={modx:g} ×2={x2}枚: 山 {sum(copies.values())}枚 / {a.games}ゲーム L={a.L}", flush=True)
        games = run_games(a.dir, "new", a.L, a.games, a.seed, a.procs, "hint", modx, x2)
        G = Game(a.dir, copies, a.L)
        s = summarize(games, a.L); s.update(write_condition_csvs(a.out, tag, G, games, copies, a.dir)); s["wall"] = sum(copies.values())
        rows, sx = slot_stats(G, games); s.update(sx)
        write_csv(os.path.join(a.out, f"slots_{tag}.csv"), ["slot_no", "slot", "words_in_slot", "hands_with_slot_word_pct", "mean_words_per_hand", "share_of_words_pct"], rows)
        s["slots"] = rows
        # ステージ目標点の提案: 初期目標を振って、到達ステージを見る(倍率1.3・N=5・ライフ3。従来の設計の基準は、平均到達ステージ約5.2)
        prop = []
        for init in list(range(2000, 13001, 2000)) + list(range(14000, 40001, 2000)):
            r = stage_sim(games, init, 1.3); prop.append([init, 1.3, f"{r['mean']:.2f}", r["p10"], r["p50"], r["p90"], f"{r['first']:.1f}"])
        write_csv(os.path.join(a.out, f"stage_proposal_{tag}.csv"), ["initial_target", "mult", "mean_stage", "p10", "p50", "p90", "stage1_clear_pct"], prop)
        s["stage"] = prop; summ[tag] = s
        print(f"  完了 {time.time()-t0:.0f}秒: アガリ率 {s['win_rate']:.1f}% 平均翻 {s['mean_han']:.2f} ×2語 {s['x2_share']:.1f}% 前置き {s['pre_share']}%", flush=True)
    keys = ["wall", "games", "wins", "win_rate", "win_ci", "tenpai_ryukyoku", "noten", "t3", "cum_tenpai_t3", "t6", "cum_tenpai_t6", "mean_han", "ge5", "ge8", "noyaku",
            "mean_points", "mean_turn", "merge_any", "merge_two", "x2_words", "x2_share", "x2_hand", "pre_share", "pre_hand", "word_max", "word_min_pos", "ratio", "zero_words", "gini"]
    fmt = lambda v: f"{v:.4g}" if isinstance(v, float) else v
    rows = [[k] + [fmt(summ[t][k]) for t in order] for k in keys]
    for k in range(7):
        rows.append([f"slot{k}_{summ[order[0]]['slots'][k][1]}_hand_pct"] + [summ[t]["slots"][k][3] for t in order])
        rows.append([f"slot{k}_{summ[order[0]]['slots'][k][1]}_word_share_pct"] + [summ[t]["slots"][k][5] for t in order])
    write_csv(os.path.join(a.out, "summary.csv"), ["metric"] + order, rows)
    print("→", os.path.join(a.out, "summary.csv"))

if __name__ == "__main__":
    main()
