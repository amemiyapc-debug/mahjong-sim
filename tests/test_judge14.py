"""14牌形のアガリ判定(judge14.py)の確認。
1. words.csv の別々の4語 + heads.csv の雀頭1つ を組んだ14牌を、ランダムに1万手作り、全部アガリと判定されること
2. 牌を1枚入れ替えた手を1万手作り、判定が、独立の総当たり(別のアルゴリズム)と完全に一致すること(誤判定0)
3. game/core.js があれば、同じ手で win14 と照合する(--core-dir に、game/core.js と data/ を含む展開済みフォルダ)

  python3 tests/test_judge14.py [--core-dir /path/to/unzipped]
"""
import argparse, csv, json, os, random, subprocess, sys, tempfile, time
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from judge14 import Judge14

ap = argparse.ArgumentParser()
ap.add_argument("--words", default=os.path.join(HERE, "..", "data_v13", "words.csv"))
ap.add_argument("--heads", default=os.path.join(HERE, "..", "data_v13", "heads.csv"))
ap.add_argument("--n", type=int, default=10000)
ap.add_argument("--seed", type=int, default=20261005)
ap.add_argument("--core-dir", default="")
a = ap.parse_args()
J = Judge14(a.words, a.heads)
rng = random.Random(a.seed)
NW, NH = len(J.words), len(J.heads)


def oracle(hand):
    """独立の総当たり: 雀頭ごとに、残り12牌を、語のindex昇順の4つ組(入れ子ループ・牌数で枝刈り)で作れるかを調べる。"""
    c = Counter(hand)
    found = set()
    for hi, ht in enumerate(J.head_tiles):
        if not ht <= c:
            continue
        r0 = c - ht
        cand = [i for i, wt in enumerate(J.word_tiles) if wt <= r0]
        for x in range(len(cand)):
            r1 = r0 - J.word_tiles[cand[x]]
            for y in range(x + 1, len(cand)):
                if not J.word_tiles[cand[y]] <= r1:
                    continue
                r2 = r1 - J.word_tiles[cand[y]]
                for z in range(y + 1, len(cand)):
                    if not J.word_tiles[cand[z]] <= r2:
                        continue
                    r3 = r2 - J.word_tiles[cand[z]]
                    for w in range(z + 1, len(cand)):
                        if J.word_tiles[cand[w]] == r3:
                            found.add(((cand[x], cand[y], cand[z], cand[w]), hi))
    return sorted(found)


def valid(hand, p):
    ws, h = p
    tot = Counter()
    for i in ws:
        tot += J.word_tiles[i]
    tot += J.head_tiles[h]
    return tot == Counter(hand) and len(set(ws)) == 4


# ---- 1. 勝ち手を作る ----
t0 = time.time()
hands1, intended = [], []
miss1 = bad_valid1 = 0
for _ in range(a.n):
    ws = tuple(sorted(rng.sample(range(NW), 4)))
    h = rng.randrange(NH)
    hand = [t for i in ws for t in J.words[i]["tiles"].split("|")] + J.heads[h]["tiles"].split("|")
    rng.shuffle(hand)
    res = J.partitions(hand)
    hands1.append(hand)
    intended.append((ws, h))
    if (ws, h) not in res:
        miss1 += 1
    bad_valid1 += sum(not valid(hand, p) for p in res)
t1 = time.time() - t0
print(f"1. 件数 {a.n} / 不一致(アガリと判定されない・意図した分割が出ない) {miss1} / 無効な分割が返った {bad_valid1} / 実行時間 {t1:.1f}秒")

# ---- 2. 牌を1枚入れ替える ----
t0 = time.time()
hands2 = []
mism2 = n_win2 = n_multi2 = 0
for k in range(a.n):
    hand = list(hands1[k])
    i = rng.randrange(14)
    hand[i] = rng.choice([t for t in J.tiles if t != hand[i]])
    hands2.append(hand)
    res = J.partitions(hand)
    ref = oracle(hand)
    n_win2 += bool(res)
    n_multi2 += len(res) > 1
    if res != ref or any(not valid(hand, p) for p in res):
        mism2 += 1
t2 = time.time() - t0
print(f"2. 件数 {a.n} / 不一致(誤判定。総当たりとの差・無効な分割) {mism2} / 実行時間 {t2:.1f}秒(うち、アガリ判定 {n_win2}件、分割が複数 {n_multi2}件)")

# ---- 3. core.js との照合 ----
if not a.core_dir:
    print("3. game/core.js との照合: --core-dir が未指定のため省略")
else:
    core = os.path.join(a.core_dir, "game", "core.js")
    dd = os.path.join(a.core_dir, "data")
    if not os.path.exists(core) or not os.path.exists(os.path.join(dd, "yaku.csv")):
        print("3. game/core.js との照合: core.js または data/ が見つからないため省略")
    else:
        rd = lambda n: list(csv.DictReader(open(os.path.join(dd, n), encoding="utf-8-sig")))
        data = {"words": [{k: w[k] for k in ("word", "type", "modifier", "modifiers", "position", "stem", "tiles", "part", "tag", "flavor")} for w in rd("words.csv")],
                "yaku": [{k: y[k] for k in ("name", "group", "tier", "condition_type", "params", "han_provisional")} for y in rd("yaku.csv")],
                "heads": [{k: h[k] for k in ("head", "tiles", "type", "flavor", "stem")} for h in rd("heads.csv")],
                "variants": [{k: v[k] for k in ("tile", "base", "copies", "name", "mode")} for v in rd("tile_variants.csv")],
                "options": {"triplesOutOfDeckRule": True}}
        tmp = tempfile.mkdtemp()
        json.dump(data, open(os.path.join(tmp, "data.json"), "w", encoding="utf-8"), ensure_ascii=False)
        out = {}
        for name, hands in (("勝ち手", hands1), ("入れ替え", hands2)):
            hp, op = os.path.join(tmp, name + "_h.json"), os.path.join(tmp, name + "_o.json")
            json.dump(hands, open(hp, "w", encoding="utf-8"), ensure_ascii=False)
            t0 = time.time()
            subprocess.run(["node", os.path.join(HERE, "compare_core14.js"), core, os.path.join(tmp, "data.json"), hp, op], check=True)
            out[name] = (json.load(open(op))["res"], time.time() - t0)
        c1, c2 = out["勝ち手"][0], out["入れ替え"][0]
        mine2 = [J.is_win(h) for h in hands2]
        diff = [k for k in range(a.n) if c2[k] != mine2[k]]
        var_tiles = {"っ", "つ", "ちゅ", "ぉ゛"}
        explained = sum(any(t in var_tiles for t in hands2[k]) for k in diff)
        print(f"3. core.js 照合: 勝ち手 {a.n}件中 core.jsもアガリ {sum(c1)}件 / 入れ替え {a.n}件中 不一致 {len(diff)}件"
              f"(うち、っ・つ・ちゅを含む手 {explained}件。core.jsは牌の変種を扱う) / 実行時間 {out['勝ち手'][1] + out['入れ替え'][1]:.1f}秒")
        if diff:
            ex = diff[0]
            print("   不一致の例:", hands2[ex], "core.js:", c2[ex], "judge14:", mine2[ex])
assert miss1 == 0 and bad_valid1 == 0 and mism2 == 0
