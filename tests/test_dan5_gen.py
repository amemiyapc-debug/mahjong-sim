"""dan5/gen.py の出力の確認(辞書343語→重複統合で342語・役177行・合体36・牌の枚数)。
  python3 tests/test_dan5_gen.py
"""
import csv, os, subprocess, sys
from collections import Counter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
subprocess.run([sys.executable, os.path.join(ROOT, "dan5", "gen.py")], check=True, capture_output=True)   # 重複があれば、ここで失敗する
rd = lambda n: list(csv.DictReader(open(os.path.join(ROOT, "dan5", n), encoding="utf-8-sig")))
W, Y, M = rd("words.csv"), rd("yaku.csv"), rd("yaku_merge.csv")
ng = 0
def ok(msg, c):
    global ng; print(("OK  " if c else "NG  ") + msg); ng += (not c)
nrm = lambda t: {"ぉ゛": "お", "っ": "つ"}.get(t, t)
src = Counter(w["source"] for w in W)
ok(f"語 {len(W)}(辞書CSV285語のうち、牌の組み合わせが同じ ぉ゛っぉ゛っ を おっおっ に統合して284 + 前置き58)", len(W) == 342 and src["前置き(案B)"] == 58 and src["×2"] == 61)
keys = Counter(tuple(sorted(nrm(t) for t in w["tiles"].split("|"))) for w in W)
ok("牌の組み合わせ(つ=っ・ぉ゛=お)が同じ語の重複なし", max(keys.values()) == 1)
ok("×2語は、語幹2牌+×2の3牌", all(w["tiles"].endswith("|×2") and w["tile_count"] == "3" for w in W if w["type"] == "×2"))
ok("はしごでは×2語の語幹を同じ語幹とみなす(ちんちん=stem ちん・まめまめ=stem くり)", {w["word"]: w["stem"] for w in W if w["type"] == "×2"}["ちんちん"] == "ちん" and {w["word"]: w["stem"] for w in W if w["type"] == "×2"}["まめまめ"] == "くり")
ok("ち-ち語幹(ちち♡・ちちコキ・おちち)は、部位が胸", all(next(w for w in W if w["word"] == n)["part"] == "胸" for n in ("ちち♡", "ちちコキ", "おちち")))
slot = Counter(w["slot_no"] for w in W)
ok(f"7スロット+前置き(0〜6): {dict(sorted(slot.items()))}", sorted(slot) == list("0123456"))
names = [y["name"] for y in Y]
ok(f"役 {len(Y)}行・{len(set(names))}種(v1.3n)", len(Y) == 177)
ok("v1.3n の改名: 童貞目線→目が釘づけ ほか5件、新役9つ", all(n in names for n in ("目が釘づけ", "中イキ", "むちむち自慢", "顔にぶっかけ", "おくちまんこ", "ぶっかけ", "ぶっかけでイクっ", "あな好き", "じっくり責め", "女王様と下僕", "女王様のご命令", "ぱいにぶっかけ", "まんにぶっかけ", "けつにぶっかけ")) and "童貞目線" not in names)
ok(f"合体 {len(M)}個(元の役が、改名後の名前)", len(M) == 36 and all(s in names for m in M for s in m["source_yaku"].split("|")))
def setsize(yname, grp):
    y = next(y for y in Y if y["name"] == yname); g = y["params"].split(";")[grp]; return len(g.replace("set=", "").split("|"))
ok("キス語・絶頂・結末・喘ぎ声の語集合が拡張されている(キスの雨 / 絶頂そろい / 喘ぎ二重唱)", setsize("キスの雨", 1) == 23 and setsize("絶頂そろい", 1) == 25 and setsize("喘ぎ二重唱", 1) == 29)
from yaku14 import Scorer
S = Scorer(os.path.join(ROOT, "dan5"))
ok("Scorer が全ての役・合体を読める(参照する語が、辞書にある)", len(S.W) == 342 and len(S.Y) == 177 and len(S.M) == 36 and not S.judge.flex)
cs = rd("tile_copies_conditions.csv")
ok("山の枚数(MODX,×2): " + str([(c["MODX"], c["x2_copies"], c["wall_tiles"]) for c in cs]), [int(c["wall_tiles"]) for c in cs] == [347, 339, 329, 346, 348])
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
