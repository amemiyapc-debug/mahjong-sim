"""巡目ごとの記録(trace)が、チェックポイントの結果と整合していることを確かめる。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import simulator as sim

n = bad = 0
for wall in ("A", "B"):
    for g in range(300):
        seed = 700000 + g
        st = sim.make_setup(wall, seed, 14, (2, 3))
        for cpu in sim.CPUS:
            res = sim.play_game(st, cpu, (6, 10, 14, 20), seed ^ 0x9E3779B1, trace=True)
            win_turn, mask = res["trace"]
            for cp in (6, 10, 14, 20):
                r = res[cp]
                n += 1
                if r[0] == "win":
                    ok = win_turn == r[3] and win_turn <= cp
                else:
                    ok = (win_turn == -1 or win_turn > cp) and bool(mask >> cp & 1) == (r[0] == "tenpai")
                if not ok:
                    bad += 1
                    print("MISMATCH", wall, cpu, cp, r, res["trace"])
print(f"checks {n}, mismatch {bad}")
assert bad == 0
print("OK")
