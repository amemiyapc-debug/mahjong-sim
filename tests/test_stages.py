"""ステージ制(simulate_stages)の動きを、決まった順番のゲーム結果で確かめる。
ルール: バーストなし / 焦らし(連続3回)は記録のみ / 積み点は連続1回ごと500点・連続5回分まで /
連続30回で強制消費 / アガリ・ノーテン・ステージ変更で積み点リセット。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
import simulator as sim


class Fake:
    def __init__(s, seq): s.seq = list(seq)
    def integers(s, lo, hi, size): return np.full(size, s.seq.pop(0))


def run(seq, pad, games, L=12, mult=1.0, N=1, table="X", base=5000, runs=3, **kw):
    np.random.default_rng = lambda seed: Fake(seq + [pad] * 500)
    return sim.simulate_stages(games, L, mult, N, table, runs, 1, base=base, **kw)


WIN5 = ("win", 5, (), 7, 0)    # 5翻(Y: 8,000点)、7ツモ
WIN1 = ("win", 1, (), 3, 0)    # 1翻(1,000点)、3ツモ
TP = ("tenpai", False)
NO = ("noten",)
g = [WIN1, TP, NO]             # index 0:アガリ 1:テンパイ流局 2:ノーテン

# 1) 毎ゲーム満貫(Y) → N=1でも全ステージ突破。上限30クリアで終了。総ツモ = 30ゲーム x 7
o = run([], 0, [WIN5], table="Y")
assert (o["final_stage"] == 30).all() and o["capclear"].all() and (o["total"] == 30 * 7).all()
assert o["success"][1:31].tolist() == [3] * 30 and o["reach"][1:31].tolist() == [3] * 30

# 2) 毎ゲームノーテン、N=3 → 3ゲーム消費で失敗を3回 → ステージ1でゲームオーバー。総ツモ = 3 x 3 x 12
o = run([], 2, g, N=3)
assert (o["final_stage"] == 1).all() and not o["capclear"].any() and (o["total"] == 3 * 3 * 12).all()

# 3) 積み点: テンパイ2回→アガリ(1翻1,000) = 1,000 + 積み1,000 = 2,000 で、目標2,000を1ゲームで達成。積み点なしなら届かない
o = run([1, 1, 0], 0, g, N=3, base=2000, lives=1, cap=1)
assert o["capclear"].all()
o = run([0], 0, g, N=1, base=2000, lives=1, cap=1)
assert not o["capclear"].any()

# 4) 積みは連続5回分まで: テンパイ6回→アガリ = 1,000 + 500x5 = 3,500(6回分の3,000ではない)
o = run([1] * 6 + [0], 0, g, N=1, base=3500, lives=1, cap=1)
assert o["capclear"].all()
o = run([1] * 6 + [0], 0, g, N=1, base=3501, lives=1, cap=1)
assert not o["capclear"].any()

# 5) バーストなし: テンパイが4回以上続いても失敗しない。テンパイ4回→アガリ = 1,000 + 2,000 = 3,000
o = run([1] * 4 + [0], 0, g, N=1, base=3000, lives=1, cap=1)
assert o["capclear"].all() and o["attempts"][1] == 3 // 3 * 3

# 6) ノーテンで積み点が消える: テンパイ2回→ノーテン→アガリ(1,000)。N=2で目標2,000に届かず失敗(ライフ1)
o = run([1, 1, 2, 0], 2, g, N=2, base=2000, lives=1, cap=1)
assert not o["capclear"].any()

# 7) ステージが変わると積み点リセット: テンパイ2回→アガリでステージ1(目標1,000)を突破(2,000)。
#    ステージ2(目標1,500)は積み点0から: アガリ1,000単独では届かない(N=1で失敗)
o = run([1, 1, 0, 0], 0, g, N=1, base=1000, mult=1.5, lives=1, cap=2)
assert not o["capclear"].any() and o["final_stage"][0] == 2

# 8) ライフは失敗のたびに減り、ステージを跨いで戻らない: ステージ1突破 → ステージ2で3回失敗 → ゲームオーバー(到達2)
o = run([0], 2, [WIN5, TP, NO], N=1, base=5000, mult=100.0, table="Y", lives=3)
assert (o["final_stage"] == 2).all() and o["success"][1] == 3 and o["attempts"][2] == 9

# 9) 焦らしプレイ(連続3回で達成): 3回続けば1回、4回続いても1回、3回+3回で2回。2回続きでは達成しない
o = run([1, 1, 1, 0], 2, g, N=1, base=99999, lives=1, cap=1)
assert (o["tease_n"] == 1).all()
o = run([1] * 4 + [0], 2, g, N=1, base=99999, lives=1, cap=1)
assert (o["tease_n"] == 1).all()
o = run([1, 1, 1, 2, 1, 1, 1, 0], 2, g, N=3, base=99999, lives=1, cap=1)
assert (o["tease_n"] == 2).all()
o = run([1, 1, 0], 2, g, N=1, base=99999, lives=1, cap=1)
assert (o["tease_n"] == 0).all()

# 10) 安全装置: テンパイ30回で強制的に1ゲーム消費(ノーテン扱い)。毎ゲームテンパイ、N=1 → 30テンパイで1消費→失敗、x3(ライフ3)
o = run([], 1, g, N=1)
assert o["forced"] == 3 * 3 and (o["total"] == 3 * 30 * 12).all() and (o["final_stage"] == 1).all()
assert (o["consumed"] == 3).all()
print("OK")
