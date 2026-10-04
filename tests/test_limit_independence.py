"""強・弱CPUの捨て方は、ツモの上限(残りツモ回数)に依存しない。
上限6だけで回した結果と、上限(6,10,14,20)で回して6で打ち切った結果が完全に一致することを確かめる。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import simulator as sim

n = bad = 0
for wall in ("A", "B"):
    for g in range(300):
        seed = 500000 + g
        st = sim.make_setup(wall, seed, 14, (2, 3))
        for cpu in sim.CPUS:
            for L in (6, 10):
                alone = sim.play_game(st, cpu, (L,), seed ^ 0x9E3779B1)[L]
                multi = sim.play_game(st, cpu, (6, 10, 14, 20), seed ^ 0x9E3779B1)[L]
                n += 1
                if alone != multi:
                    bad += 1
                    print("MISMATCH", wall, cpu, L, alone, multi)
print(f"comparisons {n}, mismatch {bad}")
assert bad == 0
print("OK")
