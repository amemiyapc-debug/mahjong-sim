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
class Setup:
    """1ゲーム分の盤面(プール・山・完成形の全候補)。強弱CPUで共有する。"""

    def __init__(self, seed, pool_size, heads_range):
        d = data()
        rs = random.Random(seed)
        self.idx = rs.sample(range(d.nw), pool_size)
        k = rs.randint(*heads_range)
        heads = [d.head_idx[i] for i in rs.sample(range(len(HEADS)), k)]
        Wp = d.W[self.idx]
        total = Wp.sum(axis=0).astype(np.int16)
        for h in heads:
            total[h] += 1
        self.total = total
        wall = [t for t in range(d.T) for _ in range(total[t])]
        rs.shuffle(wall)
        self.wall = wall
        # 完成形(4語+喘ぎ牌1枚)の全候補。行 = 候補、列 = 牌
        self.combo = d.combos(pool_size)
        S0 = Wp[self.combo].sum(axis=1).astype(np.int8)
        rows = []
        for h in heads:
            s = S0.copy()
            s[:, h] += 1
            rows.append(s)
        self.S = np.concatenate(rows)
        self.row_combo = np.tile(np.arange(len(self.combo)), len(heads))
        self.combo_mask = [sum(1 << self.idx[j] for j in c) for c in self.combo]


def best_complete(st, hand):
    """手牌に完全に含まれる完成形のうち、翻が最大のもの。なければNone。"""
    d = data()
    full = np.minimum(st.S, hand).sum(axis=1) == HAND
    if not full.any():
        return None
    best = None
    for ci in set(st.row_combo[full].tolist()):
        r = d.eval_mask(st.combo_mask[ci])
        if best is None or r[0] > best[0]:
            best = r
    return best


def is_tenpai(R, h, rem):
    """13枚hが、1枚入れ替えで完成し、その必要牌が山(rem)に残っているか。Rは候補(完成形)の行。"""
    if not len(R):
        return False
    m = np.minimum(R, h).sum(axis=1)
    f = (np.clip(R - h, 0, None) <= rem).all(axis=1)
    return bool(((m == HAND - 1) & f).any())


def play_game(st, cpu, max_draws, cpu_seed):
    """戻り値: ("win", 翻, 役index tuple, 巡目) / ("tenpai", 崩せるか) / ("noten",)"""
    d = data()
    rc = random.Random(cpu_seed)
    S = st.S
    hand = np.zeros(d.T, dtype=np.int8)
    rem = st.total.astype(np.int16)  # 山に残っている牌
    for t in st.wall[:HAND]:
        hand[t] += 1
        rem[t] -= 1
    pos = HAND

    r = best_complete(st, hand)
    if r:
        return ("win", r[0], r[1], 0)

    for turn in range(1, max_draws + 1):
        if pos >= len(st.wall):
            return ("noten",)
        t = st.wall[pos]
        pos += 1
        hand[t] += 1
        rem[t] -= 1
        r = best_complete(st, hand)
        if r:
            return ("win", r[0], r[1], turn)

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
        key, c, h2 = max(cands, key=lambda x: x[0])

        if turn == max_draws:
            # テンパイ = 13枚のうち1枚を入れ替えれば完成し、その必要牌が山に残っている(必要牌は実際の残りで判定)
            R = S[m14 >= HAND - 1]
            ten_chosen = is_tenpai(R, h2, rem)
            if not ten_chosen:
                return ("noten",)
            can_break = any(not is_tenpai(R, h, rem) for _, _, h in cands)
            return ("tenpai", can_break)
        hand = h2
    return ("noten",)


def _game_worker(args):
    seeds, pool_size, max_draws, heads_range = args
    out = []
    for g in seeds:
        st = Setup(g, pool_size, heads_range)
        out.append(tuple(play_game(st, cpu, max_draws, g ^ 0x9E3779B1) for cpu in CPUS))
    data()._eval_cache.clear() if len(data()._eval_cache) > 1_500_000 else None
    return out


def run_batch(seed_start, n, pool_size, max_draws, heads_range, procs):
    seeds = list(range(seed_start, seed_start + n))
    chunks = [seeds[i::procs * 4] for i in range(procs * 4)]
    jobs = [(c, pool_size, max_draws, heads_range) for c in chunks if c]
    if procs > 1:
        with ProcPool(procs) as p:
            parts = p.map(_game_worker, jobs)
    else:
        parts = [_game_worker(j) for j in jobs]
    # seeds[i::k] で分けたので元の順序に戻す
    ordered = [None] * n
    for ci, part in zip([i for i, c in enumerate(chunks) if c], parts):
        for j, g in enumerate(part):
            ordered[ci + j * (procs * 4)] = g
    return ordered


def ci_halfwidth(k, n):
    p = k / n
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / n)


def collect(args, heads_range):
    games = []
    seed = args.seed * 1_000_003
    while True:
        n = args.games if args.games else args.batch
        games += run_batch(seed + len(games), n, args.pool_size, args.max_draws, heads_range, args.procs)
        if args.games:
            return games
        G = len(games)
        worst = 0.0
        for ci in range(len(CPUS)):
            for kind in ("win", "tenpai", "noten"):
                k = sum(g[ci][0] == kind for g in games)
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
def simulate_runs(games, ci, n_range, targets, policy, pile_point, burst_at, runs, seed):
    """ゲームは独立なので結果を再抽選して1ランを再現する。
    policy: None=テンパイを崩せない / K=連続数がK回目になるテンパイを崩す(崩せるとき)。"""
    rng = np.random.default_rng(seed)
    res = [g[ci] for g in games]
    kind = np.array([0 if r[0] == "win" else 1 if r[0] == "tenpai" else 2 for r in res])
    score = np.array([r[1] * ARGS.han_point if r[0] == "win" else 0 for r in res], dtype=np.int64)
    can_break = np.array([r[0] == "tenpai" and r[1] for r in res])
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

    while True:
        act = alive & (used < nmax)
        if not act.any():
            break
        gi = rng.integers(0, G, size=runs)
        k, s, cb = kind[gi], score[gi], can_break[gi]
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

    out = {}
    for N in n_range:
        for T in targets:
            clear = (cum_at[N] >= T).mean()
            burst = ((burst_used >= 0) & (burst_used < N) & (cum < T)).mean()
            r3 = ((r3_used >= 0) & (r3_used < N) & (r3_cum < T)).mean()
            out[(N, T)] = (float(clear), float(burst), float(r3))
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
    ARGS = args = ap.parse_args()

    heads_range = parse_range(args.heads)
    d = data()
    print(f"語{d.nw}語 / 役{len(d.yaku)}行を読み込み")
    if args.no_enum:
        enum = (1, [0] * len(d.yaku), [0] * len(d.yaku))
    else:
        print("役の数え上げ(4語の全組み合わせ)...", flush=True)
        enum = enumerate_yaku(args.procs)
    print("ゲームのシミュレーション...", flush=True)
    games = collect(args, heads_range)
    print()
    sums = print_game_report(args, games, heads_range)
    print_yaku_report(args, sums, enum, args.out)
    print_run_report(args, games)


if __name__ == "__main__":
    main()
