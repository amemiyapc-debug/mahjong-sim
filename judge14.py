"""ひらがな麻雀(仮) v1.3: アガリ判定(14牌形)。

14牌 = words.csv の別々の4語(各3牌) + heads.csv の雀頭1語(2牌) に、過不足なく分割できればアガリ。
- 牌は順序なしの多重集合として扱う。同じ語は1手牌に2回使えない(雀頭は別の辞書)。
- 分割が複数あるときは、すべて返す(翻の選択・役は扱わない)。
- 修飾牌3つの語(modifiers列)も、通常の語と同じ3牌語として扱う。
- 牌の変種(ぉ゛・っ・ちゅ)は扱わない。牌は、CSVの tiles 列の文字列どおりに区別する。

  python3 judge14.py --words data_v13/words.csv --heads data_v13/heads.csv   # 簡単な動作例
"""
import csv
from collections import Counter, defaultdict


def read_rows(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Judge14:
    def __init__(self, words_csv, heads_csv):
        self.words = read_rows(words_csv)
        self.heads = read_rows(heads_csv)
        self.word_tiles = [Counter(w["tiles"].split("|")) for w in self.words]
        self.head_tiles = [Counter(h["tiles"].split("|")) for h in self.heads]
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
        self.tiles = sorted({t for c in self.word_tiles + self.head_tiles for t in c})

    def partitions(self, hand):
        """手牌(牌の文字列のリスト、14枚)の分割を、すべて返す。
        戻り値: [(語indexのtuple(昇順, 4つ), 雀頭index), ...]。アガリでなければ []。"""
        if len(hand) != 14:
            return []
        c = Counter(hand)
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
        return sorted(found)

    def is_win(self, hand):
        return bool(self.partitions(hand))

    def describe(self, partition):
        ws, h = partition
        return [self.words[i]["word"] for i in ws], self.heads[h]["head"]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", default="data_v13/words.csv")
    ap.add_argument("--heads", default="data_v13/heads.csv")
    a = ap.parse_args()
    j = Judge14(a.words, a.heads)
    print(f"語{len(j.words)} / 雀頭{len(j.heads)} / 牌の種類{len(j.tiles)}")
    ix = {w["word"]: i for i, w in enumerate(j.words)}
    hand = []
    for nm in ("ちんぽ", "まんこ", "あなる", "いくっ"):
        hand += j.words[ix[nm]]["tiles"].split("|")
    hand += j.heads[0]["tiles"].split("|")
    print("例:", [j.describe(p) for p in j.partitions(hand)])
