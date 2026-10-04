import sys
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, argparse
import simulator as sim

sim.ARGS = argparse.Namespace(han_point=1000)

class Fake:
    def __init__(s, seq): s.seq = list(seq)
    def integers(s, lo, hi, size): return np.full(size, s.seq.pop(0))

def run(seq, pad, games, policy=None, N=8):
    np.random.default_rng = lambda seed: Fake(seq + [pad] * 40)
    out = sim.simulate_runs(games, 0, [N], [4000, 5000], policy, 500, 4, 3, 1)
    return {k: v[:3] for k, v in out.items()}  # (クリア, バースト, 焦らし)。4番目は総ツモ数

WIN = ("win", 3, (), 0); TP = ("tenpai", False); TPB = ("tenpai", True); NO = ("noten",)
g = [(WIN,) * 2, (TP,) * 2, (NO,) * 2]   # 0:win(3翻) 1:tenpai 2:noten

r = run([1, 1, 0, 1, 1, 1, 1], 2, g); print(1, r)          # tp,tp,win=3000+1000 / その後tp4連続でバースト
assert r[(8, 4000)] == (1.0, 0.0, 0.0) and r[(8, 5000)] == (0.0, 1.0, 1.0)

r = run([], 0, [(TP,) * 2]); print(2, r)                   # 全部テンパイ → 即バースト
assert r[(8, 4000)] == (0.0, 1.0, 1.0)

g2 = [(WIN,) * 2, (TPB,) * 2, (NO,) * 2]
r = run([1, 1, 1, 1], 0, g2, policy=4); print(3, r)       # 4回目を崩す → バーストしない
assert r[(8, 5000)][1] == 0.0

r = run([1, 1, 2, 0, 0, 0], 0, g, N=1); print(4, r)       # tp,tp,noten(積み消失),win → 3000のみ (N=1: noten消費で終了)
r = run([1, 1, 2], 0, g, N=3); print(4.5, r)              # tp,tp,noten,win,win → 6000
assert r[(3, 4000)][0] == 1.0 and r[(3, 5000)][0] == 1.0

r = run([1, 1, 1, 0], 0, g, N=1)                          # tp x3 → win(3000+1500=4500)  N=1
print(5, r)
assert r[(1, 4000)][0] == 1.0 and r[(1, 5000)][0] == 0.0
print("OK")
