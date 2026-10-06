"""14牌形のアガリ判定(judge14.py)の確認。牌の変種(ぉ゛=お・っ=つ・ちゅ→つ)を含む。
1. 変種牌を混ぜた勝ち手 1万手 / 牌を1枚入れ替えた手 1万手 を、独立の総当たり(別のアルゴリズム)と比べる(不一致0)
2. 前回の確認3(変種を含まない生成の手)で、game/core.js の win14 と照合し直す(--core-dir)
3. 10,000手あたりの実行時間(judge14 の判定だけを測る)

  python3 tests/test_judge14.py [--core-dir /path/to/unzipped(game/core.js と data/ を含む)]
"""
import argparse, csv, itertools, json, os, random, subprocess, sys, tempfile, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
D13 = os.path.join(HERE, "..", "data_v13")
sys.path.insert(0, os.path.join(HERE, ".."))
from judge14 import Judge14

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=10000)
ap.add_argument("--seed", type=int, default=20261005)
ap.add_argument("--core-dir", default="")
a = ap.parse_args()
P = lambda n: os.path.join(D13, n)
JV = Judge14(P("words.csv"), P("heads.csv"), P("tile_variants.csv"))   # 変種あり
J0 = Judge14(P("words.csv"), P("heads.csv"))                            # 変種なし(前回の版)
NW, NH = len(JV.words), len(JV.heads)

# ---- 独立の総当たり(judge14 とは別の書き方) ----
VAR = list(csv.DictReader(open(P("tile_variants.csv"), encoding="utf-8-sig")))
REP = {v["tile"]: v["base"] for v in VAR if v["mode"] == "replace"}           # っ→つ, ぉ゛→お
FLEX = [(v["tile"], v["base"]) for v in VAR if v["mode"] == "flex"][0]         # ちゅ→つ
rd = lambda n: list(csv.DictReader(open(P(n), encoding="utf-8-sig")))
WT_RAW = [r["tiles"].split("|") for r in rd("words.csv")]
HT_RAW = [r["tiles"].split("|") for r in rd("heads.csv")]


def oracle(hand, variants=True):
    rep = REP if variants else {}
    wt = [Counter(rep.get(t, t) for t in ts) for ts in WT_RAW]
    ht = [Counter(rep.get(t, t) for t in ts) for ts in HT_RAW]
    oho = sum(t == "ぉ゛" for t in hand) if variants else 0
    flex_idx = [i for i, t in enumerate(hand) if t == FLEX[0]] if variants else []
    out, seen = set(), set()
    for choice in itertools.product((0, 1), repeat=len(flex_idx)):   # ちゅ1枚ずつ、ちゅ/つ のどちらで使うか(全部)
        h = [rep.get(t, t) for t in hand]
        k = 0
        for i, ch in zip(flex_idx, choice):
            if ch:
                h[i] = FLEX[1]
                k += 1
        key = (tuple(sorted(h)), k)
        if key in seen:
            continue
        seen.add(key)
        c = Counter(h)
        for hi, hh in enumerate(ht):
            if not hh <= c:
                continue
            r0 = c - hh
            cand = [i for i, w in enumerate(wt) if w <= r0]
            for x in range(len(cand)):
                r1 = r0 - wt[cand[x]]
                for y in range(x + 1, len(cand)):
                    if not wt[cand[y]] <= r1:
                        continue
                    r2 = r1 - wt[cand[y]]
                    for z in range(y + 1, len(cand)):
                        if not wt[cand[z]] <= r2:
                            continue
                        r3 = r2 - wt[cand[z]]
                        for w in range(z + 1, len(cand)):
                            if wt[cand[w]] == r3:
                                out.add(((cand[x], cand[y], cand[z], cand[w]), hi, oho, k))
    return sorted(out)


def valid(J, hand, p, variants=True):
    """返された分割が、手牌の14牌と過不足なく一致するか(ちゅをp[3]枚つとして使う)。"""
    ws, h, oho, used = p
    rep = J.replace
    c = Counter(rep.get(t, t) for t in hand)
    c[FLEX[0]] -= used if variants else 0
    c[FLEX[1]] += used if variants else 0
    tot = Counter()
    for i in ws:
        tot += J.word_tiles[i]
    tot += J.head_tiles[h]
    c = +c
    return c == tot and len(set(ws)) == 4 and used >= 0 and oho == (sum(t == "ぉ゛" for t in hand) if variants else 0)


def timed(J, hands):
    t0 = time.perf_counter()
    res = [J.partitions(h) for h in hands]
    return res, time.perf_counter() - t0


rng = random.Random(a.seed)

# ================= 前回と同じ生成(変種牌はっ・つ・ちゅのうち、辞書の文字どおり。ぉ゛なし) =================
legacy1, intended0 = [], []
for _ in range(a.n):
    ws = tuple(sorted(rng.sample(range(NW), 4)))
    h = rng.randrange(NH)
    hand = [t for i in ws for t in WT_RAW[i]] + HT_RAW[h]
    rng.shuffle(hand)
    legacy1.append(hand)
    intended0.append((ws, h))
legacy2 = []
for k in range(a.n):
    hand = list(legacy1[k])
    i = rng.randrange(14)
    hand[i] = rng.choice([t for t in J0.tiles if t != hand[i]])
    legacy2.append(hand)

# ================= 1. 変種牌を混ぜた勝ち手 / 入れ替えた手 =================
rng2 = random.Random(a.seed + 1)


def mix(tiles):
    out = []
    for t in tiles:
        n = REP.get(t, t)
        if n == "お":
            out.append(rng2.choice(["お", "ぉ゛"]))
        elif n == FLEX[1]:
            out.append(rng2.choice(["つ", "っ", "ちゅ"]))   # つ・っ・ちゅ のどれでも つ の語に使える
        else:
            out.append(t)
    return out


mixed1, want = [], []
for _ in range(a.n):
    ws = tuple(sorted(rng2.sample(range(NW), 4)))
    h = rng2.randrange(NH)
    raw = [t for i in ws for t in WT_RAW[i]] + HT_RAW[h]
    hand = mix(raw)
    rng2.shuffle(hand)
    mixed1.append(hand)
    need_chu = sum(t == FLEX[0] for t in raw)   # 辞書の語・雀頭が、ちゅとして要る枚数
    want.append((ws, h, sum(t == "ぉ゛" for t in hand), hand.count(FLEX[0]) - need_chu))
mixed2 = []
UNI = JV.tiles + JV.variant_tiles
for k in range(a.n):
    hand = list(mixed1[k])
    i = rng2.randrange(14)
    hand[i] = rng2.choice([t for t in UNI if t != hand[i]])
    mixed2.append(hand)
nvar = sum(any(t in JV.variant_tiles for t in h) for h in mixed1)

res1, tj1 = timed(JV, mixed1)
miss1 = sum(w not in r for w, r in zip(want, res1))
bad1 = sum(not valid(JV, h, p) for h, r in zip(mixed1, res1) for p in r)
ora1 = sum(r != oracle(h) for h, r in zip(mixed1, res1))
print(f"1a. 変種を混ぜた勝ち手: 件数 {a.n}(変種牌を含む手 {nvar}件) / 不一致 {ora1 + miss1 + bad1}"
      f"(総当たりとの差 {ora1}・意図した分割が出ない {miss1}・無効な分割 {bad1}) / 判定の実行時間 {tj1:.1f}秒")
res2, tj2 = timed(JV, mixed2)
ora2 = sum(r != oracle(h) for h, r in zip(mixed2, res2))
bad2 = sum(not valid(JV, h, p) for h, r in zip(mixed2, res2) for p in r)
print(f"1b. 変種を混ぜた入れ替え手: 件数 {a.n} / 不一致 {ora2 + bad2}(総当たりとの差 {ora2}・無効な分割 {bad2}) / 判定の実行時間 {tj2:.1f}秒"
      f"(アガリ {sum(bool(r) for r in res2)}件・ぉ゛を含むアガリ {sum(bool(r) and r[0][2] > 0 for r in res2)}件)")

# ================= 2. core.js との照合(前回と同じ手) =================
leg_v1, tl1 = timed(JV, legacy1)
leg_v2, tl2 = timed(JV, legacy2)
_, tn1 = timed(J0, legacy1)
_, tn2 = timed(J0, legacy2)
print(f"3. 実行時間(前回と同じ手 {a.n}+{a.n}手の判定だけ): 変種あり {tl1 + tl2:.1f}秒 / 変種なし(前回の版) {tn1 + tn2:.1f}秒 / 変種を混ぜた手 {tj1 + tj2:.1f}秒")
if not a.core_dir:
    print("2. game/core.js との照合: --core-dir が未指定のため省略")
else:
    core = os.path.join(a.core_dir, "game", "core.js")
    dd = os.path.join(a.core_dir, "data")
    if not (os.path.exists(core) and os.path.exists(os.path.join(dd, "yaku.csv"))):
        print("2. game/core.js との照合: core.js または data/ が見つからないため省略")
    else:
        rdd = lambda n: list(csv.DictReader(open(os.path.join(dd, n), encoding="utf-8-sig")))
        data = {"words": [{k: w[k] for k in ("word", "type", "modifier", "modifiers", "position", "stem", "tiles", "part", "tag", "flavor")} for w in rdd("words.csv")],
                "yaku": [{k: y[k] for k in ("name", "group", "tier", "condition_type", "params", "han_provisional")} for y in rdd("yaku.csv")],
                "heads": [{k: h[k] for k in ("head", "tiles", "type", "flavor", "stem")} for h in rdd("heads.csv")],
                "variants": [{k: v[k] for k in ("tile", "base", "copies", "name", "mode")} for v in rdd("tile_variants.csv")],
                "options": {"triplesOutOfDeckRule": True}}
        tmp = tempfile.mkdtemp()
        json.dump(data, open(os.path.join(tmp, "data.json"), "w", encoding="utf-8"), ensure_ascii=False)

        def core_res(name, hands):
            hp, op = os.path.join(tmp, name + "_h.json"), os.path.join(tmp, name + "_o.json")
            json.dump(hands, open(hp, "w", encoding="utf-8"), ensure_ascii=False)
            subprocess.run(["node", os.path.join(HERE, "compare_core14.js"), core, os.path.join(tmp, "data.json"), hp, op], check=True)
            return json.load(open(op))["res"]

        c1, c2 = core_res("legacy1", legacy1), core_res("legacy2", legacy2)
        d1 = [k for k in range(a.n) if c1[k] != bool(leg_v1[k])]
        d2 = [k for k in range(a.n) if c2[k] != bool(leg_v2[k])]
        old2 = [k for k in range(a.n) if c2[k] != J0.is_win(legacy2[k])]
        print(f"2. core.js 照合(前回と同じ手): 勝ち手 {a.n}件中 不一致 {len(d1)} / 入れ替え {a.n}件中 不一致 {len(d2)}"
              f"(前回の版では {len(old2)}件 → 減った数 {len(old2) - len(d2)})")
        for k in d2[:3]:
            print("   不一致の例:", legacy2[k], "core.js:", c2[k], "judge14:", bool(leg_v2[k]))
        m1, m2 = core_res("mixed1", mixed1), core_res("mixed2", mixed2)
        e1 = sum(m1[k] != bool(res1[k]) for k in range(a.n))
        e2 = [k for k in range(a.n) if m2[k] != bool(res2[k])]
        print(f"   (参考)変種を混ぜた手での core.js 照合: 勝ち手 不一致 {e1}/{a.n} / 入れ替え 不一致 {len(e2)}/{a.n}")
        for k in e2[:3]:
            print("   不一致の例:", mixed2[k], "core.js:", m2[k], "judge14:", bool(res2[k]))
assert ora1 == miss1 == bad1 == ora2 == bad2 == 0
