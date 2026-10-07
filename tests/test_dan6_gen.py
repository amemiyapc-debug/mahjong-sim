"""dan6/gen.py の出力の確認(辞書365語=v16の307+前置き58・雀頭28・役87種・合体17・牌の枚数)。
  python3 tests/test_dan6_gen.py"""
import csv, os, subprocess, sys
from collections import Counter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
subprocess.run([sys.executable, os.path.join(ROOT, "dan6", "gen.py")], check=True, capture_output=True)   # 重複があれば、ここで失敗する
rd = lambda n, d="dan6": list(csv.DictReader(open(os.path.join(ROOT, d, n), encoding="utf-8-sig")))
W, H, Y, M, C = rd("words.csv"), rd("heads.csv"), rd("yaku.csv"), rd("yaku_merge.csv"), rd("tile_copies.csv")
ng = 0
def ok(msg, c):
    global ng; print(("OK  " if c else "NG  ") + msg); ng += (not c)
nrm = lambda t: {"ぉ゛": "お", "っ": "つ"}.get(t, t)
ok(f"語 {len(W)}(v16の307語 + 修飾3型58語)・雀頭 {len(H)}(しり を含む)", len(W) == 365 and len(H) == 28 and any(h["head"] == "しり" and h["tiles"] == "し|り" for h in H))
keys = Counter(tuple(sorted(nrm(t) for t in w["tiles"].split("|"))) for w in W)
ok("牌の組み合わせ(つ=っ・ぉ゛=お、×2語、前置き語を含む)が同じ語の重複なし", max(keys.values()) == 1)
x2 = [w for w in W if w["type"] == "×2"]
ok(f"×2語 {len(x2)}: 語幹2牌+×2の3牌", len(x2) == 63 and all(w["tiles"].endswith("|×2") and w["tile_count"] == "3" for w in x2))
ok("後ろ(しり・ぱち・しつ・しこ)の部位語がある", {"しりしり", "しこしこ"} <= {w["word"] for w in W} or any(w["part"] == "後ろ" and w["stem"] == "しり" for w in W))
cp = {r["tile"]: (int(r["used_in_words"]), int(r["copies"])) for r in C}
ok("牌の枚数: し 20語→10枚 / り 31→10 / け 21→10 / つ 32→10 / ぽ 11→6 / お 34→10 / ×2 13枚 / ぉ゛ 4枚",
   cp["し"] == (20, 10) and cp["り"] == (31, 10) and cp["け"] == (21, 10) and cp["つ"] == (32, 10) and cp["ぽ"] == (11, 6) and cp["お"] == (34, 10) and cp["×2"][1] == 13 and cp["ぉ゛"][1] == 4)
from yaku14 import Scorer
ok("ちゅ→つ の代用は廃止(ちゅ は、くちゅっ・ちゅっちゅ などの語の牌としてだけ使う。つ=っ・ぉ゛=お は残る)", not Scorer(os.path.join(ROOT, "dan6")).judge.flex)
cs = rd("tile_copies_conditions.csv")
ok("山の枚数(MODX,×2): " + str([(c["MODX"], c["x2_copies"], c["wall_tiles"]) for c in cs]), [(c["MODX"], int(c["x2_copies"]), int(c["wall_tiles"])) for c in cs] == [("0.05", 13, 361), ("0.1", 13, 369), ("0.0", 13, 351)])
names = [y["name"] for y in Y]; fin = [r["name"] for r in rd("yaku_final_v2.csv", "data")]
ok(f"役 {len(Y)}行・{len(set(names))}種 = yaku_final_v2.csv の {len(set(fin))}種と一致(1本化・飾り・削除を反映)", set(names) == set(fin) and len(set(names)) == 87)
ok("削除された役(全開フルオープン など)・はじめての語ボーナスは、役にない", "全開フルオープン" not in names)
ok(f"合体 {len(M)}個(名前つき合体17。元の役が、すべて存在)", len(M) == 17 and all(s in names for m in M for s in m["source_yaku"].split("|")))
mf = {r["name"]: r for r in rd("merge_final_v3.csv", "data")}
ok("合体の名前が merge_final_v3.csv と一致", {m["name"] for m in M} == set(mf))
from yaku14 import Scorer
S = Scorer(os.path.join(ROOT, "dan6"))
ok("Scorer が全ての役・合体を読める(新しい条件・slot: を含む)", len(S.W) == 365 and len(S.M) == 17 and len({y["name"] for y in S.Y}) == 87 and not S.judge.flex)
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
