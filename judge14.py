"""ひらがな麻雀(仮) v1.3: アガリ判定(14牌形)。

14牌 = words.csv の別々の4語(各3牌) + heads.csv の雀頭1語(2牌) に、過不足なく分割できればアガリ。
- 牌は順序なしの多重集合として扱う。同じ語は1手牌に2回使えない(雀頭は別の辞書)。
- 分割が複数あるときは、すべて返す(翻の選択・役は扱わない)。
- 修飾牌3つの語(modifiers列)も、通常の語と同じ3牌語として扱う。
- 牌の変種(tile_variants.csv。variants_csv を渡したときだけ有効):
  っ=つ(互換) / ぉ゛=お(置き換え): 判定では、つ・おとして数える。
  ちゅ→つ(一方向): ちゅは、つの代わりにも使える。つは、ちゅの代わりにならない。ちゅを何枚「つ」として使うかを、
  0枚から全部まですべて試して、成立するものを、すべて返す。
- 結果は、分割ごとに (語indexのtuple, 雀頭index, ぉ゛の枚数, ちゅを「つ」として使った枚数) 。
  ぉ゛の枚数は、手牌の14牌に含まれるぉ゛の数(分割に依らない)。役の判定で使う。

  python3 judge14.py --words data_v13/words.csv --heads data_v13/heads.csv   # 簡単な動作例
"""
import csv
from collections import Counter, defaultdict


def read_rows(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Judge14:
    def __init__(self, words_csv, heads_csv, variants_csv=None):
        self.words = read_rows(words_csv)
        self.heads = read_rows(heads_csv)
        self.variants = read_rows(variants_csv) if variants_csv else []
        # 置き換え(replace): 牌 -> もとの牌 / 一方向の代用(flex): ちゅ -> つ
        self.replace = {v["tile"]: v["base"] for v in self.variants if v["mode"] == "replace"}
        self.flex = [(v["tile"], v["base"]) for v in self.variants if v["mode"] == "flex"]
        self.oho_tile = next((v["tile"] for v in self.variants if v["base"] == "お" and v["mode"] == "replace"), None)
        norm = lambda t: self.replace.get(t, t)
        self.word_tiles = [Counter(norm(t) for t in w["tiles"].split("|")) for w in self.words]
        self.head_tiles = [Counter(norm(t) for t in h["tiles"].split("|")) for h in self.heads]
        for w, c in zip(self.words, self.word_tiles):
            assert sum(c.values()) == 3, ("3牌でない語", w["word"])
        for h, c in zip(self.heads, self.head_tiles):
            assert sum(c.values()) == 2, ("2牌でない雀頭", h["head"])
        # 牌 -> その牌を含む語/雀頭のindex
        self.words_by_tile = defaultdict(list)
        for i, c in enumerate(self.word_tiles):
            for t in c:
                self.words_by_tile[t].append(i)
        self.heads_by_tile = defaultdict(list)
        for i, c in enumerate(self.head_tiles):
            for t in c:
                self.heads_by_tile[t].append(i)
        # 辞書に出てくる牌(CSVの文字どおり。っ・ちゅを含む)と、変種の牌(ぉ゛)
        self.tiles = sorted({t for r in self.words for t in r["tiles"].split("|")}
                            | {t for r in self.heads for t in r["tiles"].split("|")})
        self.variant_tiles = sorted(set(self.replace) | {t for t, _ in self.flex})

    def partitions(self, hand):
        """手牌(牌の文字列のリスト、14枚)の分割を、すべて返す。判定の入り口。
        戻り値: [(語indexのtuple(昇順, 4つ), 雀頭index, ぉ゛の枚数, ちゅを「つ」として使った枚数), ...]。
        アガリでなければ []。"""
        if len(hand) != 14:
            return []
        base = Counter(self.replace.get(t, t) for t in hand)
        oho = sum(1 for t in hand if t == self.oho_tile) if self.oho_tile else 0
        found = set()
        # ちゅ(flex)を、b枚だけ つ として使う、すべての場合
        interps = [(base, 0)]
        for ftile, fbase in self.flex:
            nxt = []
            for c0, used0 in interps:
                for b in range(c0.get(ftile, 0) + 1):
                    c1 = Counter(c0)
                    c1[ftile] -= b
                    c1[fbase] += b
                    nxt.append((c1, used0 + b))
            interps = nxt
        for c, used in interps:
            for ws, h in self._partitions_exact(c):
                found.add((ws, h, oho, used))
        return sorted(found)

    def _partitions_exact(self, c):
        """牌の多重集合c(変種を展開済み)を、別々の4語+雀頭に過不足なく分ける、すべての分割(語index, 雀頭index)。"""
        found = set()
        chosen = []

        def fits(need):
            return all(c.get(t, 0) >= n for t, n in need.items())

        def take(need, sign):
            for t, n in need.items():
                c[t] -= sign * n

        def dfs(head):
            # 残っている牌のうち最小の牌を、必ず、どれかの語(または雀頭)が覆う
            t = min((k for k, v in c.items() if v > 0), default=None)
            if t is None:
                if len(chosen) == 4 and head is not None:
                    found.add((tuple(sorted(chosen)), head))
                return
            if len(chosen) < 4:
                for wi in self.words_by_tile.get(t, ()):
                    need = self.word_tiles[wi]
                    if wi in chosen or not fits(need):  # 同じ語は2回使えない
                        continue
                    take(need, 1)
                    chosen.append(wi)
                    dfs(head)
                    chosen.pop()
                    take(need, -1)
            if head is None:
                for hi in self.heads_by_tile.get(t, ()):
                    need = self.head_tiles[hi]
                    if not fits(need):
                        continue
                    take(need, 1)
                    dfs(hi)
                    take(need, -1)

        dfs(None)
        return found

    def is_win(self, hand):
        return bool(self.partitions(hand))

    def describe(self, partition):
        ws, h = partition[0], partition[1]
        return [self.words[i]["word"] for i in ws], self.heads[h]["head"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", default="data_v13/words.csv")
    ap.add_argument("--heads", default="data_v13/heads.csv")
    ap.add_argument("--variants", default="data_v13/tile_variants.csv")
    a = ap.parse_args()
    j = Judge14(a.words, a.heads, a.variants)
    print(f"語{len(j.words)} / 雀頭{len(j.heads)} / 牌の種類{len(j.tiles)}")
    ix = {w["word"]: i for i, w in enumerate(j.words)}
    hand = []
    for nm in ("ちんぽ", "まんこ", "あなる", "いくっ"):
        hand += j.words[ix[nm]]["tiles"].split("|")
    hand += j.heads[0]["tiles"].split("|")
    print("例:", [(j.describe(p), p[2], p[3]) for p in j.partitions(hand)])
    hand2 = [("っ" if t == "つ" else t) for t in hand] + []
    print("変種の例(ちゅ・っ・ぉ゛):", [(j.describe(p), p[2], p[3]) for p in j.partitions(["ちゅ", "ぉ゛"] + hand[2:])][:2])
