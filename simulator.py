"""ひらがな麻雀(仮) シミュレーター v1.2。仕様は CLAUDE.md(v1.2)が正本。

  pip install numpy
  python3 simulator.py                          # 既定(誤差±1ptまで自動で回す)
  python3 simulator.py --games 50000            # ゲーム数を固定
  python3 simulator.py --targets 6000,8000,10000 --break-policies none,4

構成:
  1. 役の数え上げ(4語の全組み合わせ C(63,4) を直接判定。シミュレーション不要)
  2. 1ゲームのシミュレーション(強CPU・弱CPUを同じ配牌・同じ山で比較 = 共通乱数)
  3. 1ランの再現(ゲーム結果を再抽選。積み点・バースト・テンパイを崩す方針)

仕様どおりの部分(CLAUDE.md §2〜§6):
- 山 = プール14語の各語3牌を1セットずつ + 喘ぎ牌(6種から2〜3種、各1枚)。ダミー牌なし。
- 手牌13枚。ツモ→1枚捨てを最大10回。ツモ直後の14枚から1枚捨てて13枚が完成ならアガリ。
- 同じ語は1手牌に2回使えない。お題ワードは無効。
- 翻 = 形1翻 + 役の加算。同じgroupは条件を満たす中でtierが最大の1つだけ。groupなしは全て加算。
- アガリ: 1ゲーム消費、得点 = 翻x1,000 + 積み点。ノーテン: 1ゲーム消費、積み点と連続数をリセット。
  テンパイ流局: 消費なし、連続1回ごとに500点を積む。連続4回目でバースト(即ゲームオーバー)。
- テンパイ = 10回目のツモ・捨ての後、13枚のうち1枚を入れ替えれば完成形になり、その必要牌が山に残っている。

仮置き:
- 積み点は一律500点/回(回数に比例して増やさない)。
- 語尾そろい(count_tail_same_part)は、count_same_partに合わせてSMを同じ部位として数えない。
- テンパイを崩す方針: none=崩せない / K=「連続数がK回目になるテンパイ」を崩してノーテンにする
  (崩した場合は1ゲーム消費・積み点と連続数を失う。崩せるのは、テンパイにならない捨て牌が存在するとき)。
- 強CPU = 山の残りで完成できる語セットのうち、手牌との一致枚数が最大のものに寄せる(到達経路の数でも比較)。
  弱CPU = 山の残りは見ず、完成形との一致枚数が最大になる牌を残すだけ(同点はランダム)。
"""
import argparse
import csv
import itertools
import math
import os
import random
import sys
import time
from collections import Counter
from multiprocessing import Pool as ProcPool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HEADS = ["お゛っ", "んぉ゛", "お゛ほ", "やん", "あん", "きゃん"]
HAND = 13
N_WORDS = 4
CPUS = ("strong", "weak")
CPU_LABEL = {"strong": "強CPU", "weak": "弱CPU"}


# ---------------------------------------------------------------- データ・役の判定
def read_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def popcount(x):
    return x.bit_count()


class Data:
    def __init__(self):
        self.words = read_csv("words.csv")
        self.yaku = read_csv("yaku.csv")
        self.nw = len(self.words)
        tiles = sorted({t for w in self.words for t in w["tiles"].split("|")}) + HEADS
        self.tid = {t: i for i, t in enumerate(tiles)}
        self.T = len(tiles)
        self.head_idx = [self.tid[h] for h in HEADS]
        self.W = np.zeros((self.nw, self.T), dtype=np.int8)
        for i, w in enumerate(self.words):
            for t in w["tiles"].split("|"):
                self.W[i, self.tid[t]] += 1
        self._combos = {}
        self._eval_cache = {}
        self._compile_yaku()

    def combos(self, n):
        if n not in self._combos:
            self._combos[n] = np.array(list(itertools.combinations(range(n), N_WORDS)), dtype=np.int16)
        return self._combos[n]

    # --- 語のビットマスク ---
    def _mask(self, pred):
        return sum(1 << i for i, w in enumerate(self.words) if pred(w))

    def token_mask(self, tok):
        """語名、または mod:X / stem:X / part:X セレクターを、語のビットマスクにする。"""
        if tok.startswith("mod:"):
            return self._mask(lambda w: w["modifier"] == tok[4:])
        if tok.startswith("stem:"):
            return self._mask(lambda w: w["stem"] == tok[5:])
        if tok.startswith("part:"):
            return self._mask(lambda w: w["part"] == tok[5:])
        m = self._mask(lambda w: w["word"] == tok)
        if not m:
            raise ValueError(f"yaku.csvに、words.csvに存在しない語がある: {tok}")
        return m

    def _compile_yaku(self):
        parts = sorted({w["part"] for w in self.words if w["part"] and w["part"] != "SM"})
        part_mask = {p: self._mask(lambda w, p=p: w["part"] == p) for p in parts}
        tail_mask = self._mask(lambda w: w["position"] == "語尾")
        singles = self._mask(lambda w: w["type"] == "単独")
        stems = sorted({w["stem"] for w in self.words if w["stem"]})
        mods = sorted({w["modifier"] for w in self.words if w["modifier"]})
        pair_mask = {
            (m, s): self._mask(lambda w, m=m, s=s: w["modifier"] == m and w["stem"] == s)
            for m in mods for s in stems
        }

        def kv(params):
            return dict(x.split("=", 1) for x in params.split(";"))

        def assign(masks, bits, i=0, used=0):
            """各グループ(masks[i])に、別々の語(bits)を割り当てられるか。"""
            if i == len(masks):
                return True
            for b in bits:
                if not used & b and masks[i] & b and assign(masks, bits, i + 1, used | b):
                    return True
            return False

        self.fns = []
        for y in self.yaku:
            ct, p = y["condition_type"], y["params"]
            if ct == "count_same_modifier":
                a = kv(p); m = self._mask(lambda w, a=a: w["modifier"] == a["mod"]); n = int(a["n"])
                fn = lambda s, m=m, n=n: popcount(s & m) >= n
            elif ct == "count_same_stem":
                a = kv(p); m = self._mask(lambda w, a=a: w["stem"] == a["stem"]); n = int(a["n"])
                fn = lambda s, m=m, n=n: popcount(s & m) >= n
            elif ct == "count_same_part":
                n = int(kv(p)["n"])
                fn = lambda s, n=n: any(popcount(s & pm) >= n for pm in part_mask.values())
            elif ct == "count_tail_same_part":
                n = int(kv(p)["n"])
                fn = lambda s, n=n: any(popcount(s & tail_mask & pm) >= n for pm in part_mask.values())
            elif ct == "singles_eq":
                n = int(kv(p)["n"])
                fn = lambda s, n=n: popcount(s & singles) == n
            elif ct == "count_in_set":
                a = kv(p); m = sum(self.token_mask(t) for t in a["set"].split("|")); n = int(a["min"])
                fn = lambda s, m=m, n=n: popcount(s & m) >= n
            elif ct == "all_in_set":
                m = sum(self.token_mask(t) for t in kv(p)["set"].split("|"))
                fn = lambda s, m=m: s & ~m == 0
            elif ct == "contains_all":
                alts = [[self.token_mask(t) for t in g.split("|")] for g in p.split("/")]
                fn = lambda s, alts=alts: any(all(s & tm for tm in g) for g in alts)
            elif ct == "one_from_each":
                gm = [sum(self.token_mask(t) for t in g.split("|")) for g in p.split(";")]
                def fn(s, gm=gm):
                    if not all(s & g for g in gm):
                        return False
                    bits = [1 << i for i in range(self.nw) if s >> i & 1]
                    return assign(gm, bits)
            elif ct == "pair_same_stem_modifiers":
                ms = p.split("|")
                fn = lambda s, ms=ms: any(all(s & pair_mask[(m, st)] for m in ms) for st in stems)
            else:
                raise ValueError(f"未対応のcondition_type: {ct}")
            self.fns.append(fn)

    def eval_mask(self, s):
        """4語(ビットマスク)の (総翻, 適用された役の行index tuple)。"""
        r = self._eval_cache.get(s)
        if r is None:
            r = self.apply_hits(self.raw_hits(s))
            if len(self._eval_cache) < 2_000_000:
                self._eval_cache[s] = r
        return r

    def apply_hits(self, hits):
        """成立した役(行index)から、groupごとにtier最大の1つだけを残して翻を合計する。"""
        best = {}
        chosen = []
        for i in hits:
            y = self.yaku[i]
            g = y["group"]
            if not g:
                chosen.append(i)
                continue
            key = (int(y["tier"] or 0), int(y["han_provisional"]))
            if g not in best or key > best[g][0]:
                best[g] = (key, i)
        chosen += [i for _, i in best.values()]
        han = 1 + sum(int(self.yaku[i]["han_provisional"]) for i in chosen)
        return han, tuple(sorted(chosen))

    def raw_hits(self, s):
        return [i for i, fn in enumerate(self.fns) if fn(s)]


_DATA = None


def data():
    global _DATA
    if _DATA is None:
        _DATA = Data()
    return _DATA


# ---------------------------------------------------------------- 1. 役の数え上げ
def _enum_worker(a):
    d = data()
    hits = [0] * len(d.yaku)
    applied = [0] * len(d.yaku)
    n = 0
    for b, c, e in itertools.combinations(range(a + 1, d.nw), 3):
        s = (1 << a) | (1 << b) | (1 << c) | (1 << e)
        n += 1
        h = d.raw_hits(s)
        for i in h:
            hits[i] += 1
        for i in d.apply_hits(h)[1]:
            applied[i] += 1
    return n, hits, applied


def enumerate_yaku(procs):
    d = data()
    with ProcPool(procs) as p:
        parts = p.map(_enum_worker, range(d.nw - 3), chunksize=1)
    total = sum(x[0] for x in parts)
    hits = [sum(x[1][i] for x in parts) for i in range(len(d.yaku))]
    applied = [sum(x[2][i] for x in parts) for i in range(len(d.yaku))]
    return total, hits, applied


# ---------------------------------------------------------------- 2. 1ゲーム
FIXED_MIN_COPIES = 4   # 全語入りの固定の山: ひらがな・修飾牌は max(4, used_in_words) 枚
FIXED_HEAD_COPIES = 4  # 喘ぎ牌は6種 x 4枚
TOPK = 12              # 近似CPU: 手牌との一致が多い上位何語から4語の組を作るか


def fixed_wall_counts():
    """全語入り固定の山の構成。戻り値: (牌ごとの枚数 array, 牌→used_in_words)。"""
    d = data()
    used = Counter()
    for w in d.words:
        for t in set(w["tiles"].split("|")):  # 同じ語で2回出る牌も1語と数える
            used[t] += 1
    counts = np.zeros(d.T, dtype=np.int16)
    for t, u in used.items():
        counts[d.tid[t]] = max(FIXED_MIN_COPIES, u)
    for h in d.head_idx:
        counts[h] = FIXED_HEAD_COPIES
    return counts, used


def print_fixed_wall():
    d = data()
    counts, used = fixed_wall_counts()
    tiles = sorted(used, key=lambda t: (-counts[d.tid[t]], t))
    body = sum(int(counts[d.tid[t]]) for t in tiles)
    heads = sum(int(counts[h]) for h in d.head_idx)
    print("=== 全語入り固定の山(B)の構成: 牌ごとに max(4, used_in_words) 枚 / 喘ぎ牌は6種x4枚 ===")
    print(f"  {'牌':<6}{'語数':>4}{'枚数':>5}   " * 3)
    rows = [f"  {t:<6}{used[t]:>4}{int(counts[d.tid[t]]):>5}   " for t in tiles]
    for i in range(0, len(rows), 3):
        print("".join(rows[i:i + 3]))
    print(f"  喘ぎ牌: {' / '.join(HEADS)} 各{FIXED_HEAD_COPIES}枚 = {heads}枚")
    print(f"  ひらがな・修飾牌: {len(tiles)}種 {body}枚 / 喘ぎ牌 {heads}枚 / 合計 {body + heads}枚")
    ok = (body, heads, body + heads) == (243, 24, 267)
    print(f"  期待値(243 + 24 = 267)との一致: {'一致' if ok else '不一致'}")
    if not ok:
        print(f"  → 差: ひらがな・修飾牌 {body - 243:+d} / 喘ぎ牌 {heads - 24:+d}。words.csv の語数や used_in_words が前提と違う可能性")
    return ok


def rank_pruned(Wp, hand, rem, cpu, rc, head_idx, k=TOPK):
    """近似CPU(全語入りの山用)。手牌との一致が多い上位k語から4語の組を作り、
    組との一致枚数(+喘ぎ牌)が最大になる捨て牌を選ぶ。強CPUは山の残りで足りる組だけを数える。
    戻り値は Setup.rank_discards と同じ [(key, 捨てる牌, 捨てた後の手牌)]。"""
    d = data()
    o = np.minimum(Wp, hand).sum(axis=1)
    order = np.argsort(-o, kind="stable")[:k]
    sel = Wp[order]
    if len(order) >= N_WORDS:
        Ssub = sel[d.combos(len(order))].sum(axis=1)
    else:
        Ssub = sel.sum(axis=0, keepdims=True)
    cands = []
    for c in np.nonzero(hand)[0]:
        h2 = hand.copy()
        h2[c] -= 1
        m = np.minimum(Ssub, h2).sum(axis=1) + (1 if h2[head_idx].any() else 0)
        if cpu == "strong":
            f = (np.clip(Ssub - h2, 0, None) <= rem).all(axis=1)
            if f.any():
                mm = m[f].max()
                key = (int(mm), int((f & (m == mm)).sum()), rc.random())
            else:
                key = (0, 0, rc.random())
        else:
            key = (int(m.max()), 0, rc.random())
        cands.append((key, c, h2))
    return cands


def is_tenpai(R, h, rem):
    """13枚hが、1枚入れ替えで完成し、その必要牌が山(rem)に残っているか。Rは候補(完成形)の行。"""
    if not len(R):
        return False
    m = np.minimum(R, h).sum(axis=1)
    f = (np.clip(R - h, 0, None) <= rem).all(axis=1)
    return bool(((m == HAND - 1) & f).any())


class Setup:
    """A: 1ゲーム分の盤面(14語のプール・山・完成形の全候補)。強弱CPUで共有する。"""

    def __init__(self, seed, pool_size, heads_range, pruned=False):
        d = data()
        self.pruned = pruned  # True なら近似CPU(rank_pruned)を使う(検証用)
        rs = random.Random(seed)
        self.idx = rs.sample(range(d.nw), pool_size)
        k = rs.randint(*heads_range)
        heads = [d.head_idx[i] for i in rs.sample(range(len(HEADS)), k)]
        self.Wp = d.W[self.idx]
        total = self.Wp.sum(axis=0).astype(np.int16)
        for h in heads:
            total[h] += 1
        self.total = total
        wall = [t for t in range(d.T) for _ in range(total[t])]
        rs.shuffle(wall)
        self.wall = wall
        # 完成形(4語+喘ぎ牌1枚)の全候補。行 = 候補、列 = 牌
        self.combo = d.combos(pool_size)
        S0 = self.Wp[self.combo].sum(axis=1).astype(np.int8)
        rows = []
        for h in heads:
            s = S0.copy()
            s[:, h] += 1
            rows.append(s)
        self.S = np.concatenate(rows)
        self.row_combo = np.tile(np.arange(len(self.combo)), len(heads))
        self.combo_mask = [sum(1 << self.idx[j] for j in c) for c in self.combo]

    def best_complete(self, hand):
        """手牌に完全に含まれる完成形のうち翻が最大のもの (翻, 役, 語のマスク)。なければNone。"""
        d = data()
        full = np.minimum(self.S, hand).sum(axis=1) == HAND
        if not full.any():
            return None
        best = None
        for ci in set(self.row_combo[full].tolist()):
            r = d.eval_mask(self.combo_mask[ci])
            if best is None or r[0] > best[0]:
                best = (r[0], r[1], self.combo_mask[ci])
        return best

    def rank_discards(self, hand, rem, cpu, rc):
        if self.pruned:
            return rank_pruned(self.Wp, hand, rem, cpu, rc, data().head_idx)
        S = self.S
        m14 = np.minimum(S, hand).sum(axis=1)
        if cpu == "strong":
            base = (np.clip(S - hand, 0, None) <= rem).all(axis=1)
            top = m14[base].max() if base.any() else -1
            Sk = S[base & (m14 >= top - 1)] if top >= 0 else S[:0]
        else:  # 弱CPU: 山の残りを見ない
            Sk = S[m14 >= m14.max() - 1]
        cands = []
        for c in np.nonzero(hand)[0]:
            h2 = hand.copy()
            h2[c] -= 1
            if len(Sk):
                m = np.minimum(Sk, h2).sum(axis=1)
                if cpu == "strong":
                    f = (np.clip(Sk - h2, 0, None) <= rem).all(axis=1)
                    if f.any():
                        mm = m[f].max()
                        key = (int(mm), int((f & (m == mm)).sum()), rc.random())
                    else:
                        key = (0, 0, rc.random())
                else:
                    key = (int(m.max()), 0, rc.random())
            else:
                key = (0, 0, rc.random())
            cands.append((key, c, h2))
        return cands

    def tenpai_checker(self, hand14, rem):
        """ツモ直後の14枚から、捨てた後の13枚hがテンパイかを返す関数を作る。"""
        m14 = np.minimum(self.S, hand14).sum(axis=1)
        R = self.S[m14 >= HAND - 1]
        return lambda h: is_tenpai(R, h, rem)


def complete_words(hand):
    """手牌に(枚数まで含めて)完全に入っている語の行index。"""
    return np.nonzero((data().W <= hand).all(axis=1))[0]


def find_complete(hand):
    """全語から、手牌に完全に含まれる 4語+喘ぎ牌1枚 を探す(厳密)。翻最大の (翻, 役, マスク) かNone。"""
    d = data()
    if not hand[d.head_idx].any():
        return None
    comp = complete_words(hand)
    if len(comp) < N_WORDS:
        return None
    combos = comp[d.combos(len(comp))]
    ok = (d.W[combos].sum(axis=1) <= hand).all(axis=1)
    best = None
    for row in combos[ok]:
        mask = sum(1 << int(i) for i in row)
        r = d.eval_mask(mask)
        if best is None or r[0] > best[0]:
            best = (r[0], r[1], mask)
    return best


class FixedSetup:
    """B: 全語入りの固定の山。毎ゲーム同じ構成をシャッフルするだけ。"""

    _counts = None

    def __init__(self, seed):
        d = data()
        if FixedSetup._counts is None:
            FixedSetup._counts = fixed_wall_counts()[0]
        self.total = FixedSetup._counts
        rs = random.Random(seed)
        wall = [t for t in range(d.T) for _ in range(int(self.total[t]))]
        rs.shuffle(wall)
        self.wall = wall

    def best_complete(self, hand):
        return find_complete(hand)

    def rank_discards(self, hand, rem, cpu, rc):
        d = data()
        return rank_pruned(d.W, hand, rem, cpu, rc, d.head_idx)

    def tenpai_checker(self, hand14, rem):
        d = data()
        head = np.array(d.head_idx)

        def check(h13):
            # 完成には、h13だけで完成している語が3語以上(枚数の取り合いで残り1語がw待ち)必要
            if len(complete_words(h13)) < N_WORDS - 1:
                return False
            ws = np.nonzero(rem > 0)[0]
            if not h13[head].any():
                ws = np.intersect1d(ws, head)
            for w in ws:
                h = h13.copy()
                h[w] += 1
                if find_complete(h) is not None:
                    return True
            return False

        return check


def play_game(st, cpu, checkpoints, cpu_seed, trace=False):
    """checkpoints = ツモ回数の候補(例 (10, 14))。各ツモ回数で打ち切った場合の結果 {回数: 結果} を返す。
    結果: ("win", 翻, 役index tuple, 巡目, 語のマスク) / ("tenpai", 崩せるか) / ("noten",)
    捨て方はツモの上限を見ない(残りツモ回数に依存しない)ので、同じ配牌・同じ山・同じ乱数なら、
    上限20の1回のプレイが、上限6〜20のどの結果にもなる。
    trace=True なら res["trace"] = (アガリ巡目 or -1, テンパイ以上ビット列) も返す。
    ビット列の第t bit = 巡目tの捨て牌の後の13枚がテンパイ(アガリ済みなら立てない。t=0は配牌)。"""
    d = data()
    rc = random.Random(cpu_seed)
    hand = np.zeros(d.T, dtype=np.int8)
    rem = st.total.astype(np.int16)  # 山に残っている牌
    for t in st.wall[:HAND]:
        hand[t] += 1
        rem[t] -= 1
    pos = HAND
    res = {}
    tmask = 0

    r = st.best_complete(hand)
    if r:
        out = {cp: ("win", r[0], r[1], 0, r[2]) for cp in checkpoints}
        if trace:
            out["trace"] = (0, 0)
        return out
    if trace and st.tenpai_checker(hand, rem)(hand):
        tmask |= 1

    win_turn = -1
    for turn in range(1, max(checkpoints) + 1):
        if pos >= len(st.wall):
            break
        t = st.wall[pos]
        pos += 1
        hand[t] += 1
        rem[t] -= 1
        r = st.best_complete(hand)
        if r:
            for cp in checkpoints:
                res.setdefault(cp, ("win", r[0], r[1], turn, r[2]))
            win_turn = turn
            break
        cands = st.rank_discards(hand, rem, cpu, rc)
        _, _, h2 = max(cands, key=lambda x: x[0])
        if turn in checkpoints or trace:
            check = st.tenpai_checker(hand, rem)
            ten = check(h2)  # テンパイ = 13枚のうち1枚を入れ替えれば完成し、その必要牌が山に残っている
            if trace and ten:
                tmask |= 1 << turn
            if turn in checkpoints:
                res[turn] = ("tenpai", any(not check(h) for _, _, h in cands)) if ten else ("noten",)
        hand = h2
    for cp in checkpoints:
        res.setdefault(cp, ("noten",))
    if trace:
        res["trace"] = (win_turn, tmask)
    return res


def make_setup(wall, seed, pool_size, heads_range):
    if wall == "A":
        return Setup(seed, pool_size, heads_range)
    if wall == "Ap":  # 14語プール + 近似CPU(近似の検証用)
        return Setup(seed, pool_size, heads_range, pruned=True)
    if wall == "B":
        return FixedSetup(seed)
    raise ValueError(wall)


def _game_worker(args):
    seeds, pool_size, heads_range, checkpoints, walls, trace = args
    out = []
    for g in seeds:
        rec = {}
        for wall in walls:
            st = make_setup(wall, g, pool_size, heads_range)
            for cpu in CPUS:
                res = play_game(st, cpu, checkpoints, g ^ 0x9E3779B1, trace)
                for cp, r in res.items():
                    rec[(wall, cpu, cp)] = r
        out.append(rec)
    dd = data()
    if len(dd._eval_cache) > 1_500_000:
        dd._eval_cache.clear()
    return out


def run_batch(seed_start, n, pool_size, heads_range, checkpoints, walls, procs, trace=False):
    seeds = list(range(seed_start, seed_start + n))
    k = procs * 4
    chunks = [seeds[i::k] for i in range(k)]
    jobs = [(c, pool_size, heads_range, checkpoints, walls, trace) for c in chunks if c]
    if procs > 1:
        with ProcPool(procs) as p:
            parts = p.map(_game_worker, jobs)
    else:
        parts = [_game_worker(j) for j in jobs]
    # seeds[i::k] で分けたので元の順序に戻す
    ordered = [None] * n
    for ci, part in zip([i for i, c in enumerate(chunks) if c], parts):
        for j, g in enumerate(part):
            ordered[ci + j * k] = g
    return ordered


def view(games, wall, cp):
    """条件(山の作りとツモ回数)ごとに、[(強CPUの結果, 弱CPUの結果)] を取り出す。"""
    return [tuple(g[(wall, cpu, cp)] for cpu in CPUS) for g in games]


def ci_halfwidth(k, n):
    p = k / n
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / n)


def collect(args, heads_range, walls, checkpoints, kinds=("win", "tenpai", "noten"), trace=False):
    """誤差幅(アガリ率など)が目標以下になるまで、5000ゲームずつ増やす。シードは固定(連番)。"""
    games = []
    seed = args.seed * 1_000_003
    while True:
        n = args.games if args.games else args.batch
        games += run_batch(seed + len(games), n, args.pool_size, heads_range, checkpoints, walls, args.procs, trace)
        if args.games:
            return games
        G = len(games)
        worst = 0.0
        for wall in walls:
            for cp in checkpoints:
                for cpu in CPUS:
                    for kind in kinds:
                        k = sum(g[(wall, cpu, cp)][0] == kind for g in games)
                        worst = max(worst, ci_halfwidth(k, G))
        print(f"  ... {G}ゲーム: 最大の95%誤差幅 ±{worst * 100:.2f}pt", flush=True)
        if (G >= args.min_games and worst <= args.ci) or G >= args.max_games:
            return games


# ---------------------------------------------------------------- 集計
def summarize(games, ci):
    res = [g[ci] for g in games]
    n = len(res)
    wins = [r for r in res if r[0] == "win"]
    tp = [r for r in res if r[0] == "tenpai"]
    s = {
        "n": n,
        "win": len(wins),
        "tenpai": len(tp),
        "noten": sum(r[0] == "noten" for r in res),
        "break_ok": sum(r[1] for r in tp),
        "han_hist": Counter(r[1] for r in wins),
        "turn_hist": Counter(r[3] for r in wins),
        "yaku": Counter(i for r in wins for i in r[2]),
        "word": Counter(i for r in wins for i in range(data().nw) if r[4] >> i & 1),
        "avg_han": sum(r[1] for r in wins) / len(wins) if wins else 0.0,
        "avg_turn": sum(r[3] for r in wins) / len(wins) if wins else 0.0,
    }
    return s


def pct(k, n):
    return f"{k / n:6.1%}" if n else "   -  "


def print_game_report(args, games, heads_range):
    n = len(games)
    print(f"=== 1ゲーム: プール{args.pool_size}語 / 最大ツモ{args.max_draws}回 / 喘ぎ牌{heads_range[0]}〜{heads_range[1]}種x各1枚 / {n}ゲーム(強弱同じ配牌・同じ山) ===")
    sums = [summarize(games, ci) for ci in range(len(CPUS))]
    print(f"  {'':<22}{CPU_LABEL['strong']:>12}{CPU_LABEL['weak']:>12}")
    for label, key in (("アガリ率", "win"), ("テンパイ流局率", "tenpai"), ("ノーテン率", "noten")):
        vals = [f"{s[key] / n:6.1%} ±{ci_halfwidth(s[key], n) * 100:.1f}" for s in sums]
        print(f"  {label:<22}{vals[0]:>12}{vals[1]:>12}")
    print(f"  {'テンパイを崩せる割合*':<20}{pct(sums[0]['break_ok'], sums[0]['tenpai']):>12}{pct(sums[1]['break_ok'], sums[1]['tenpai']):>12}")
    print(f"  {'平均翻(アガリ時)':<20}{sums[0]['avg_han']:>12.2f}{sums[1]['avg_han']:>12.2f}")
    print(f"  {'平均巡目(アガリ時)':<20}{sums[0]['avg_turn']:>12.2f}{sums[1]['avg_turn']:>12.2f}")
    # 強-弱のアガリ率差(同じ配牌なので対応のある差)
    diff = np.array([(g[0][0] == "win") - (g[1][0] == "win") for g in games], dtype=float)
    print(f"  アガリ率の差(強-弱): {diff.mean() * 100:+.1f}pt ±{1.96 * diff.std(ddof=1) / math.sqrt(n) * 100:.1f}  (* テンパイ流局のうち、テンパイにならない捨て牌が存在した割合)")

    for ci, s in enumerate(sums):
        print(f"\n[翻の分布] {CPU_LABEL[CPUS[ci]]}(アガリ時、形1翻+役)")
        w = s["win"]
        hist = s["han_hist"]
        for han in range(min(hist), max(hist) + 1):
            c = hist.get(han, 0)
            if c:
                print(f"  {han:>2}翻: {c:>6}  {c / w:6.1%}  {'#' * round(40 * c / w)}")
    return sums


def han_hint(rate):
    return "1" if rate >= 0.05 else "2" if rate >= 0.01 else "3+"


def print_yaku_report(args, sums, enum, outdir):
    d = data()
    total_sets, e_hits, e_applied = enum
    os.makedirs(outdir, exist_ok=True)
    print(f"\n=== 役ごとの出現率(分母 = アガリ手。全ゲーム中も併記) ===")
    print(f"  数え上げ: 4語の組み合わせ全 {total_sets:,} 通りのうち、その役の条件を満たす割合(プール・牌の取り合いは考えない)")
    for ci, cpu in enumerate(CPUS):
        s = sums[ci]
        w, n = s["win"], s["n"]
        rows = []
        for i, y in enumerate(d.yaku):
            c = s["yaku"].get(i, 0)
            rows.append(dict(
                id=y["id"], name=y["name"], pattern=y["pattern"], group=y["group"], tier=y["tier"],
                han=int(y["han_provisional"]), status=y["han_status"], hits=c,
                rate_win=c / w if w else 0.0, rate_all=c / n,
                enum_sets=e_hits[i], enum_rate=e_hits[i] / total_sets,
            ))
        with open(os.path.join(outdir, f"yaku_stats_{cpu}.csv"), "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"\n[{CPU_LABEL[cpu]}] アガリ{w}回中。全役の表: {os.path.join(outdir, f'yaku_stats_{cpu}.csv')}")
        if cpu == "strong":
            print(f"  {'id':<5}{'役名':<12}{'型':<12}{'翻':>2}{'目安':>4} {'アガリ手中':>9}{'全ゲーム中':>9} {'回数':>6} {'組合せ割合':>9}")
            for r in sorted(rows, key=lambda r: -r["hits"]):
                if r["hits"]:
                    print(f"  {r['id']:<5}{r['name']:<12}{r['pattern'][:6]:<12}{r['han']:>2}{han_hint(r['rate_win']):>4} "
                          f"{r['rate_win']:>9.2%}{r['rate_all']:>9.3%} {r['hits']:>6} {r['enum_rate']:>9.3%}")
        zero = [r for r in rows if r["hits"] == 0]
        bound = f"(アガリ{w}回中0回 = 真の出現率は95%の確信で {3 / w:.3%} 以下)" if w else ""
        print(f"\n  ■ 一度も出なかった役: {len(zero)}/{len(rows)} {bound}")
        for r in zero:
            note = "数え上げでも成立する組み合わせが0 → 条件の誤り・成立不能の疑い" if r["enum_sets"] == 0 else \
                f"組み合わせとしては成立可能({r['enum_sets']:,}通り, {r['enum_rate']:.4%})"
            print(f"    {r['id']} {r['name']}(翻{r['han']}・{r['status']}): {note}")
    # 同名の役
    names = Counter(y["name"] for y in d.yaku)
    dup = [n for n, c in names.items() if c > 1]
    if dup:
        s = sums[0]
        for nme in dup:
            ids = [i for i, y in enumerate(d.yaku) if y["name"] == nme]
            c = sum(s["yaku"].get(i, 0) for i in ids)
            print(f"\n  ※同名の役「{nme}」{len(ids)}行の合算(強CPU): {c}回 = アガリ手の{c / s['win']:.2%}")


# ---------------------------------------------------------------- 3. 1ラン
def simulate_runs(games, ci, n_range, targets, policy, pile_point, burst_at, runs, seed, limit=None):
    """ゲームは独立なので結果を再抽選して1ランを再現する。
    policy: None=テンパイを崩せない / K=連続数がK回目になるテンパイを崩す(崩せるとき)。"""
    rng = np.random.default_rng(seed)
    res = [g[ci] for g in games]
    kind = np.array([0 if r[0] == "win" else 1 if r[0] == "tenpai" else 2 for r in res])
    score = np.array([r[1] * ARGS.han_point if r[0] == "win" else 0 for r in res], dtype=np.int64)
    can_break = np.array([r[0] == "tenpai" and r[1] for r in res])
    # そのゲームで引いたツモ数(アガリはアガリ巡目、それ以外は上限まで引く)
    draws = np.array([r[3] if r[0] == "win" else (limit or 0) for r in res], dtype=np.int64)
    nmax = max(n_range)
    G = len(res)

    cum = np.zeros(runs, dtype=np.int64)
    pile = np.zeros(runs, dtype=np.int64)
    streak = np.zeros(runs, dtype=np.int32)
    used = np.zeros(runs, dtype=np.int32)
    alive = np.ones(runs, dtype=bool)
    r3_used = np.full(runs, -1, dtype=np.int32)
    r3_cum = np.zeros(runs, dtype=np.int64)
    burst_used = np.full(runs, -1, dtype=np.int32)
    cum_at = np.zeros((nmax + 1, runs), dtype=np.int64)
    dr = np.zeros(runs, dtype=np.int64)  # 累計ツモ数(テンパイ流局のやり直しも含む)
    dr_at = np.zeros((nmax + 1, runs), dtype=np.int64)

    while True:
        act = alive & (used < nmax)
        if not act.any():
            break
        gi = rng.integers(0, G, size=runs)
        k, s, cb = kind[gi], score[gi], can_break[gi]
        dr[act] += draws[gi][act]
        is_win = act & (k == 0)
        is_noten = act & (k == 2)
        is_tp = act & (k == 1)
        if policy is not None:
            broken = is_tp & cb & (streak + 1 >= policy)
            is_noten = is_noten | broken
            is_tp = is_tp & ~broken
        cum[is_win] += s[is_win] + pile[is_win]
        reset = is_win | is_noten
        pile[reset] = 0
        streak[reset] = 0
        used[reset] += 1
        idx = np.nonzero(reset)[0]
        cum_at[used[idx], idx] = cum[idx]
        dr_at[used[idx], idx] = dr[idx]
        streak[is_tp] += 1
        pile[is_tp] += pile_point
        new3 = is_tp & (streak >= 3) & (r3_used < 0)
        r3_used[new3] = used[new3]
        r3_cum[new3] = cum[new3]
        b = is_tp & (streak >= burst_at)
        alive[b] = False
        burst_used[b] = used[b]
    for kk in range(1, nmax + 1):  # バーストで止まったランは、そこまでの得点で固定
        m = used < kk
        cum_at[kk][m] = cum[m]
        dr_at[kk][m] = dr[m]

    out = {}
    for N in n_range:
        for T in targets:
            clear = (cum_at[N] >= T).mean()
            burst = ((burst_used >= 0) & (burst_used < N) & (cum < T)).mean()
            r3 = ((r3_used >= 0) & (r3_used < N) & (r3_cum < T)).mean()
            # 1ランの総ツモ数: クリアしたらその時点まで、しなければバーストまたはN消費まで
            ok = cum_at[1:N + 1] >= T
            cleared = ok.any(axis=0)
            first = ok.argmax(axis=0) + 1
            end = np.where(cleared, dr_at[first, np.arange(runs)], dr_at[N])
            out[(N, T)] = (float(clear), float(burst), float(r3), float(end.mean()))
    return out


def print_run_report(args, games):
    targets = [int(x) for x in args.targets.split(",")]
    lo, hi = (int(x) for x in args.n_range.split("-"))
    n_range = list(range(lo, hi + 1))
    policies = [None if p == "none" else int(p) for p in args.break_policies.split(",")]
    print(f"\n=== 1ラン(積み点{args.pile_point}点/回、連続{args.burst_at}回目のテンパイ流局でバースト、{args.runs}ラン) ===")
    print("  クリア率 / バースト率 / 焦らしプレイ(連続テンパイ3回)到達率。バースト・焦らしは、クリアまたはN消費の前に起きた割合。")
    table = {}
    for ci, cpu in enumerate(CPUS):
        for pol in policies:
            r = simulate_runs(games, ci, n_range, targets, pol, args.pile_point, args.burst_at, args.runs, args.seed + ci)
            table[(cpu, pol)] = r
            label = "テンパイを崩せない" if pol is None else f"{pol}回目のテンパイは崩す"
            print(f"\n[{CPU_LABEL[cpu]} / {label}]")
            for title, j in (("クリア率", 0), ("バースト率", 1), ("焦らしプレイ到達率", 2)):
                print(f"  {title}   目標点 |" + "".join(f"{'N=' + str(N):>7}" for N in n_range))
                for T in targets:
                    print(f"  {'':<10}{T:>7} |" + "".join(f"{r[(N, T)][j]:>7.1%}" for N in n_range))
    return table


# ---------------------------------------------------------------- 比較モード(v1.3): A=14語プール / B=全語入り固定の山
class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, s):
        for f in self.files:
            f.write(s)

    def flush(self):
        for f in self.files:
            f.flush()


COND_NAME = {"A": "A(14語プール)", "B": "B(全語入り固定の山)"}
POLICIES = (None, 4)
POLICY_LABEL = {None: "テンパイを崩せない", 4: "4回目のテンパイは崩す"}


def cond_id(wall, cp):
    return f"{wall}{cp}"


def validate_pruned(args, heads_range, n):
    """近似CPU(rank_pruned)が、総当たりCPUとどれだけ違うかを、14語プールで確かめる。"""
    print(f"\n=== 近似CPUの検証: 14語プールで、総当たりCPU(従来)と近似CPU(上位{TOPK}語から選ぶ)を同じ配牌・山で比較({n}ゲーム) ===")
    games = run_batch(args.seed * 1_000_003 + 900_000, n, args.pool_size, heads_range, (10, 14), ("A", "Ap"), args.procs)
    print(f"  {'':<14}{'総当たり':>10}{'近似':>10}{'差(近似-総当たり)':>22}")
    for cp in (10, 14):
        for cpu in CPUS:
            a = np.array([g[("A", cpu, cp)][0] == "win" for g in games], dtype=float)
            b = np.array([g[("Ap", cpu, cp)][0] == "win" for g in games], dtype=float)
            diff = b - a
            print(f"  {CPU_LABEL[cpu]}・ツモ{cp:<2}回 {a.mean():>9.1%}{b.mean():>10.1%}"
                  f"{diff.mean() * 100:>+14.1f}pt ±{1.96 * diff.std(ddof=1) / math.sqrt(n) * 100:.1f}")


def dedicated_words():
    """専用牌(used_in_words==1)を使う語。"""
    d = data()
    _, used = fixed_wall_counts()
    return [i for i, w in enumerate(d.words) if any(used[t] == 1 for t in set(w["tiles"].split("|")))]


def word_rows(s):
    d = data()
    w, n = s["win"], s["n"]
    rows = []
    for i, wd in enumerate(d.words):
        c = s["word"].get(i, 0)
        share = c / w if w else 0.0
        rows.append(dict(id=wd["id"], word=wd["word"], type=wd["type"], hits=c, share_of_wins=share,
                         per_game=c / n, ratio_vs_mean=share / (N_WORDS / d.nw) if w else 0.0))
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)


def yaku_rows(s, enum):
    d = data()
    total_sets, e_hits, _ = enum
    w, n = s["win"], s["n"]
    rows = []
    for i, y in enumerate(d.yaku):
        c = s["yaku"].get(i, 0)
        rows.append(dict(id=y["id"], name=y["name"], pattern=y["pattern"], group=y["group"], tier=y["tier"],
                         han=int(y["han_provisional"]), status=y["han_status"], hits=c,
                         share_of_wins=c / w if w else 0.0, per_game=c / n,
                         combo_sets=e_hits[i], combo_rate=e_hits[i] / total_sets))
    return rows


TENHOU_TARGETS = ((0.3, 0.05), (0.6, 0.28))  # 0.3L巡目で約5%、0.6L巡目で約28%(天鳳のテンパイ率を、17巡=L換算)


def curve_arrays(raw, wall, cpu, tmax):
    """巡目0〜tmaxごとの累積アガリ率・累積テンパイ率(アガリ含む)・その巡目にアガった割合。"""
    wt = np.array([g[(wall, cpu, "trace")][0] for g in raw])
    mk = np.array([g[(wall, cpu, "trace")][1] for g in raw], dtype=np.int64)
    won = wt >= 0
    cw, ct, at = [], [], []
    for t in range(tmax + 1):
        w_by = won & (wt <= t)
        cw.append(float(w_by.mean()))
        ct.append(float((w_by | ((mk >> t) & 1 == 1)).mean()))
        at.append(float((won & (wt == t)).mean()))
    mean_turn = float(wt[won].mean()) if won.any() else float("nan")
    return np.array(cw), np.array(ct), np.array(at), mean_turn


def interp(arr, x):
    lo = int(math.floor(x))
    if lo >= len(arr) - 1:
        return float(arr[-1])
    f = x - lo
    return float(arr[lo] * (1 - f) + arr[lo + 1] * f)


def first_turn(cw, p):
    for t in range(1, len(cw)):
        if cw[t] >= p:
            return t
    return None


def compact_list(items, indent="    ", width=96):
    import textwrap
    return textwrap.fill(", ".join(items), width=width, initial_indent=indent, subsequent_indent=indent)


def print_condition_detail(cname, ci, s, enum, outdir):
    d = data()
    cpu = CPUS[ci]
    w, n = s["win"], s["n"]
    print(f"\n--- {cname} / {CPU_LABEL[cpu]}  (アガリ {w}回 / {n}ゲーム) ---")
    hist = s["han_hist"]
    if w:
        print("  [翻の分布](アガリ時): " + "  ".join(f"{h}翻 {hist[h] / w:.1%}" for h in sorted(hist) if hist[h] / w >= 0.005))
    yrows = yaku_rows(s, enum)
    write_csv(os.path.join(outdir, f"{cname}_{cpu}_yaku.csv"), yrows)
    print(f"  [役ごとのアガリ手での出現率](分母=アガリ手{w}回。上位8。全84役はCSV)")
    for r in sorted(yrows, key=lambda r: -r["hits"])[:8]:
        print(f"    {r['id']} {r['name']:<10}翻{r['han']} {r['share_of_wins']:>7.2%} ({r['hits']}回)")
    zero = [r for r in yrows if r["hits"] == 0]
    bound = f"; アガリ{w}回中0回 = 真の出現率は95%の確信で{3 / w:.2%}以下" if w else ""
    print(f"  [一度も出なかった役] {len(zero)}/{len(yrows)}{bound}")
    print("    表記: ID 役名(4語の組み合わせとしての割合。595,665通りの数え上げ。※は成立する組み合わせが0)")
    print(compact_list([f"{r['id']} {r['name']}({'※' if r['combo_sets'] == 0 else format(r['combo_rate'], '.3%')})" for r in zero]))
    wrows = word_rows(s)
    write_csv(os.path.join(outdir, f"{cname}_{cpu}_words.csv"), wrows)
    ranked = sorted(wrows, key=lambda r: -r["hits"])
    fmt = lambda r: f"{r['word']} {r['share_of_wins']:.1%}"
    print(f"  [語ごとの出現率](分母=アガリ手。平均は4語/63語={N_WORDS / d.nw:.1%})")
    print("    上位8: " + " / ".join(fmt(r) for r in ranked[:8]))
    print("    下位8: " + " / ".join(fmt(r) for r in ranked[-8:]))
    ded = set(dedicated_words())
    drows = sorted((r for i, r in enumerate(wrows) if i in ded), key=lambda r: -r["hits"])
    print("    専用牌を使う語: " + " / ".join(fmt(r) for r in drows))
    pon = next(r for r in wrows if r["word"] == "ちんぽ")
    print(f"    ちんぽ: アガリ手の{pon['share_of_wins']:.2%}({pon['hits']}回) / 全ゲームの{pon['per_game']:.3%} / 平均の{pon['ratio_vs_mean']:.2f}倍")


def compare_main(args):
    heads_range = parse_range(args.heads)
    outdir = args.out_compare
    os.makedirs(outdir, exist_ok=True)
    report = open(os.path.join(outdir, "report.txt"), "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, report)
    t0 = time.time()
    d = data()
    limits = tuple(int(x) for x in args.limits.split(","))
    tmax = args.curve_max
    checkpoints = tuple(sorted(set(limits) | {tmax}))
    walls = ("A", "B")
    print("ひらがな麻雀(仮) v1.3 比較: 山の作り(A/B) x ツモ上限 x CPU(強/弱) x 崩し方")
    print(f"  A = 14語プール(喘ぎ牌{heads_range[0]}〜{heads_range[1]}種x各1枚) / B = 全語入り固定の山。語{d.nw}・役{len(d.yaku)}行。")
    print(f"  ツモ上限 L = {','.join(map(str, limits))}。巡目カーブはツモ{tmax}回まで。乱数シード固定(seed={args.seed}、ゲーム番号 {args.seed * 1_000_003}〜の連番)。")
    print("  捨て方は残りツモ回数を見ないので、同じ番号のゲームでは、どのLでも同じ配牌・同じ山・同じ捨て方(途中経過が共通)。")
    print()
    print_fixed_wall()
    print("\n役の数え上げ(4語の全組み合わせ)...", flush=True)
    enum = enumerate_yaku(args.procs)
    validate_pruned(args, heads_range, args.validate_games)

    print("\nゲームのシミュレーション(アガリ率の95%誤差幅が目標以下になるまで)...", flush=True)
    raw = collect(args, heads_range, walls, checkpoints, kinds=("win",), trace=True)
    G = len(raw)
    print(f"  → {G}ゲーム(各条件・各CPU)。経過 {time.time() - t0:.0f}秒")

    # ================= パート1: 巡目カーブ =================
    series = [(w, cpu) for w in walls for cpu in CPUS]
    sname = lambda s: f"{s[0]}{'強' if s[1] == 'strong' else '弱'}"
    curves = {s: curve_arrays(raw, s[0], s[1], tmax) for s in series}
    print(f"\n{'=' * 10} パート1: ゲーム単位の速度(巡目カーブ。ツモ{tmax}回まで、{G}ゲーム) {'=' * 10}")
    print("  累積アガリ率 = その巡目までにアガった割合 / 累積テンパイ率 = その巡目の捨て牌の後で13枚がテンパイ以上(アガリ含む)の割合")
    print(f"\n  {'巡目':>4} |" + "".join(f"{sname(s):>7}" for s in series) + " |" + "".join(f"{sname(s):>7}" for s in series))
    print(f"  {'':>4} | {'--- 累積テンパイ率 ---':<28} | {'--- 累積アガリ率 ---'}")
    for t in range(1, tmax + 1):
        print(f"  {t:>4} |" + "".join(f"{curves[s][1][t]:>7.1%}" for s in series) + " |" + "".join(f"{curves[s][0][t]:>7.1%}" for s in series))
    print("\n  [アガリ巡目] 平均アガリ巡目(アガリ全体、ツモ20回以内)と、その巡目にアガった割合(全ゲーム中)")
    print(f"  {'巡目':>4} |" + "".join(f"{sname(s):>7}" for s in series))
    for t in range(0, tmax + 1):
        print(f"  {t:>4} |" + "".join(f"{curves[s][2][t]:>7.1%}" for s in series))
    print(f"  {'平均':>4} |" + "".join(f"{curves[s][3]:>7.2f}" for s in series))
    print("\n  [累積アガリ率が30%・50%・70%に達する巡目](ツモ20回以内に届かなければ「>20」)")
    print(f"  {'':>8}|" + "".join(f"{sname(s):>7}" for s in series))
    for p in (0.3, 0.5, 0.7):
        cells = []
        for s in series:
            ft = first_turn(curves[s][0], p)
            cells.append(f"{ft if ft else '>' + str(tmax):>7}")
        print(f"  {int(p * 100):>6}% |" + "".join(cells))
    print("\n  [天鳳との比較] 天鳳の累積テンパイ率(5巡5%・6巡9%・7巡13%・10巡28%)を、ゲーム巡数Lに換算: 0.3L巡目で約5%、0.6L巡目で約28%が目標")
    print("  巡目が整数にならないときは、前後の巡目の線形補間。()は目標との差(pt)。")
    tenhou_rows = []
    for frac, target in TENHOU_TARGETS:
        print(f"\n  {frac}L 巡目の累積テンパイ率(目標 約{target:.0%})")
        print(f"  {'L':>3} {'巡目':>5} |" + "".join(f"{sname(s):>14}" for s in series))
        for L in limits:
            x = frac * L
            vals = [interp(curves[s][1], x) for s in series]
            print(f"  {L:>3} {x:>5.1f} |" + "".join(f"{v:>7.1%}({(v - target) * 100:+5.1f})" for v in vals))
            for s, v in zip(series, vals):
                tenhou_rows.append(dict(L=L, factor=frac, turn=x, series=sname(s), tenpai_rate=v, target=target, diff_pt=(v - target) * 100))
    curve_rows = [dict(wall=s[0], cpu=s[1], turn=t, cum_win=curves[s][0][t], cum_tenpai=curves[s][1][t], win_at_turn=curves[s][2][t])
                  for s in series for t in range(tmax + 1)]
    write_csv(os.path.join(outdir, "curves.csv"), curve_rows)
    write_csv(os.path.join(outdir, "tenhou_compare.csv"), tenhou_rows)

    # ================= パート2: 1ラン =================
    conds = [(w, L) for w in walls for L in limits]
    views = {c: view(raw, *c) for c in conds}
    sums = {(c, ci): summarize(views[c], ci) for c in conds for ci in range(len(CPUS))}
    cn = lambda c: f"{c[0]}・ツモ{c[1]:>2}"

    def avg_draws(c, ci):
        res = [v[ci] for v in views[c]]
        return sum(r[3] if r[0] == "win" else c[1] for r in res) / len(res)

    print(f"\n{'=' * 10} パート2: 1ラン(ツモ上限 L = {','.join(map(str, limits))}) {'=' * 10}")
    print(f"\n[1ゲーム({G}ゲーム。95%誤差幅つき)]")
    for ci, cpu in enumerate(CPUS):
        print(f"\n  {CPU_LABEL[cpu]}")
        print(f"  {'条件':<12}{'アガリ率':>11}{'テンパイ流局':>12}{'ノーテン':>9}{'平均翻':>7}{'平均アガリ巡目':>13}{'平均ツモ/ゲーム':>14}{'崩せる割合':>10}")
        for c in conds:
            s = sums[(c, ci)]
            print(f"  {cn(c):<12}{s['win'] / G:>8.1%}±{ci_halfwidth(s['win'], G) * 100:.1f}{s['tenpai'] / G:>10.1%}{s['noten'] / G:>11.1%}"
                  f"{s['avg_han']:>8.2f}{s['avg_turn']:>13.2f}{avg_draws(c, ci):>14.2f}{pct(s['break_ok'], s['tenpai']):>10}")
    print("  (平均ツモ/ゲーム = アガリはアガリ巡目、それ以外は上限Lまで引く。崩せる割合 = テンパイ流局のうち、テンパイにならない捨て牌が存在した割合)")
    print("\n[翻の分布(アガリ時)]")
    for ci, cpu in enumerate(CPUS):
        for c in conds:
            s = sums[(c, ci)]
            h = s["han_hist"]
            if s["win"]:
                print(f"  {CPU_LABEL[cpu]} {cn(c):<10}" + " ".join(f"{k}翻{h[k] / s['win']:>6.1%}" for k in sorted(h) if h[k] / s["win"] >= 0.005))

    targets = [int(x) for x in args.targets.split(",")]
    N = int(args.run_n)
    print(f"\n[1ラン(N={N}、積み点{args.pile_point}点/回、連続{args.burst_at}回目のテンパイ流局でバースト、{args.runs}ラン)]")
    print("  クリア率 / バースト率 / 焦らし(連続テンパイ3回)到達率 / 1ランあたりの総ツモ数(平均。クリア・バースト・N消費のどれかで終わるまで。テンパイ流局のやり直し分も含む)")
    print("  崩す方針(4回目を崩す)では、バーストは0%、焦らし到達率は「崩せない」と同じ。クリア率と総ツモ数だけ違う。")
    run_rows, runs = [], {}
    for ci, cpu in enumerate(CPUS):
        for pol in POLICIES:
            for c in conds:
                runs[(c, ci, pol)] = simulate_runs(views[c], ci, [N], targets, pol, args.pile_point, args.burst_at, args.runs, args.seed + ci, limit=c[1])
                for T in targets:
                    cl, bu, r3, dr_ = runs[(c, ci, pol)][(N, T)]
                    run_rows.append(dict(condition=cond_id(*c), wall=c[0], limit=c[1], cpu=cpu, policy="none" if pol is None else f"break@{pol}",
                                         target=T, clear=cl, burst=bu, tease3=r3, total_draws=dr_))
    for ci, cpu in enumerate(CPUS):
        for pol in POLICIES:
            print(f"\n  [{CPU_LABEL[cpu]} / {POLICY_LABEL[pol]}]")
            metrics = (("クリア率", 0, "{:>8.1%}"), ("バースト率", 1, "{:>8.1%}"), ("焦らし到達率", 2, "{:>8.1%}"), ("総ツモ数", 3, "{:>8.1f}"))
            for title, j, f in metrics:
                if pol is not None and j in (1, 2):
                    continue
                print(f"    {title:<8}{'目標点':>6} |" + "".join(f"{T:>8}" for T in targets))
                for c in conds:
                    print(f"    {cn(c):<14} |" + "".join(f.format(runs[(c, ci, pol)][(N, T)][j]) for T in targets))
    write_csv(os.path.join(outdir, "runs_N%d.csv" % N), run_rows)

    # ================= 共通の出力 =================
    ded = set(dedicated_words())
    print(f"\n{'=' * 10} 共通: ちんぽ(専用牌「ぽ」)と専用牌を使う語の出やすさ {'=' * 10}")
    print("  分母=アガリ手。倍率 = 平均(4語/63語)の何倍か。")
    print(f"  専用牌を使う語({len(ded)}語): " + "、".join(d.words[i]["word"] for i in sorted(ded)))
    print(f"  {'条件':<12}{'CPU':<6}{'ちんぽ(アガリ手中)':>16}{'倍率':>6}{'全ゲーム中':>10}{'専用牌語の平均倍率':>16}{'それ以外の平均倍率':>16}")
    for c in conds:
        for ci, cpu in enumerate(CPUS):
            wr = word_rows(sums[(c, ci)])
            pon = next(r for r in wr if r["word"] == "ちんぽ")
            dm = np.mean([r["ratio_vs_mean"] for i, r in enumerate(wr) if i in ded])
            om = np.mean([r["ratio_vs_mean"] for i, r in enumerate(wr) if i not in ded])
            print(f"  {cn(c):<12}{CPU_LABEL[cpu]:<6}{pon['share_of_wins']:>14.2%}{pon['ratio_vs_mean']:>8.2f}{pon['per_game']:>11.3%}{dm:>14.2f}{om:>16.2f}")

    print(f"\n{'=' * 10} 共通: 役の出現率の比較(分母=アガリ手。強CPU。上位30。全84役・弱CPUはCSV) {'=' * 10}")
    cmp_rows = {}
    for ci, cpu in enumerate(CPUS):
        rows = []
        for i, y in enumerate(d.yaku):
            r = dict(id=y["id"], name=y["name"], han=int(y["han_provisional"]))
            for c in conds:
                s = sums[(c, ci)]
                r["share_" + cond_id(*c)] = s["yaku"].get(i, 0) / s["win"] if s["win"] else 0.0
                r["hits_" + cond_id(*c)] = s["yaku"].get(i, 0)
            r["combo_rate"] = enum[1][i] / enum[0]
            rows.append(r)
        cmp_rows[cpu] = rows
        write_csv(os.path.join(outdir, f"yaku_compare_{cpu}.csv"), rows)
    ref = cond_id("A", 10) if 10 in limits else cond_id(*conds[0])
    print(f"  {'id':<5}{'役名':<12}{'翻':>2}" + "".join(f"{cond_id(*c):>7}" for c in conds) + f"{'組合せ':>8}")
    for r in sorted(cmp_rows["strong"], key=lambda r: -r["share_" + ref])[:30]:
        print(f"  {r['id']:<5}{r['name']:<12}{r['han']:>2}" + "".join(f"{r['share_' + cond_id(*c)]:>7.1%}" for c in conds) + f"{r['combo_rate']:>8.2%}")
    print("  一度も出なかった役の数(全84役中)")
    for cpu in CPUS:
        print(f"    {CPU_LABEL[cpu]}: " + " ".join(f"{cond_id(*c)}={sum(1 for r in cmp_rows[cpu] if r['hits_' + cond_id(*c)] == 0)}" for c in conds))
    print("    (アガリ回数が少ない条件(特にB・L小)では、出なかった役が増える。誤差の目安は各詳細に記載)")

    print(f"\n{'=' * 10} 共通: 条件ごとの詳細 {'=' * 10}")
    for c in conds:
        for ci in range(len(CPUS)):
            print_condition_detail(cond_id(*c), ci, sums[(c, ci)], enum, outdir)

    srows = []
    for c in conds:
        for ci, cpu in enumerate(CPUS):
            s = sums[(c, ci)]
            srows.append(dict(condition=cond_id(*c), wall=c[0], limit=c[1], cpu=cpu, games=G,
                              win_rate=s["win"] / G, win_ci95=ci_halfwidth(s["win"], G), tenpai_rate=s["tenpai"] / G,
                              noten_rate=s["noten"] / G, avg_han=s["avg_han"], avg_win_turn=s["avg_turn"],
                              avg_draws_per_game=avg_draws(c, ci),
                              break_possible=s["break_ok"] / s["tenpai"] if s["tenpai"] else 0.0))
    write_csv(os.path.join(outdir, "summary.csv"), srows)
    print(f"\n完了。経過 {time.time() - t0:.0f}秒。CSV: {outdir}/")
    sys.stdout = sys.__stdout__
    report.close()


def parse_range(s):
    a, _, b = s.partition("-")
    return (int(a), int(b or a))


ARGS = None


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=0, help="ゲーム数を固定(0なら誤差幅で自動停止)")
    ap.add_argument("--ci", type=float, default=0.01, help="自動停止の目標: 主要な率の95%%誤差幅(既定0.01=±1pt)")
    ap.add_argument("--min-games", type=int, default=10000)
    ap.add_argument("--max-games", type=int, default=200000)
    ap.add_argument("--batch", type=int, default=5000)
    ap.add_argument("--pool-size", type=int, default=14)
    ap.add_argument("--max-draws", type=int, default=10)
    ap.add_argument("--heads", default="2-3", help="喘ぎ牌の種類数(各1枚)。例: 2-3 / 3")
    ap.add_argument("--han-point", type=int, default=1000, help="1翻あたりの点数")
    ap.add_argument("--pile-point", type=int, default=500, help="テンパイ流局1回あたりの積み点")
    ap.add_argument("--burst-at", type=int, default=4, help="連続何回目のテンパイ流局でバーストか")
    ap.add_argument("--n-range", default="3-8", help="規定ゲーム数Nの範囲")
    ap.add_argument("--targets", default="4000,6000,8000,10000,12000,15000", help="目標点(カンマ区切り)")
    ap.add_argument("--break-policies", default="none,4,3", help="テンパイを崩す方針。none=崩せない、K=K回目のテンパイを崩す")
    ap.add_argument("--runs", type=int, default=200000, help="クリア率計算のラン数")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--out", default=os.path.join(HERE, "results_v1.2"), help="役ごとの表(CSV)の出力先")
    ap.add_argument("--no-enum", action="store_true", help="役の数え上げを省略")
    ap.add_argument("--compare", action="store_true", help="v1.3: 山の作り(A/B) x ツモ(10/14) x CPU x 崩し方を比較し、results_v1.3/に保存")
    ap.add_argument("--out-compare", default=os.path.join(HERE, "results_v1.3"))
    ap.add_argument("--run-n", default="5", help="--compare の1ランのN")
    ap.add_argument("--limits", default="6,8,10,12,14", help="--compare: ツモ上限Lの一覧")
    ap.add_argument("--curve-max", type=int, default=20, help="--compare: 巡目カーブを取るツモ回数の上限")
    ap.add_argument("--validate-games", type=int, default=4000, help="--compare: 近似CPUの検証に使うゲーム数")
    ARGS = args = ap.parse_args()

    if args.compare:
        compare_main(args)
        return
    heads_range = parse_range(args.heads)
    d = data()
    print(f"語{d.nw}語 / 役{len(d.yaku)}行を読み込み")
    if args.no_enum:
        enum = (1, [0] * len(d.yaku), [0] * len(d.yaku))
    else:
        print("役の数え上げ(4語の全組み合わせ)...", flush=True)
        enum = enumerate_yaku(args.procs)
    print("ゲームのシミュレーション...", flush=True)
    games = view(collect(args, heads_range, ("A",), (args.max_draws,)), "A", args.max_draws)
    print()
    sums = print_game_report(args, games, heads_range)
    print_yaku_report(args, sums, enum, args.out)
    print_run_report(args, games)


if __name__ == "__main__":
    main()
