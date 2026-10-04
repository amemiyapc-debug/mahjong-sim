"""ひらがな麻雀(仮) シミュレーター v1.1。仕様は CLAUDE.md(v1.1)が正本。

  pip install numpy
  python3 simulator.py                         # 既定値
  python3 simulator.py --games 50000 --targets 3000,5000,8000
  python3 simulator.py --pool-size 12 --heads 2-3 --max-tenpai-retries 3

仕様に従った部分:
- 山 = プールの各語が3牌を1セットずつ出す + 喘ぎ牌(6種から2〜3種を抽選、各1枚)。
- 手牌13枚。ツモ → 1枚捨てを最大10回。同じ語は1手牌で2回使えない。
- アガリ形 = 3牌語x4 + 喘ぎ牌1枚。分割が複数あれば翻最大を採用。
- 翻 = 形で1翻 + 役の加算(同じgroupは最高位のみ、groupなしは加算)。得点 = 翻 x 1,000。
- アガリ/ノーテンは1ゲーム消費、テンパイ流局は消費しない(1ランの上限回数まで)。
- テンパイ = 13枚の手牌のうち1枚を入れ替えれば完成形になり、その必要牌が山に残っている状態。

仮置き(オプションで変更可):
- アガリ判定は「ツモ直後の14枚から1枚捨てて13枚が完成するか」。配牌13枚での完成も0巡目アガリ。
- 上限回数(--max-tenpai-retries)に達した後のテンパイ流局は、ノーテン同様に1ゲーム消費。
- CPU(初級): 捨て牌ごとに「山に残っている牌だけで完成できる語セットのうち、手牌との一致枚数が
  最大のもの」を評価し、その値と到達経路の数が大きくなる牌を捨てる。
"""
import argparse
import csv
import itertools
import os
import random
from collections import Counter
from multiprocessing import Pool as ProcPool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HEADS = ["お゛っ", "んぉ゛", "お゛ほ", "やん", "あん", "きゃん"]
HAND = 13
N_WORDS = 4


# ---------------------------------------------------------------- データ読み込み
def read_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Data:
    def __init__(self):
        self.words = read_csv("words.csv")
        self.yaku = read_csv("yaku.csv")
        tiles = sorted({t for w in self.words for t in w["tiles"].split("|")}) + HEADS
        self.tid = {t: i for i, t in enumerate(tiles)}
        self.tiles = tiles
        self.T = len(tiles)
        self.head_idx = [self.tid[h] for h in HEADS]
        self.W = np.zeros((len(self.words), self.T), dtype=np.int8)
        for i, w in enumerate(self.words):
            for t in w["tiles"].split("|"):
                self.W[i, self.tid[t]] += 1
        self._yaku_cache = {}
        self._combos = {}

    def combos(self, n):
        if n not in self._combos:
            self._combos[n] = np.array(list(itertools.combinations(range(n), N_WORDS)), dtype=np.int16)
        return self._combos[n]

    # --- 役判定 ---
    def eval_yaku(self, word_ids):
        """4語(グローバルindexのfrozenset)に対する (総翻, 成立した役名のtuple)。"""
        if word_ids in self._yaku_cache:
            return self._yaku_cache[word_ids]
        ws = [self.words[i] for i in word_ids]
        names = {w["word"] for w in ws}
        mods = Counter(w["modifier"] for w in ws if w["modifier"])
        stems = Counter(w["stem"] for w in ws if w["stem"])
        parts = Counter(w["part"] for w in ws if w["part"] and w["part"] != "SM")
        pairs = {(w["modifier"], w["stem"]) for w in ws if w["modifier"] and w["stem"]}
        n_single = sum(w["type"] == "単独" for w in ws)
        n_tail = sum(w["modifier"] in ("穴", "媚") for w in ws)

        def ok(y):
            ct, p = y["condition_type"], y["params"]
            if ct == "count_same_modifier":
                return max(mods.values(), default=0) >= int(p)
            if ct == "count_same_stem":
                return max(stems.values(), default=0) >= int(p)
            if ct == "count_same_part":
                return max(parts.values(), default=0) >= int(p)
            if ct == "singles_eq":
                return n_single == int(p)
            if ct == "count_tail_modifier":
                return n_tail >= int(p)
            if ct == "count_in_set":
                kv = dict(x.split("=") for x in p.split(";"))
                return len(names & set(kv["set"].split("|"))) >= int(kv["min"])
            if ct == "contains_all":
                return any(set(g.split("|")) <= names for g in p.split("/"))
            if ct == "pair_same_stem_modifiers":
                m = p.split("|")
                return any(all((x, s) in pairs for x in m) for s in stems)
            raise ValueError(f"未対応のcondition_type: {ct}")

        hit = [y for y in self.yaku if ok(y)]
        best_in_group = {}
        for y in hit:
            g = y["group"]
            if g and (g not in best_in_group or int(y["han_provisional"]) > int(best_in_group[g]["han_provisional"])):
                best_in_group[g] = y
        chosen = [y for y in hit if not y["group"]] + list(best_in_group.values())
        han = 1 + sum(int(y["han_provisional"]) for y in chosen)
        res = (han, tuple(y["name"] for y in chosen))
        self._yaku_cache[word_ids] = res
        return res


_DATA = None


def data():
    global _DATA
    if _DATA is None:
        _DATA = Data()
    return _DATA


# ---------------------------------------------------------------- 1ゲーム
def play_game(rng, pool_size, max_draws, heads_range):
    """戻り値: ("win", 翻, 役名tuple, 巡目) / ("tenpai",) / ("noten",)"""
    d = data()
    idx = rng.sample(range(len(d.words)), pool_size)
    k = rng.randint(*heads_range)
    heads = [d.head_idx[i] for i in rng.sample(range(len(HEADS)), k)]

    Wp = d.W[idx]  # プール語 x 牌
    total = Wp.sum(axis=0).astype(np.int16)
    for h in heads:
        total[h] += 1
    wall = [t for t in range(d.T) for _ in range(total[t])]
    rng.shuffle(wall)

    # 完成形(4語+喘ぎ牌1枚)の全候補。行 = 候補、列 = 牌
    combo = d.combos(pool_size)
    S0 = Wp[combo].sum(axis=1).astype(np.int8)
    rows, row_combo = [], []
    for h in heads:
        s = S0.copy()
        s[:, h] += 1
        rows.append(s)
        row_combo.append(np.arange(len(combo)))
    S = np.concatenate(rows)
    row_combo = np.concatenate(row_combo)

    def eye(t):
        v = np.zeros(d.T, dtype=np.int8)
        v[t] = 1
        return v

    def best_complete(h):
        """手牌h(13枚以上)に完全に含まれる候補のうち翻最大のもの。なければNone。"""
        full = np.minimum(S, h).sum(axis=1) == HAND
        if not full.any():
            return None
        best = None
        for ci in set(row_combo[full].tolist()):
            gids = frozenset(idx[j] for j in combo[ci])
            han, names = d.eval_yaku(gids)
            if best is None or han > best[0]:
                best = (han, names)
        return best

    hand = np.zeros(d.T, dtype=np.int8)
    rem = total.astype(np.int16)  # 山に残っている牌
    for t in wall[:HAND]:
        hand[t] += 1
        rem[t] -= 1
    pos = HAND

    r = best_complete(hand)
    if r:
        return ("win", r[0], r[1], 0)

    final_best = 0
    for turn in range(1, max_draws + 1):
        if pos >= len(wall):
            break
        t = wall[pos]
        pos += 1
        hand[t] += 1
        rem[t] -= 1
        r = best_complete(hand)
        if r:
            return ("win", r[0], r[1], turn)

        # 初級CPU: 残り牌だけで完成できる候補のうち、一致枚数が最大になる牌を残す
        m14 = np.minimum(S, hand).sum(axis=1)
        feas14 = (np.clip(S - hand, 0, None) <= rem).all(axis=1)
        if feas14.any():
            top = m14[feas14].max()
            keep = feas14 & (m14 >= top - 1)
            Sk = S[keep]
        else:
            Sk = S[:0]
        best_key, best_t = None, None
        for c in np.nonzero(hand)[0]:
            h2 = hand.copy()
            h2[c] -= 1
            if len(Sk):
                m = np.minimum(Sk, h2).sum(axis=1)
                f = (np.clip(Sk - h2, 0, None) <= rem).all(axis=1)
                if f.any():
                    mm = m[f].max()
                    key = (int(mm), int((f & (m == mm)).sum()), rng.random())
                else:
                    key = (0, 0, rng.random())
            else:
                key = (0, 0, rng.random())
            if best_key is None or key > best_key:
                best_key, best_t = key, c
        hand[best_t] -= 1
        final_best = best_key[0]

    # テンパイ = 手牌13枚のうち1枚を入れ替えれば完成し、その必要牌が山に残っている
    return ("tenpai",) if final_best == HAND - 1 else ("noten",)


def worker(args):
    seed, n, pool_size, max_draws, heads_range = args
    rng = random.Random(seed)
    return [play_game(rng, pool_size, max_draws, heads_range) for _ in range(n)]


def run_games(n_games, pool_size, max_draws, heads_range, seed, procs):
    chunks = max(procs * 4, 1)
    per = [n_games // chunks + (1 if i < n_games % chunks else 0) for i in range(chunks)]
    jobs = [(seed * 100003 + i, per[i], pool_size, max_draws, heads_range) for i in range(chunks) if per[i]]
    if procs > 1:
        with ProcPool(procs) as p:
            parts = p.map(worker, jobs)
    else:
        parts = [worker(j) for j in jobs]
    return [g for part in parts for g in part]


# ---------------------------------------------------------------- 集計
def summarize(games, han_point):
    n = len(games)
    wins = [g for g in games if g[0] == "win"]
    tenpai = sum(g[0] == "tenpai" for g in games)
    noten = sum(g[0] == "noten" for g in games)
    out = {"n": n, "win": len(wins), "tenpai": tenpai, "noten": noten}
    out["han_hist"] = Counter(g[1] for g in wins)
    out["yaku"] = Counter(name for g in wins for name in g[2])
    out["yaku_none"] = sum(1 for g in wins if not g[2])
    out["turn_hist"] = Counter(g[3] for g in wins)
    out["avg_han"] = sum(g[1] for g in wins) / len(wins) if wins else 0.0
    out["avg_turn"] = sum(g[3] for g in wins) / len(wins) if wins else 0.0
    out["avg_score_per_game"] = sum(g[1] for g in wins) * han_point / n
    return out


def clear_rates(games, n_range, targets, retries, han_point, runs, seed):
    """ゲームは独立なので、結果を再抽選して1ランを再現し、(N, 目標点)ごとのクリア率を出す。
    戻り値: {上限R: ({(N, 目標点): クリア率}, 1ランあたりのテンパイ再抽選の平均回数)}"""
    rng = np.random.default_rng(seed)
    kind = np.array([0 if g[0] == "win" else 1 if g[0] == "tenpai" else 2 for g in games])
    score = np.array([g[1] * han_point if g[0] == "win" else 0 for g in games])
    n_max = max(n_range)
    res = {}
    for R in retries:
        cum = np.zeros(runs, dtype=np.int64)
        used = np.zeros(runs, dtype=np.int32)
        ret = np.zeros(runs, dtype=np.int32)
        cum_at = np.zeros((n_max + 1, runs), dtype=np.int64)
        while (used < n_max).any():
            act = used < n_max
            gi = rng.integers(0, len(games), size=runs)
            k, s = kind[gi], score[gi]
            free = act & (k == 1) & (ret < R)  # 消費しないテンパイ流局
            ret[free] += 1
            spend = act & ~free
            cum[spend] += s[spend]
            used[spend] += 1
            idx = np.nonzero(spend)[0]
            cum_at[used[idx], idx] = cum[idx]
        res[R] = {
            (N, T): float((cum_at[N] >= T).mean()) for N in n_range for T in targets
        }, float(ret.mean())
    return res


def print_report(args, games, heads_range):
    han_point = args.han_point
    s = summarize(games, han_point)
    n = s["n"]
    print(f"=== 設定: プール{args.pool_size}語 / 最大ツモ{args.max_draws}回 / 喘ぎ牌{heads_range[0]}〜{heads_range[1]}種x各1枚 / {n}ゲーム ===")
    print(f"アガリ率      : {s['win'] / n:6.1%}  ({s['win']}/{n})")
    print(f"テンパイ流局率: {s['tenpai'] / n:6.1%}  ({s['tenpai']}/{n})  ← ゲーム消費なし(上限あり)")
    print(f"ノーテン率    : {s['noten'] / n:6.1%}  ({s['noten']}/{n})  ← 1ゲーム消費")
    print(f"アガリ時の平均巡目: {s['avg_turn']:.2f}   平均翻: {s['avg_han']:.2f}")
    print(f"1ゲームあたり平均得点(全ゲーム): {s['avg_score_per_game']:.0f}点")
    print(f"巡目別アガリ数: {dict(sorted(s['turn_hist'].items()))}")

    print("\n[翻の分布](アガリ時、形1翻+役)")
    w = s["win"]
    for han in sorted(s["han_hist"]):
        c = s["han_hist"][han]
        print(f"  {han:>2}翻 ({han * han_point:>6}点): {c:>5}  {c / w:6.1%}  {'#' * round(40 * c / w)}")

    print("\n[役ごとの出現率]  分母A=アガリ手 / 分母B=全ゲーム")
    print(f"  {'役':<12}{'翻':>3}  {'アガリ手中':>8}  {'全ゲーム中':>8}")
    han_of = {y['name']: int(y['han_provisional']) for y in data().yaku}
    order = sorted(data().yaku, key=lambda y: -s["yaku"].get(y["name"], 0))
    for y in order:
        c = s["yaku"].get(y["name"], 0)
        print(f"  {y['name']:<12}{han_of[y['name']]:>3}  {c / w if w else 0:>9.1%}  {c / n:>9.2%}   ({c})")
    print(f"  {'(役なし=形のみ1翻)':<14}{'':>1}  {s['yaku_none'] / w if w else 0:>9.1%}  {s['yaku_none'] / n:>9.2%}   ({s['yaku_none']})")


def print_clear(args, games):
    targets = [int(x) for x in args.targets.split(",")]
    lo, hi = (int(x) for x in args.n_range.split("-"))
    n_range = list(range(lo, hi + 1))
    retries = [int(x) for x in args.max_tenpai_retries.split(",")]
    res = clear_rates(games, n_range, targets, retries, args.han_point, args.runs, args.seed)
    for R in retries:
        table, avg_ret = res[R]
        print(f"\n[クリア率] テンパイ流局の再抽選上限={R}回/ラン (実際の平均使用 {avg_ret:.2f}回)  {args.runs}ラン")
        print(f"  {'目標点':>7} |" + "".join(f"{'N=' + str(N):>7}" for N in n_range))
        for T in targets:
            print(f"  {T:>7} |" + "".join(f"{table[(N, T)]:>7.1%}" for N in n_range))


def parse_range(s):
    a, _, b = s.partition("-")
    return (int(a), int(b or a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=20000, help="1ゲームのシミュレーション回数")
    ap.add_argument("--pool-size", type=int, default=14)
    ap.add_argument("--max-draws", type=int, default=10)
    ap.add_argument("--heads", default="2-3", help="喘ぎ牌の種類数(各1枚)。例: 2-3 / 3")
    ap.add_argument("--han-point", type=int, default=1000, help="1翻あたりの点数")
    ap.add_argument("--n-range", default="3-8", help="規定ゲーム数Nの範囲")
    ap.add_argument("--targets", default="2000,3000,4000,6000,8000,10000", help="目標点(カンマ区切り)")
    ap.add_argument("--max-tenpai-retries", default="0,3,10", help="テンパイ流局の再抽選上限/ラン(カンマ区切りで複数可)")
    ap.add_argument("--runs", type=int, default=200000, help="クリア率計算のラン数")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args()

    heads_range = parse_range(args.heads)
    games = run_games(args.games, args.pool_size, args.max_draws, heads_range, args.seed, args.procs)
    print_report(args, games, heads_range)
    print_clear(args, games)


if __name__ == "__main__":
    main()
