"""sim14.py の確認。
1. 牌の枚数ルール: 新ルールが tile_copies_adopted.csv と全牌で一致 / 山294枚(ぉ゛4込み)・牌41種 / 旧ルールは max(4,使う語の数)
2. ゲームの整合: 手牌は常に13/14枚・牌の総数が保存される・CPUの捨て牌は手牌にある・アガリはjudge14の判定と一致
3. テンパイ判定: CPUが返す「捨てた後にテンパイか」を、総当たり(山に残る各牌を足して、14牌がアガリ形か)と比べる(不一致0)
   hint モードと exact モードの両方。

  python3 tests/test_sim14.py [--dir v13m] [--states 300]
"""
import argparse, os, random, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from sim14 import Game, tile_copies, check_tiles

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default=os.path.join(HERE, "..", "v13m"))
ap.add_argument("--states", type=int, default=300)
a = ap.parse_args()
ng = 0
def ok(msg, cond):
    global ng
    print(("OK  " if cond else "NG  ") + msg)
    ng += (not cond)

r = check_tiles(a.dir)
ok(f"新ルールの枚数が tile_copies_adopted.csv と一致(不一致 {len(r['diff'])}。使う語の数の不一致 {len(r['used_diff'])})", not r["diff"] and not r["used_diff"])
ok(f"山 {r['new_total']}枚(ぉ゛{r['oho']}枚込み)・牌 {r['new_types']}種", r["new_total"] == 294 and r["new_types"] == 41 and r["oho"] == 4)
old = tile_copies(a.dir, "old")
ok(f"旧ルール: 山 {sum(old.values())}枚(max(4,使う語の数)+ぉ゛4)", old["ん"] == 38 and old["が"] == 4 and old["ぉ゛"] == 4)

for cpu in ("hint", "exact"):
    G = Game(a.dir, tile_copies(a.dir, "new"), 12, cpu=cpu)
    rng = random.Random(11)
    bad_t = bad_state = bad_win = n = n_t = 0
    for g in range(a.states // 10):
        wall = G.wall0[:]; rng.shuffle(wall); total = Counter(wall)
        wc = Counter(wall); hand = [wall.pop() for _ in range(13)]
        for t in hand: wc[t] -= 1
        disc_all = []
        for turn in range(1, 13):
            t = wall.pop(); wc[t] -= 1; hand.append(t)
            win = bool(G.J.partitions(hand))
            ok_state = len(hand) == 14 and Counter(hand) + Counter(disc_all) + wc == total
            bad_state += not ok_state
            if win:
                bad_win += G.S.best(hand) is None
                break
            d, tp = G.choose(hand, wc)
            bad_state += d not in hand
            hand.remove(d); disc_all.append(d)
            # 総当たり
            brute = any(G.J.partitions(hand + [x]) for x in [x for x, k in wc.items() if k > 0])
            n += 1; n_t += brute
            bad_t += (brute != tp)
    ok(f"[{cpu}] テンパイ判定: 状態 {n}(テンパイ {n_t})で、総当たりとの不一致 {bad_t} / 手牌・牌の保存の不一致 {bad_state} / アガリ判定の不一致 {bad_win}",
       bad_t == 0 and bad_state == 0 and bad_win == 0)
print("すべてOK" if not ng else f"失敗 {ng}")
sys.exit(1 if ng else 0)
