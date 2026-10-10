"""1周目のステージ条件(和了回数。data/stage_wins_lap1.csv)のクリア率と、ライフ3での脱落(ゲームオーバー)の確率。20261010-1210
規則: 1ステージ=3ゲーム、ライフ3。アガリ・ノーテンは1ゲーム消費、テンパイ流局は消費しない。必要回数に達した時点でクリア、3ゲーム使って届かなければライフ-1・同じステージをやり直し。
強CPU(hint)・一周版100語・残りツモ12・seed 20261008+i(i < N)。試合の流れを順に使う(1回の挑戦=ステージ1から。ステージ3クリアかゲームオーバーで終わる)。
python3 ichishuu/measure_stage_lap1.py [N=12000]"""
import json, os, sys, math, hashlib, statistics
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu")); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim_ichishuu as S
import goro14 as G

SEED, L, LAST = 20261008, 12, 3        # LAST: ここまでクリアしたら終わり(1周目のステージ数は未決。決定済みの条件があるステージ1〜3まで)


def run_stream(results, need):
    """results: 'win'/'tenpai'/'nowin' の列。返り値: 挑戦ごとの dict と、使わなかった試合数"""
    i, n, runs = 0, len(results), []
    while True:
        stage, lives, att, used_i = 1, 3, [], i
        hist = []; consumed = 0
        while lives > 0 and stage <= LAST:
            wins, cons = 0, 0
            while cons < 3:
                if i >= n: return runs, n - used_i
                r = results[i]; i += 1
                if r == "tenpai": continue            # テンパイ流局: ゲームを消費しない
                cons += 1; consumed += 1; wins += (r == "win")
                if wins >= need(stage): break
            ok = wins >= need(stage)
            hist.append((stage, ok))
            if ok: stage += 1
            else: lives -= 1
        runs.append(dict(hist=hist, over=(lives == 0), cleared_last=(stage > LAST), consumed=consumed, played=i - used_i))


def analytic(p, need):
    """1ゲーム(消費するゲーム)の和了確率 p・各ゲーム独立として、各ステージの1回の挑戦のクリア率と、ライフ3で脱落する確率(計算)"""
    def clear(nd):   # 3ゲーム中、nd 回に達する確率
        return sum(math.comb(3, k) * p ** k * (1 - p) ** (3 - k) for k in range(nd, 4))
    cs = [clear(need(s)) for s in range(1, LAST + 1)]
    # ライフ3: 各ステージで、連続でなく合計3回まで失敗できる。状態=(ステージ, 失敗回数)。失敗が3回で脱落
    from functools import lru_cache
    @lru_cache(None)
    def reach(stage, fails):   # この状態から ステージ LAST+1 に着く確率
        if fails >= 3: return 0.0
        if stage > LAST: return 1.0
        c = cs[stage - 1]
        return c * reach(stage + 1, fails) + (1 - c) * reach(stage, fails + 1)
    return cs, 1 - reach(1, 0)


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
    W100, pairs, usage = S.load(); heads_all = S.rd(os.path.join(S.D6, "heads.csv"))
    v = S.verify(W100, pairs, usage, heads_all)
    games = S.play_all(W100, v["heads"], v["copies"], L, N, SEED, 4, "hint", os.path.join(ROOT, "ichishuu", "_dict"))
    res = ["win" if g["result"] == "win" else "tenpai" if g["result"] == "tenpai" else "nowin" for g in games]
    c = Counter(res); wins, nowin = c["win"], c["nowin"]
    need = G.wins_needed
    runs, unused = run_stream(res, need)
    att = Counter(); ok = Counter(); over_at = Counter()
    for r in runs:
        for st, o in r["hist"]:
            att[st] += 1; ok[st] += o
        if r["over"]: over_at[r["hist"][-1][0]] += 1
    p = wins / (wins + nowin)
    cs, pover = analytic(p, need)
    out = dict(games=N, counts=dict(c), win_rate_of_all=100 * wins / N, tenpai_rate=100 * c["tenpai"] / N, p_win_per_consumed_game=p, need={s: need(s) for s in range(1, LAST + 1)},
               runs=len(runs), unused_games=unused, over=100 * sum(r["over"] for r in runs) / len(runs), over_count=sum(r["over"] for r in runs),
               cleared_last=100 * sum(r["cleared_last"] for r in runs) / len(runs),
               per_attempt_clear={s: dict(attempts=att[s], rate=100 * ok[s] / att[s]) for s in range(1, LAST + 1) if att[s]},
               over_at_stage={s: over_at[s] for s in range(1, LAST + 1)},
               analytic=dict(per_attempt_clear={s: 100 * cs[s - 1] for s in range(1, LAST + 1)}, game_over=100 * pover),
               games_per_run=dict(consumed_mean=statistics.mean(r["consumed"] for r in runs), consumed_median=statistics.median(r["consumed"] for r in runs), consumed_max=max(r["consumed"] for r in runs),
                                  played_mean=statistics.mean(r["played"] for r in runs), played_median=statistics.median(r["played"] for r in runs), played_max=max(r["played"] for r in runs)),
               first_digest=hashlib.sha256(json.dumps(res[:1000]).encode()).hexdigest()[:16])
    json.dump(out, open(os.path.join(ROOT, "ichishuu", "results_stage_lap1_20261010.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
