"""ひらがな麻雀(仮) v1.3m: 役の判定・合体・翻の選択(14牌形)。仕様は CLAUDE.md(v1.3m)§4・§6。

judge14 が返す分割(4語+雀頭)ごとに、次を行う。
  1. 全ての役(yaku.csv)を判定する(雀頭の条件・ぉ゛の枚数 variant_count を含む)。
  2. group の絞り込み: 同じ group は、成立している中で tier 最大の1つだけ。group なしは全部。
     同じ役名の行は、1回だけ加算する(先に有効な行の翻)。
  3. 合体(yaku_merge.csv): group の絞り込みの【前】に成立している役で判定する。
     各役は1つの合体にだけ使う / 同時に成立する合体は最大2つ / 翻が最大の組み合わせ /
     合体は、元の役が「実際に加算していた翻」(絞り込みで消えていた役は0)を、合体の翻に置き換える / 連鎖なし。
  4. 分割のうち、翻が最大のものを採用する(同点は、役の数が多いほう、それも同じなら先に見つけたほう)。
翻 = 形1翻 + 役の加算 + (合体による置き換えの差分)。

  python3 yaku14.py --dir v13m "ちんぽ|..."   # (使い方は sim14.py / tests/test_yaku14.py を参照)
"""
import csv
import itertools
import os
from collections import Counter

from judge14 import Judge14

PARTS4 = ("男性器", "女性器", "胸", "後ろ")
MAX_MERGES = 2


def read_rows(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def kv(params):
    out = {}
    for x in params.split(";"):
        k, _, v = x.partition("=")
        out[k] = v
    return out


class Scorer:
    def __init__(self, d, judge=None, merge_limit=MAX_MERGES):
        P = lambda n: os.path.join(d, n)
        self.judge = judge or Judge14(P("words.csv"), P("heads.csv"), P("tile_variants.csv"))
        self.W = self.judge.words
        self.H = self.judge.heads
        self.Y = read_rows(P("yaku.csv"))
        self.M = read_rows(P("yaku_merge.csv")) if os.path.exists(P("yaku_merge.csv")) else []
        self.merge_limit = merge_limit
        self.nw = len(self.W)
        self.widx = {w["word"]: i for i, w in enumerate(self.W)}
        self.mods = [[m for m in (w.get("modifiers") or w["modifier"]).split("|") if m] for w in self.W]
        self._compile()
        self.han = [int(y["han_provisional"]) for y in self.Y]
        self.msrc = [m["source_yaku"].split("|") for m in self.M]
        self.mhan = [int(m["han_provisional"]) for m in self.M]
        names = {y["name"] for y in self.Y}
        for m, src in zip(self.M, self.msrc):
            assert all(s in names for s in src), ("合体の元の役が、yaku.csvにない", m["name"], src)
        self._word_cache = {}
        self._score_cache = {}

    # ---------------- 役の条件 ----------------
    def _mask(self, pred):
        return sum(1 << i for i, w in enumerate(self.W) if pred(i, w))

    def token_mask(self, tok):
        if tok.startswith("mod:"):
            return self._mask(lambda i, w: tok[4:] in self.mods[i])
        if tok.startswith("pos:"):
            return self._mask(lambda i, w: w["position"] == tok[4:])
        if tok.startswith("stem:"):
            return self._mask(lambda i, w: w["stem"] == tok[5:])
        if tok.startswith("part:"):
            return self._mask(lambda i, w: w["part"] == tok[5:])
        if tok not in self.widx:
            raise ValueError("辞書にない語: " + tok)
        return 1 << self.widx[tok]

    def set_mask(self, toks):
        m = 0
        for t in toks:
            m |= self.token_mask(t)
        return m

    def _compile(self):
        W = self.W
        part_mask = {p: self._mask(lambda i, w, p=p: w["part"] == p) for p in PARTS4}
        tail_part = {p: self._mask(lambda i, w, p=p: w["part"] == p and w["position"] == "語尾") for p in PARTS4}
        singles = self._mask(lambda i, w: w["type"] == "単独")
        pc = lambda x: x.bit_count()
        stems = sorted({w["stem"] for w in W if w["stem"]})
        mod_names = sorted({m for ms in self.mods for m in ms})
        # 同じ語幹 X の、修飾牌 m を使う語(修飾牌1つの語)
        sm_mask = {(s, m): self._mask(lambda i, w, s=s, m=m: w["stem"] == s and self.mods[i] == [m]) for s in stems for m in mod_names}
        self.word_rows, self.head_rows = [], []   # (行index, 関数)
        for ri, y in enumerate(self.Y):
            ct, p = y["condition_type"], y["params"]
            f = None; head = False
            if ct == "count_same_modifier":
                a = kv(p); m = self.token_mask("mod:" + a["mod"]); n = int(a["n"]); f = lambda s, m=m, n=n: pc(s & m) >= n
            elif ct == "count_same_stem":
                a = kv(p); m = self.token_mask("stem:" + a["stem"]); n = int(a["n"]); f = lambda s, m=m, n=n: pc(s & m) >= n
            elif ct == "count_same_part":
                n = int(kv(p)["n"]); f = lambda s, n=n: any(pc(s & pm) >= n for pm in part_mask.values())
            elif ct == "count_tail_same_part":
                n = int(kv(p)["n"]); f = lambda s, n=n: any(pc(s & tm) >= n for tm in tail_part.values())
            elif ct == "singles_eq":
                n = int(kv(p)["n"]); f = lambda s, n=n: pc(s & singles) == n
            elif ct == "count_in_set":
                a = kv(p); m = self.set_mask(a["set"].split("|")); n = int(a["min"]); f = lambda s, m=m, n=n: pc(s & m) >= n
            elif ct == "all_in_set":
                m = self.set_mask(kv(p)["set"].split("|")); f = lambda s, m=m: s & ~m == 0
            elif ct == "contains_all":
                alts = [[self.token_mask(t) for t in g.split("|")] for g in p.split("/")]
                f = lambda s, alts=alts: any(all(s & tm for tm in g) for g in alts)
            elif ct == "one_from_each":
                gm = [self.set_mask(g.split("|")) for g in p.split(";")]
                f = lambda s, gm=gm: self._assign(gm, s)
            elif ct == "pair_same_stem_modifiers":
                ms = p.split("|")
                f = lambda s, ms=ms: any(all(s & sm_mask[(st, m)] for m in ms) for st in stems)
            elif ct == "count_part":
                a = kv(p); m = self.token_mask("part:" + a["part"]); n = int(a["n"]); f = lambda s, m=m, n=n: pc(s & m) >= n
            elif ct == "stem_pairs":
                P_ = int(kv(p)["pairs"])
                def f(s, P_=P_):
                    cs = Counter(W[i]["stem"] for i in self._bits(s) if W[i]["stem"])
                    return sum(1 for v in cs.values() if v == 2) == P_
            elif ct == "distinct_stems":
                def f(s):
                    st = [W[i]["stem"] for i in self._bits(s)]
                    return all(st) and len(set(st)) == 4
            elif ct == "distinct_modifiers":
                def f(s):
                    ms = [self.mods[i] for i in self._bits(s)]
                    if not all(len(m) >= 1 for m in ms):
                        return False
                    flat = [x for m in ms for x in m]
                    return len(set(flat)) == len(flat)
            elif ct == "modifier_pairs":
                P_ = int(kv(p)["pairs"])
                def f(s, P_=P_):
                    ms = [self.mods[i] for i in self._bits(s)]
                    if not all(len(m) == 1 for m in ms):
                        return False
                    cm = Counter(m[0] for m in ms)
                    return sum(1 for v in cm.values() if v == 2) == P_
            elif ct == "position_split":
                a = kv(p); h_, t_ = int(a["head"]), int(a["tail"])
                def f(s, h_=h_, t_=t_):
                    pos = [W[i]["position"] for i in self._bits(s)]
                    return pos.count("語頭") == h_ and pos.count("語尾") == t_
            elif ct == "part_pairs":
                P_ = int(kv(p)["pairs"])
                def f(s, P_=P_):
                    cp = Counter(W[i]["part"] for i in self._bits(s) if W[i]["part"] in PARTS4)
                    return sum(1 for v in cp.values() if v == 2) == P_
            elif ct == "head_is":
                hs = kv(p)["head"].split("|"); head = True
                f = lambda s, h, o, hs=hs: self.H[h]["head"] in hs
            elif ct == "head_flavor":
                fl = kv(p)["flavor"]; head = True
                f = lambda s, h, o, fl=fl: self.H[h]["type"] == "喘ぎ声" and self.H[h]["flavor"] == fl
            elif ct == "head_stem_match":
                a = kv(p); m = self.token_mask("stem:" + a["stem"]); n = int(a["min"]); st = a["stem"]; head = True
                f = lambda s, h, o, m=m, n=n, st=st: self.H[h]["type"] == "略称" and self.H[h]["stem"] == st and pc(s & m) >= n
            elif ct == "head_part_match":
                head = True
                def f(s, h, o):
                    hh = self.H[h]
                    return hh["type"] == "略称" and (hh["flavor"] in PARTS4 or hh["flavor"] == "SM") and \
                        any(W[i]["part"] == hh["flavor"] for i in self._bits(s))
            elif ct == "variant_count":
                a = kv(p); n = int(a["min"]); head = True
                assert a["tile"] == self.judge.oho_tile, "variant_count は ぉ゛ だけ対応"
                f = lambda s, h, o, n=n: o >= n
            else:
                raise ValueError("未対応の条件: " + ct)
            (self.head_rows if head else self.word_rows).append((ri, f))

    @staticmethod
    def _bits(s):
        out = []
        while s:
            b = s & -s
            out.append(b.bit_length() - 1)
            s ^= b
        return out

    def _assign(self, gm, s, i=0, used=0):
        """各グループに、別々の語を割り当てられるか(手の4語から)。"""
        if i == len(gm):
            return True
        g = gm[i]
        for b in self._bits(s & g & ~used):
            if self._assign(gm, s, i + 1, used | (1 << b)):
                return True
        return False

    # ---------------- 判定 ----------------
    def raw_hits(self, words, head, oho):
        """成立している役の行index(group の絞り込み前)。words は4語のindex。"""
        s = 0
        for w in words:
            s |= 1 << w
        wh = self._word_cache.get(s)
        if wh is None:
            wh = [ri for ri, f in self.word_rows if f(s)]
            self._word_cache[s] = wh
        return sorted(wh + [ri for ri, f in self.head_rows if f(s, head, oho)])

    def reduce(self, hits):
        """group の絞り込みと、同名の役の1回加算。{役名: 加算された翻}(定義順)を返す。"""
        best = {}
        for ri in hits:
            g = self.Y[ri]["group"]
            if g:
                key = int(self.Y[ri]["tier"] or 0)
                if g not in best or key > best[g][0]:
                    best[g] = (key, ri)
        keep = [ri for ri in hits if not self.Y[ri]["group"] or best[self.Y[ri]["group"]][1] == ri]
        added = {}
        for ri in keep:
            added.setdefault(self.Y[ri]["name"], self.han[ri])
        return added

    def choose_merges(self, raw_names, added):
        """成立している合体から、翻の増分が最大になる組み合わせ(最大 merge_limit 個、元の役は重ならない)を選ぶ。
        戻り値: (選んだ合体のindexのtuple, 増分)"""
        cand = []
        for mi, src in enumerate(self.msrc):
            if all(s in raw_names for s in src):
                cand.append((mi, self.mhan[mi] - sum(added.get(s, 0) for s in src)))
        best, best_d = (), 0
        for k in range(1, self.merge_limit + 1):
            for combo in itertools.combinations(cand, k):
                used = [s for mi, _ in combo for s in self.msrc[mi]]
                if len(set(used)) != len(used):
                    continue
                d = sum(x for _, x in combo)
                if d > best_d:
                    best, best_d = tuple(mi for mi, _ in combo), d
        return best, best_d

    def score(self, words, head, oho):
        """1つの分割の翻。戻り値 dict(han, yaku=[役名...], merges=[合体名...], raw=[成立した役名...])。"""
        key = (tuple(words), head, min(oho, 2))
        r = self._score_cache.get(key)
        if r is not None:
            return r
        hits = self.raw_hits(words, head, oho)
        added = self.reduce(hits)
        raw_names = {self.Y[ri]["name"] for ri in hits}
        mer, delta = self.choose_merges(raw_names, added) if self.M else ((), 0)
        han = 1 + sum(added.values()) + delta
        used = {s for mi in mer for s in self.msrc[mi]}
        r = dict(han=han, han_no_merge=1 + sum(added.values()), yaku=[n for n in added if n not in used],
                 merges=[self.M[mi]["name"] for mi in mer], raw=sorted(raw_names), added=added)
        if len(self._score_cache) < 3_000_000:
            self._score_cache[key] = r
        return r

    def best(self, hand):
        """14牌の手から、翻が最大の分割を選ぶ。アガリでなければ None。
        戻り値: score() の dict + words / head / parts(分割の数)。"""
        parts = self.judge.partitions(hand)
        if not parts:
            return None
        best = None
        for ws, h, oho, chu in parts:
            r = self.score(ws, h, oho)
            k = (r["han"], len(r["yaku"]) + len(r["merges"]))
            if best is None or k > best[0]:
                best = (k, ws, h, r)
        _, ws, h, r = best
        out = dict(r)
        out.update(words=ws, head=h, parts=len(parts))
        return out
