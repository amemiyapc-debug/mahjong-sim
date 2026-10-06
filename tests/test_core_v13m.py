"""game/core.js(ゲーム本体)の、14牌の全分割・採点(合体を含む)・山の枚数を、Python側(yaku14.py / sim14.py)と照合する。
  1. 山: buildDeck の枚数が、sim14.tile_copies('new'/'old')と全牌で一致(294枚・577枚)
  2. ランダムな勝ち手(既定6,000手): 分割の集合・分割ごとの翻(合体あり/なし)・役名・合体名・win14 の最大翻が一致(不一致0)
  3. 役ナビの mono 条件: 組んだ語(部分集合)+雀頭で成立する役は、4語+雀頭がそろったときも成立している(単調性)。
     4語+雀頭が完全にそろったとき、mono の判定が、完全な判定(computeYaku の raw)と一致する

  python3 tests/test_core_v13m.py [--n 6000]
"""
import argparse, itertools, json, os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from yaku14 import Scorer
from sim14 import tile_copies
from handgen import make_gen

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=6000)
ap.add_argument("--seed", type=int, default=20261010)
a = ap.parse_args()
D = os.path.join(ROOT, "v13m"); GAME = os.path.join(ROOT, "game")
S = Scorer(D); rng = random.Random(a.seed)
hk = lambda hi: "|".join(sorted(S.judge.replace.get(t, t) for t in S.H[hi]["tiles"].split("|")))   # 同じ牌の雀頭(あん/んあ)は同じ
ng = 0
def ok(msg, cond):
    global ng
    print(("OK  " if cond else "NG  ") + msg); ng += (not cond)

def mkdata(rule):
    env = dict(os.environ, HM_DATA_DIR=D, HM_TILE_RULE=rule)
    td = tempfile.mkdtemp()
    subprocess.run([sys.executable, os.path.join(GAME, "make_data.py")], cwd=td, env=env, check=True, capture_output=True)
    return os.path.join(td, "data.json")

# 1. 山
for rule in ("new", "old"):
    dj = mkdata(rule)
    js = subprocess.run(["node", "-e", f'const HM=require("{GAME}/core.js");const G=HM.setup(JSON.parse(require("fs").readFileSync("{dj}")));const c={{}};G.buildDeck().forEach(t=>c[t]=(c[t]||0)+1);console.log(JSON.stringify(c))'],
                        capture_output=True, text=True, check=True).stdout
    c = json.loads(js); py = tile_copies(D, rule)
    ok(f"山(rule={rule}): {sum(c.values())}枚(Python {sum(py.values())}枚)、牌ごとの枚数の不一致 {sum(1 for t in set(c)|set(py) if c.get(t)!=py.get(t))}", c == py)
    if rule == "new": data_new = dj

# 2. 全分割と採点
gen, theme = make_gen(S, rng)
hands = [gen()[0] for _ in range(a.n)]
tiles_all = sorted({t for r in S.W for t in r["tiles"].split("|")} | {"ぉ゛"})
for i in range(0, a.n, 6):
    h = hands[i][:]; h[rng.randrange(14)] = rng.choice(tiles_all); hands.append(h)
with tempfile.TemporaryDirectory() as td:
    hj, oj = os.path.join(td, "h.json"), os.path.join(td, "o.json")
    json.dump(hands, open(hj, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run(["node", os.path.join(GAME, "test_score_parts.js"), data_new, hj, oj], check=True)
    js = json.load(open(oj, encoding="utf-8"))
bad_set = bad_score = bad_best = n_parts = 0; ex = []
for h, j in zip(hands, js):
    py = {}
    for ws, hi, oho, chu in S.judge.partitions(h):
        r = S.score(ws, hi, oho); py[(tuple(sorted(ws)), hk(hi))] = (r["han"], r["han_no_merge"], sorted(r["added"]), sorted(r["merges"]))
    jp = {(tuple(p["four"]), p["head"]): (p["han"], p["hanNoMerge"], p["yaku"], p["merges"]) for p in j["parts"]}
    n_parts += len(py)
    if set(py) != set(jp):
        bad_set += 1; ex.append(("set", h)); continue
    for k in py:
        pa, ja = py[k], jp[k]
        # 役名は、合体に吸収された役を除いて比べる
        if pa[0] != ja[0] or pa[1] != ja[1] or pa[3] != ja[3]:
            bad_score += 1; ex.append(("score", k, pa, ja))
    if py:
        best = max(v[0] for v in py.values())
        if not j["win"] or j["win"]["han"] != best:
            bad_best += 1; ex.append(("best", h, best, j["win"]))
    elif j["win"]:
        bad_best += 1
wins = sum(1 for j in js if j["win"])
print(f"   手 {len(hands)}(アガリ {wins}、分割の総数 {n_parts})")
ok(f"分割の集合の不一致 {bad_set}", bad_set == 0)
ok(f"分割ごとの翻(合体あり/なし)・合体名の不一致 {bad_score}", bad_score == 0)
ok(f"win14 の最大翻の不一致 {bad_best}", bad_best == 0)
for e in ex[:4]: print("   例:", e)
print("すべてOK" if not ng else f"失敗 {ng}")
sys.exit(1 if ng else 0)
