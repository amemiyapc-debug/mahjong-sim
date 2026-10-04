"""ステージ制(simulate_stages)の動きを、決まった順番のゲーム結果で確かめる。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import simulator as sim


class Fake:
    def __init__(s, seq): s.seq = list(seq)
    def integers(s, lo, hi, size): return np.full(size, s.seq.pop(0))


def run(seq, pad, games, L=12, mult=1.0, N=1, table="Y", base=5000, runs=3, **kw):
    np.random.default_rng = lambda seed: Fake(seq + [pad] * 400)
    return sim.simulate_stages(games, L, mult, N, table, runs, 1, base=base, **kw)


WIN5 = ("win", 5, (), 7, 0)    # 5翻(Y: 8,000点)、7ツモ
WIN1 = ("win", 1, (), 3, 0)    # 1翻(1,000点)、3ツモ
TP = ("tenpai", False)         # 崩せないテンパイ流局
NO = ("noten",)

# 1) 毎ゲーム満貫 → N=1でも全ステージ突破。上限30クリアで終了。総ツモ = 30ゲーム x 7
o = run([], 0, [WIN5])
assert (o["final_stage"] == 30).all() and o["capclear"].all() and (o["total"] == 30 * 7).all()
assert o["success"][1:31].tolist() == [3] * 30 and o["reach"][1:31].tolist() == [3] * 30

# 2) 毎ゲームノーテン、N=3 → 3ゲーム消費で失敗を3回 → ステージ1でゲームオーバー。総ツモ = 3 x 3 x 12
o = run([], 0, [NO], N=3)
assert (o["final_stage"] == 1).all() and not o["capclear"].any()
assert (o["total"] == 3 * 3 * 12).all() and o["fail_n"][1] == 9 and o["fail_b"][1] == 0

# 3) 毎ゲーム崩せないテンパイ → 連続4回目でバースト。ライフ3 → 12ゲーム。消費ゲームは0
o = run([], 0, [TP], N=5)
assert (o["final_stage"] == 1).all() and o["fail_b"][1] == 9 and o["fail_n"][1] == 0

# 4) 積み点: tp,tp,win(1翻=1,000) → 1,000+積み1,000 = 2,000。目標2,000(base)なら1ゲームのアガリでステージ突破
g = [WIN1, TP, NO]
o = run([1, 1, 0], 0, g, N=3, base=2000, table="X", lives=1, cap=1)
assert o["capclear"].all() and o["final_stage"][0] == 1, o["final_stage"]
# 積み点なし(win単独)では1,000なので届かない → 3ゲーム(全部1,000)なら届く(3,000)が、ここではN=1で失敗
o = run([0], 0, g, N=1, base=2000, table="X", lives=1, cap=1)
assert not o["capclear"].any()

# 5) ノーテンで積み点が消える: tp,tp,noten,win(1,000) → 1,000のまま(目標2,000に届かない。N=2で失敗)
o = run([1, 1, 2, 0], 2, g, N=2, base=2000, table="X", lives=1, cap=1)
assert not o["capclear"].any()

# 6) ステージが変わると積み点がリセット: ステージ1(目標1,000)を tp,tp,win(1,000)で突破(積み1,000込みで2,000)。
#    ステージ2(目標1,000, mult=1)は新しいステージなので、積み点0から。win(1,000)単独で突破できる
o = run([1, 1, 0, 0], 0, g, N=1, base=1000, table="X", lives=1, cap=2)
assert o["capclear"].all() and o["final_stage"][0] == 2
# 目標を上げて、積み点が持ち越されないことを確かめる: ステージ2の目標1,500
#   tp,tp,win → 2,000でステージ1突破 → ステージ2(目標1,500): win(1,000)単独 → 届かない(N=1で失敗)
o = run([1, 1, 0, 0], 0, g, N=1, base=1000, mult=1.5, table="X", lives=1, cap=2)
assert not o["capclear"].any() and o["final_stage"][0] == 2

# 7) ライフは失敗のたびに減り、ステージを跨いで戻らない: ステージ1突破 → ステージ2で3回失敗 → ゲームオーバー(到達ステージ2)
o = run([0], 2, [WIN5, TP, NO], N=1, base=5000, mult=100.0, lives=3)
assert (o["final_stage"] == 2).all() and o["success"][1] == 3 and o["fail_n"][2] == 9
print("OK")
