"""ひらがな麻雀(仮) シミュレーター。仕様は CLAUDE.md が正本。

  python3 simulator.py                      # 既定値で1回
  python3 simulator.py --sweep              # 未決パラメータのスイープ
  python3 simulator.py --pool-size 12 --draws 10 --heads-per-type 3

仕様の未決部分は以下の仮置き(すべてオプションで変更可):
- アガリ判定: 初期13枚で完成していれば0巡目アガリ。以降はツモ直後の14枚から
  1枚捨てて13枚が完成する形になれば、そのツモでアガリ(自摸直後判定と捨て後判定は等価)。
- 山: プールの各語が3牌を1セットずつ出す(共有牌は語数ぶん入る)+ 喘ぎ牌 6種 x heads-per-type 枚。
- 1手牌に同じ語は2回使えない。
- 翻: 4語の han_provisional の合計 + お題ワードが手に入っていれば +1。
  分割が複数あれば翻が最大の分け方を採用。
- CPU(初級): 捨て牌ごとに「完成語 +10 / 2牌揃い(残り1牌が山にある) +4 / 雀頭 +3」の
  最大スコアが高くなる牌を捨てる。
"""
import argparse
import csv
import os
import random
from collections import Counter
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
HEADS = ["お゛っ", "んぉ゛", "お゛ほ", "やん", "あん", "きゃん"]
HAND_SIZE = 13
N_WORDS = 4


def load_words(path=os.path.join(HERE, "words.csv")):
    with open(path, encoding="utf-8-sig") as f:
        return [
            dict(word=r["word"], tiles=r["tiles"].split("|"), han=int(r["han_provisional"]))
            for r in csv.DictReader(f)
        ]


class Pool:
    """1ラウンド分のプール。牌を整数IDに変換し、判定用の索引を持つ。"""

    def __init__(self, words, heads_per_type):
        self.words = words
        names = sorted({t for w in words for t in w["tiles"]}) + HEADS
        self.tid = {t: i for i, t in enumerate(names)}
        self.n_tiles = len(names)
        self.head_ids = [self.tid[h] for h in HEADS]
        self.word_tiles = [[self.tid[t] for t in w["tiles"]] for w in words]
        self.word_han = [w["han"] for w in words]
        self.word_counts = [Counter(ts) for ts in self.word_tiles]
        self.by_tile = {}
        for i, c in enumerate(self.word_counts):
            for t in c:
                self.by_tile.setdefault(t, []).append(i)
        wall = [t for ts in self.word_tiles for t in ts]
        wall += [h for h in self.head_ids for _ in range(heads_per_type)]
        self.wall_tiles = wall
        self.wall_counts = Counter(wall)
        self._win = {}
        self._score = {}

    # --- アガリ判定(厳密な分割。翻最大) ---
    def best_win(self, hand, topic):
        """13枚の手牌tupleを4語+雀頭に分割できれば (翻, 使用語index集合) を返す。不可なら None。"""
        key = (hand, topic)
        if key in self._win:
            return self._win[key]
        counts = Counter(hand)
        best = [None]

        def dfs(used, han, head_used):
            if not counts:
                if head_used and len(used) == N_WORDS:
                    total = han + (1 if topic in used else 0)
                    if best[0] is None or total > best[0][0]:
                        best[0] = (total, frozenset(used))
                return
            t = min(counts)
            if not head_used and t in self.head_ids_set:
                counts[t] -= 1
                if counts[t] == 0:
                    del counts[t]
                dfs(used, han, True)
                counts[t] = counts.get(t, 0) + 1
            if len(used) == N_WORDS:
                return
            for wi in self.by_tile.get(t, ()):
                if wi in used:
                    continue
                wc = self.word_counts[wi]
                if all(counts.get(k, 0) >= v for k, v in wc.items()):
                    for k, v in wc.items():
                        counts[k] -= v
                        if counts[k] == 0:
                            del counts[k]
                    used.add(wi)
                    dfs(used, han + self.word_han[wi], head_used)
                    used.discard(wi)
                    for k, v in wc.items():
                        counts[k] = counts.get(k, 0) + v

        dfs(set(), 0, False)
        self._win[key] = best[0]
        return best[0]

    @property
    def head_ids_set(self):
        if not hasattr(self, "_hs"):
            self._hs = set(self.head_ids)
        return self._hs

    # --- CPUの評価関数 ---
    def score(self, hand):
        if hand in self._score:
            return self._score[hand]
        counts = Counter(hand)
        cands = []  # (value, Counter of tiles consumed)
        for wi, wc in enumerate(self.word_counts):
            have = sum(min(counts.get(t, 0), n) for t, n in wc.items())
            if have == 3:
                cands.append((10, {t: min(counts[t], n) for t, n in wc.items()}))
            elif have == 2:
                got = {t: min(counts.get(t, 0), n) for t, n in wc.items() if counts.get(t, 0)}
                missing = [t for t, n in wc.items() if counts.get(t, 0) < n]
                if missing and self.wall_counts.get(missing[0], 0) > 0:
                    cands.append((4, got))
        best = 0

        def dfs(i, left, n, val):
            nonlocal best
            if val > best:
                best = val
            if n == N_WORDS:
                return
            for j in range(i, len(cands)):
                v, need = cands[j]
                if all(left.get(k, 0) >= c for k, c in need.items()):
                    for k, c in need.items():
                        left[k] -= c
                    dfs(j + 1, left, n + 1, val + v)
                    for k, c in need.items():
                        left[k] += c

        dfs(0, dict(counts), 0, 0)
        if any(h in counts for h in self.head_ids):
            best += 3
        self._score[hand] = best
        return best


def play_round(pool, topic, draws, rng):
    """1ラウンドを回す。戻り値は (アガったか, 巡目, 翻, 使用語index集合)。"""
    wall = pool.wall_tiles[:]
    rng.shuffle(wall)
    hand = sorted(wall[:HAND_SIZE])
    wall = wall[HAND_SIZE:]
    r = pool.best_win(tuple(hand), topic)
    if r:
        return True, 0, r[0], r[1]
    for turn in range(1, draws + 1):
        if not wall:
            break
        hand.append(wall.pop())
        # アガリ判定: 14枚から1枚捨てて13枚が完成するか
        win = None
        for t in set(hand):
            h = hand[:]
            h.remove(t)
            r = pool.best_win(tuple(sorted(h)), topic)
            if r and (win is None or r[0] > win[0]):
                win = r
        if win:
            return True, turn, win[0], win[1]
        # 初級CPU: スコアが最大になる牌を捨てる(同点はランダム)
        cands = []
        for t in set(hand):
            h = hand[:]
            h.remove(t)
            cands.append((pool.score(tuple(sorted(h))), rng.random(), t))
        _, _, d = max(cands)
        hand.remove(d)
    return False, None, 0, frozenset()


def simulate(words, sims, pool_size, draws, heads_per_type, seed):
    rng = random.Random(seed)
    n = len(words)
    stat = dict(wins=0, turn_sum=0, han_sum=0, topic_hit=0)
    turn_hist = Counter()
    in_pool = Counter()
    in_win = Counter()
    for _ in range(sims):
        idx = rng.sample(range(n), pool_size)
        pw = [words[i] for i in idx]
        pool = Pool(pw, heads_per_type)
        topic = rng.randrange(pool_size)
        for i in idx:
            in_pool[i] += 1
        ok, turn, han, used = play_round(pool, topic, draws, rng)
        if ok:
            stat["wins"] += 1
            stat["turn_sum"] += turn
            stat["han_sum"] += han
            turn_hist[turn] += 1
            if topic in used:
                stat["topic_hit"] += 1
            for wi in used:
                in_win[idx[wi]] += 1
    return stat, turn_hist, in_pool, in_win


def report(words, sims, pool_size, draws, heads, seed, detail=True):
    stat, hist, in_pool, in_win = simulate(words, sims, pool_size, draws, heads, seed)
    w = stat["wins"]
    print(f"--- プール{pool_size}語 / ツモ{draws}回 / 喘ぎ牌{heads}枚x6種 / {sims}ラウンド ---")
    print(f"アガリ率: {w / sims:.1%} ({w}/{sims})")
    if w:
        print(f"平均アガリ巡目: {stat['turn_sum'] / w:.2f}  (0=配牌アガリ)")
        print(f"平均翻: {stat['han_sum'] / w:.2f}")
        print(f"お題ワード達成率(アガリ中): {stat['topic_hit'] / w:.1%}  (全ラウンド中: {stat['topic_hit'] / sims:.1%})")
    if detail:
        print("巡目別アガリ数:", dict(sorted(hist.items())))
        print("\n語ごとの出現率(アガリ手に入った回数 / プールに入った回数):")
        rows = sorted(
            ((in_win[i] / in_pool[i] if in_pool[i] else 0, words[i]["word"], in_win[i], in_pool[i]) for i in range(len(words))),
            reverse=True,
        )
        for rate, name, a, b in rows:
            print(f"  {name:<8} {rate:6.1%}  ({a}/{b})")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=5000)
    ap.add_argument("--pool-size", type=int, default=14)
    ap.add_argument("--draws", type=int, default=9)
    ap.add_argument("--heads-per-type", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="語ごとの表を省略")
    a = ap.parse_args()
    words = load_words()
    if not a.sweep:
        report(words, a.sims, a.pool_size, a.draws, a.heads_per_type, a.seed, not a.quiet)
        return
    print(f"{'プール':>4} {'ツモ':>3} {'喘ぎ':>3} | {'アガリ率':>7} {'平均巡目':>7} {'平均翻':>6} {'お題達成':>7}")
    for pool_size in (10, 12, 14, 16, 18, 20):
        for draws in (8, 9, 10):
            for heads in (1, 2, 3):
                s, _, _, _ = simulate(words, a.sims, pool_size, draws, heads, a.seed)
                w = s["wins"]
                print(
                    f"{pool_size:>6} {draws:>3} {heads:>3} | {w / a.sims:>7.1%} "
                    f"{(s['turn_sum'] / w if w else 0):>8.2f} {(s['han_sum'] / w if w else 0):>6.2f} "
                    f"{(s['topic_hit'] / w if w else 0):>8.1%}"
                )


if __name__ == "__main__":
    main()
