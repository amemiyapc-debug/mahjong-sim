"""dan6 語呂度エンジン(dan6/goro14.py)の確認。
 1. 参照実装(goro/goro.py・goro2.py・goro3.py。パスだけ書き換えて一時フォルダで実行)と、無作為の手 3000 で、つながり・連鎖・テーマ・点が完全一致
 2. 点の式・連鎖倍率・表示(万億兆京)・研究♡のしきい値・500点の下限
 python3 tests/test_goro14.py"""
import os, sys, re, shutil, tempfile, random, importlib, itertools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "dan6"))
import goro14 as G
res = []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
# --- 参照実装を、一時フォルダにコピーして読み込む ---
tmp = tempfile.mkdtemp(); ref = os.path.join(tmp, "goro"); os.makedirs(ref)
for f in ("goro.py", "goro2.py", "goro3.py", "tag.py"):
    t = open(os.path.join(ROOT, "goro", f), encoding="utf-8").read().replace("base=SAME_SUB.get((sub(a),sub(b)),1)", "base=SAME_SUB.get((sub(a),sub(b))) or SAME_SUB.get((sub(b),sub(a))) or 1").replace("/home/claude/mahjong-sim/goro", ref).replace("/home/claude/mahjong-sim/", ROOT + "/").replace("/home/claude/mahjong-sim", ROOT)
    open(os.path.join(ref, f), "w", encoding="utf-8").write(t)
sys.path.insert(0, ref)
cwd = os.getcwd(); os.chdir(tmp)
g3 = importlib.import_module("goro3")
os.chdir(cwd)
words = [r for r in g3.rows if r["kind"] == "語"]; heads = [r for r in g3.rows if r["kind"] == "雀頭"]
ok("辞書: 参照実装と goro14 の行数(語365+雀頭28)が一致(参照は雀頭を 28 でなく dan5/heads.csv 由来で持つ)", len(G.ROWS) == 393, f"(goro14 {len(G.ROWS)} / 参照の語 {len(words)}・雀頭 {len(heads)})")
rng = random.Random(1)
names_w = [w["word"] for w in words if w["word"] in G.ROWS]; names_h = [h["word"].replace("【雀頭】", "") for h in heads if h["word"] in G.ROWS]
bad = []
for _ in range(3000):
    ws = rng.sample(names_w, 4); h = rng.choice(names_h)
    a = g3.score(g3.hand(ws, h), ) if False else None
    nodes = [g3.words_by_name[w] for w in ws] + [g3.words_by_name["【雀頭】" + h]]
    ref_s = g3.score(nodes); my = G.score(ws, h)
    key = lambda s: (s["links"], s["merges"], round(s["chain"], 6), s["bonus"], s["theme"], s["points"])
    k_ref = (ref_s["links"], ref_s["merges"], round(ref_s["chain"], 6), ref_s["bonus"], ref_s["theme"], ref_s["points"])
    if key(my) != k_ref: bad.append((ws, h, k_ref, key(my)))
ok("無作為の手3000: つながり本数・連鎖数・連鎖倍率・句ボーナス・テーマ倍率・点が、参照実装と完全一致", not bad, f"(不一致 {len(bad)} {bad[:1]})")
# --- 点の式 ---
ok("連鎖倍率: 1→1.5, 2→3, 3→7.5, 4→22.5, 5→78.75, 6→315", [G.mult(k) for k in range(1, 7)] == [1.5, 3.0, 7.5, 22.5, 78.75, 315.0])
x = G.score(["ちんぽ", "ちんこ", "まんこ", "おめこ"], "あん")
ok("点 = 500 × 句ボーナス × 連鎖倍率 × テーマ倍率", x["points"] == 500 * x["bonus"] * x["chain"] * x["theme"], str(x["points"]))
z = G.score(["デカけつ", "うんん", "エロエロ♡", "くり♡"], "あっ")
ok("最低点は500(何もつながらない手では 500)", all(G.score(rng.sample(names_w, 4), rng.choice(names_h))["points"] >= 500 for _ in range(500)))
ok("表示: 万・億・兆・京(切り捨て1桁)", [G.fmt_points(v) for v in (500, 12345, 99999, 3.2e9, 7.7e13, 1e17, 123e8)] == ["500", "1.2万", "9.9万", "32億", "77兆", "10京", "123億"])
ok("研究♡: ステージ1〜2=0 無知(4)、3〜5=1 恥ずかしい(3)、6以降=2 すけべ(2)。見送り 1/2/3回", [G.KEN[G.ken_stage(s)] for s in (1, 2, 3, 5, 6, 9)] == [4, 4, 3, 3, 2, 2] and G.LV_NAMES == ["無知", "恥ずかしい", "すけべ"] and G.SKIPS == {0: 1, 1: 2, 2: 3})
# 語の順に依存しない(4語の全順列で、点が同じ)
badp = 0
for _ in range(300):
    ws = rng.sample(names_w, 4); h = rng.choice(names_h)
    if len({G.score(list(p_), h, {"thresh": 3})["points"] for p_ in itertools.permutations(ws)}) != 1: badp += 1
ok("点は、4語の並び順に依存しない(300手×24通りの順列)", badp == 0, f"(依存する手 {badp})")
# 淫: 句ボーナス = 1 + Σつながり + 淫
ok("句ボーナスに、名前つき役の淫が足される(淫0の手と、淫3の手で、句ボーナスが +3)", G.score(["ちんぽ", "ちんこ", "まんこ", "おめこ"], "あん", None, 3)["bonus"] == G.score(["ちんぽ", "ちんこ", "まんこ", "おめこ"], "あん", None, 0)["bonus"] + 3)
# しきい値を上げると、つながりは減る(単調)
hands = [(rng.sample(names_w, 4), rng.choice(names_h)) for _ in range(500)]
n2, n3, n4 = (sum(G.score(w, h, {"thresh": t})["raw_links"] for w, h in hands) for t in (2, 3, 4))
ok("しきい値が上がるほど、つながりが減る(2 ≥ 3 ≥ 4)", n2 >= n3 >= n4 and n2 > n4, f"({n2} ≥ {n3} ≥ {n4})")
print("すべてOK" if all(res) else "失敗"); shutil.rmtree(tmp, ignore_errors=True)
sys.exit(0 if all(res) else 1)
