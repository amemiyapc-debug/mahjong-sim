"""game/core.js の役判定との照合用に、Python(yaku14.Scorer)側の判定結果を JSON に出す。
  --mode sample : 4語(別々)+雀頭+ぉ゛の枚数 を乱数で n 組(役の語を多めにした偏りのある抽出を半分)
  --mode subset : 辞書から等間隔に40語を選び、その全組み合わせ C(40,4)=91,390 組(雀頭なし)
出力: [{four:[語index×4], head:雀頭index|-1, oho:ぉ゛の枚数, raw:[成立した役名(group の絞り込み前)], han:翻(合体なし)}]
  python3 tests/make_parity_sample.py --dir dan5 --mode sample --n 30000 --out /tmp/parity_sample.json
"""
import argparse, itertools, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from yaku14 import Scorer
from handgen import make_gen
ap = argparse.ArgumentParser()
ap.add_argument("--dir", default="dan5"); ap.add_argument("--mode", default="sample"); ap.add_argument("--n", type=int, default=30000)
ap.add_argument("--seed", type=int, default=20261020); ap.add_argument("--out", required=True)
a = ap.parse_args()
S = Scorer(os.path.join(ROOT, a.dir)); rng = random.Random(a.seed)
out = []
def one(four, head, oho):
    hits = S.raw_hits(four, head if head >= 0 else 0, oho) if head >= 0 else S.raw_hits_nohead(four)
    r = S.reduce(hits)
    out.append(dict(four=list(four), head=head, oho=oho, raw=sorted({S.Y[i]["name"] for i in hits}), han=1 + sum(r.values())))
# 雀頭なしの判定: 雀頭の条件は不成立にするため、head 行を飛ばす
def raw_hits_nohead(self, words):
    s = 0
    for w in words: s |= 1 << w
    return sorted([ri for ri, f in self.word_rows if f(s)])
Scorer.raw_hits_nohead = raw_hits_nohead
if a.mode == "sample":
    gen, theme = make_gen(S, rng)
    for k in range(a.n):
        if k % 2 == 0:
            four = rng.sample(range(len(S.W)), 4)
        else:
            _, four = gen()
            four = four[:4]
        out.append(None); out.pop()
        one(four, rng.randrange(len(S.H)), rng.choice((0, 0, 1, 2)))
else:
    ws = list(range(len(S.W)))[::max(1, len(S.W) // 40)][:40]
    for four in itertools.combinations(ws, 4): one(four, -1, 0)
json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
print(a.mode, len(out), "組 →", a.out)
