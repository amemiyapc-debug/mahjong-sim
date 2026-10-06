"""役の判定・合体・翻の選択(yaku14.py)の確認。
1. game/core.js との照合: 手1万手(乱数。役の語を多めにした偏りのある生成を含む。ぉ゛・っ・ちゅも混ぜる)について、
   (a) 分割ごとの「役名の集合・翻(合体なし)」、(b) win14 の最大翻(合体なし)、(c) アガリ判定そのもの を比べる。不一致の件数を出す。
2. 合体の独立実装(部分集合の総当たり)との照合: 全ての分割で、合体ありの翻が一致するか。
3. 合体・group の絞り込みの、手で作った例。
4. 合体36個が、それぞれ単独で成立する手が作れるか(元の役がそろう手を探索)。

  python3 tests/test_yaku14.py [--dir v13m] [--core-dir /path/to/unzipped(game/core.js)] [--n 10000]
"""
import argparse, csv, itertools, json, os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from yaku14 import Scorer

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=os.path.join(HERE, "..", "v13m"))
ap.add_argument("--core-dir", default="/tmp/claude-0/v13zip")
ap.add_argument("--n", type=int, default=10000)
ap.add_argument("--seed", type=int, default=20261006)
ap.add_argument("--no-patch", action="store_true",
                help="core.js の「ダブル奉仕」(pair_same_stem_modifiers)の語幹別名(まめ=くり)の扱いを、仕様(語幹)に合わせる1行の修正をしない")
a = ap.parse_args()
S = Scorer(a.dir)
W, H, Y = S.W, S.H, S.Y
rng = random.Random(a.seed)
ng = 0


def ok(msg, cond):
    global ng
    print(("OK  " if cond else "NG  ") + msg)
    if not cond:
        ng += 1


def hand_of(ws, h, variants=True):
    t = []
    for w in ws:
        t += W[w]["tiles"].split("|")
    t += H[h]["tiles"].split("|")
    if variants:
        t = [("ぉ゛" if x == "お" and rng.random() < 0.3 else x) for x in t]
        t = [("っ" if x == "つ" and rng.random() < 0.3 else x) for x in t]
        t = [("ちゅ" if x in ("つ", "っ") and rng.random() < 0.2 else x) for x in t]
    rng.shuffle(t)
    return t


# ---- 偏りのある手の生成: 役のパラメーターに出てくる語を、多めに入れる ----
def tokens_of(y):
    toks = []
    for g in y["params"].replace("/", ";").split(";"):
        for t in g.split("|"):
            t = t.split("=")[-1] if "=" in t else t
            if t:
                toks.append(t)
    return toks
THEME = []
for y in Y:
    ws = set()
    for t in tokens_of(y):
        try:
            m = S.token_mask(t)
        except Exception:
            continue
        ws |= set(S._bits(m))
    if ws:
        THEME.append(sorted(ws))


def gen_hand():
    for _ in range(100):
        k = rng.choice((0, 0, 2, 3, 4))
        ws = set()
        if k:
            pool = rng.choice(THEME)
            ws |= set(rng.sample(pool, min(k, len(pool))))
        while len(ws) < 4:
            ws.add(rng.randrange(len(W)))
        ws = list(ws)[:4]
        # 4語+雀頭を牌に分けて、ちゅを使う手が、役のない語で不成立にならないよう、そのまま使う(必ずアガリ)
        h = rng.randrange(len(H))
        return hand_of(ws, h)


hands = [gen_hand() for _ in range(a.n)]
# 非アガリの手も混ぜる(牌1枚を、別の牌に替える)
tiles_all = sorted({t for r in W for t in r["tiles"].split("|")} | {"ぉ゛"})
for i in range(0, a.n, 5):
    h = hands[i][:]
    h[rng.randrange(14)] = rng.choice(tiles_all)
    hands.append(h)

# ---- Python 側 ----
py = []
for h in hands:
    parts = S.judge.partitions(h)
    rows = []
    for ws, hi, oho, chu in parts:
        r = S.score(ws, hi, oho)
        rows.append(dict(four=list(ws), head=H[hi]["head"], han=r["han_no_merge"], yaku=sorted(r["added"])))
    best = max((r["han_no_merge"] for r in (S.score(ws, hi, oho) for ws, hi, oho, chu in parts)), default=None)
    py.append(dict(parts=rows, best=best, win=bool(parts)))

# ---- JS 側 ----
core = os.path.join(a.core_dir, "game", "core.js")
# core.js の pair_same_stem_modifiers は、語名の連結(st+a)で探すため、別名の語幹(まめコキ+くり舐め)を同じ語幹と数えない。
# CLAUDE.md §5-7(別名は語幹くりとして数える)・§6-3(同じ語幹X)に合わせた版を、一時ファイルで作って照合する。
_td0 = tempfile.mkdtemp()
if not a.no_patch:
    src = open(core, encoding="utf-8").read()
    old = src[src.index('else if(ct==="pair_same_stem_modifiers"){'):src.index('else if(ct==="count_part")')]
    new = ('else if(ct==="pair_same_stem_modifiers"){ const ms=p.split("|"); const stems=new Set(W.map(w=>w.stem).filter(x=>x));'
           ' f=four=>[...stems].some(st=>ms.every(m=>four.some(i=>W[i].stem===st&&W[i].mods.length===1&&W[i].mods[0]===m))); }\n    ')
    src = src.replace(old, new)
    core = os.path.join(_td0, "core.js")
    open(core, "w", encoding="utf-8").write(src)
data = dict(words=[{k: w[k] for k in ("word", "type", "modifier", "modifiers", "position", "stem", "tiles", "part", "tag", "flavor")} for w in W],
            yaku=[{k: y[k] for k in ("name", "group", "tier", "condition_type", "params", "han_provisional")} for y in Y],
            heads=[{k: h[k] for k in ("head", "tiles", "type", "flavor", "stem")} for h in H],
            variants=list(csv.DictReader(open(os.path.join(a.dir, "tile_variants.csv"), encoding="utf-8-sig"))),
            options={"triplesOutOfDeckRule": True})
with tempfile.TemporaryDirectory() as td:
    dj, cj, oj = (os.path.join(td, n) for n in ("data.json", "cases.json", "out.json"))
    json.dump(data, open(dj, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump([dict(hand=h, parts=[dict(four=p["four"], head=p["head"]) for p in x["parts"]]) for h, x in zip(hands, py)],
              open(cj, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["node", os.path.join(HERE, "compare_yaku_core.js"), core, dj, cj, oj], check=True)
    js = json.load(open(oj, encoding="utf-8"))

mis_win = mis_best = mis_part = n_parts = 0
first = []
for h, p, j in zip(hands, py, js):
    if p["win"] != bool(j["win"]):
        mis_win += 1; first.append(("win", h)); continue
    if not p["win"]:
        continue
    if p["best"] != j["win"]["han"]:
        mis_best += 1; first.append(("best", h, p["best"], j["win"]["han"]))
    for pp, jp in zip(p["parts"], j["parts"]):
        n_parts += 1
        if pp["han"] != jp["han"] or sorted(pp["yaku"]) != sorted(jp["yaku"]):
            mis_part += 1
            if len(first) < 5: first.append(("part", pp, jp))
n_win = sum(p["win"] for p in py)
print(f"   手 {len(hands)}(アガリ {n_win}、分割の総数 {n_parts})")
ok(f"core.js 照合: アガリ判定の不一致 {mis_win}", mis_win == 0)
ok(f"core.js 照合: 最大翻(合体なし)の不一致 {mis_best}", mis_best == 0)
ok(f"core.js 照合: 分割ごとの役名・翻の不一致 {mis_part}", mis_part == 0)
for f in first[:5]:
    print("   例:", f)
# 役ごとの、照合で成立した回数(照合できていない役の確認)
seen = {}
for p in py:
    for pp in p["parts"]:
        for n in pp["yaku"]:
            seen[n] = seen.get(n, 0) + 1
miss = sorted({y["name"] for y in Y} - set(seen))
print(f"   照合した手で、1度も成立しなかった役: {len(miss)}種 {miss}")

# ---- 2. 合体の独立実装(部分集合の総当たり) ----
def merge_naive(raw, added):
    srcs = [(m["name"], m["source_yaku"].split("|"), int(m["han_provisional"])) for m in S.M]
    ok_m = [x for x in srcs if all(s in raw for s in x[1])]
    best = 1 + sum(added.values())
    for k in (1, 2):
        for combo in itertools.combinations(ok_m, k):
            used = [s for _, ss, _ in combo for s in ss]
            if len(set(used)) != len(used):
                continue
            tot = 1 + sum(v for n, v in added.items() if n not in used) + sum(hh for _, _, hh in combo)
            best = max(best, tot)
    return best
bad = 0; with_merge = 0; two_merge = 0; tot = 0
for h in hands[:a.n]:
    for ws, hi, oho, chu in S.judge.partitions(h):
        r = S.score(ws, hi, oho)
        tot += 1
        if r["han"] != merge_naive(set(r["raw"]), r["added"]):
            bad += 1
        with_merge += bool(r["merges"]); two_merge += len(r["merges"]) == 2
        assert r["han"] >= r["han_no_merge"]
ok(f"合体: 独立実装(総当たり)との不一致 {bad} / 分割 {tot}(合体あり {with_merge}、2つ同時 {two_merge})", bad == 0)

# ---- 3. 手で作った例 ----
ix = S.widx
def sc(words, head="あん"):
    hi = next(i for i, h in enumerate(H) if h["head"] == head)
    return S.score([ix[w] for w in words], hi, 0)
r = sc(["ぱかあ", "くぱあ", "ぱかっ", "ちんぽ"])
ok("擬音3語: 全開フルオープン(5)が付き、ぱっくり(2)は group で消える", "全開フルオープン" in r["yaku"] and "ぱっくり" not in r["added"] and "ぱっくり" in r["raw"])
r = sc(["ぱかあ", "くぱあ", "まんこ", "ちんぽ"])
ok("ぱっくり+ご開帳 → 大開帳(5翻)。1+5+(ほか)", "大開帳" in r["merges"] and "ぱっくり" not in r["yaku"] and "ご開帳" not in r["yaku"])
base = r["han_no_merge"]
ok("  合体の差分 = 5 - (2+2) = +1", r["han"] - base == 1)
# group で消えていた役が元の合体: ぱかあ・くぱあ・ぱかっ・まんこ → 全開フルオープン(5)、ぱっくり(0)、ご開帳(2)。大開帳は 5-(0+2)=+3
r = sc(["ぱかあ", "くぱあ", "ぱかっ", "まんこ"])
ok("ぱっくりが group で消えていても、合体は成立し、差分は 5-(0+2)=+3", "大開帳" in r["merges"] and r["han"] - r["han_no_merge"] >= 3)
ok("合体は最大 %d つ" % S.merge_limit, all(len(S.score(ws, hi, oho)["merges"]) <= S.merge_limit for h in hands[:300] for ws, hi, oho, c in S.judge.partitions(h)))
# 合体の元の役は、2つの合体に重複しない
dup = 0
for h in hands[:a.n]:
    for ws, hi, oho, chu in S.judge.partitions(h):
        r = S.score(ws, hi, oho)
        used = [s for m in r["merges"] for s in next(x["source_yaku"] for x in S.M if x["name"] == m).split("|")]
        dup += len(used) != len(set(used))
ok(f"合体の元の役の重複 {dup}", dup == 0)

# ---- 4. 合体ごとに、成立する手を探す(語の組み合わせの探索) ----
def find_merge(name, tries=40000):
    for _ in range(tries):
        k = rng.choice((2, 3, 4))
        pool = rng.choice(THEME)
        ws = set(rng.sample(pool, min(k, len(pool))))
        while len(ws) < 4:
            ws.add(rng.randrange(len(W)))
        ws = list(ws)[:4]
        for hi in rng.sample(range(len(H)), 6):
            r = S.score(ws, hi, rng.choice((0, 0, 1, 2)))
            if name in r["merges"]:
                return ws, hi
    return None
def find_merge_exhaustive(m):
    # 元の役の語(params の語)の和集合が小さければ、4語の全組み合わせを調べる
    ws = set()
    for yn in m["source_yaku"].split("|"):
        for y in Y:
            if y["name"] == yn:
                for t in tokens_of(y):
                    try:
                        ws |= set(S._bits(S.token_mask(t)))
                    except Exception:
                        pass
    ws = sorted(ws)
    if len(ws) > 60:
        return None
    for comb in itertools.combinations(ws, 4):
        for hi in range(len(H)):
            if m["name"] in S.score(comb, hi, 0)["merges"]:
                return list(comb), hi
    return None
found = {m["name"]: find_merge(m["name"]) for m in S.M}
for m in S.M:
    if found[m["name"]] is None:
        found[m["name"]] = find_merge_exhaustive(m)
nf = [n for n, v in found.items() if v is None]
print(f"   探索で成立を確認できた合体: {len(found)-len(nf)}/{len(S.M)}。見つからなかった: {nf}(探索で見つからないだけ。成立しないとは限らない)")
print("すべてOK" if not ng else f"失敗 {ng}")
sys.exit(1 if ng else 0)
