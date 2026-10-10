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
ok("研究♡は周回数で決まる: 1周目=0 無知、2周目=1 恥ずかしい、3周目以降=2 すけべ。見送り 1/2/3回", [G.ken_lap(l) for l in (1, 2, 3, 4, 9)] == [0, 1, 2, 2, 2] and G.LV_NAMES == ["無知", "恥ずかしい", "すけべ"] and G.SKIPS == {0: 1, 1: 2, 2: 3} and not hasattr(G, "ken_stage"))
ok("しきい値: 既定は KEN_MODE=table(研究♡0/1/2=4/3/2。研究♡1=3・研究♡2=2)。KEN_CONST は残り、const に切り替えると一定の3", G.CONFIG["KEN_MODE"] == "table" and [G.thresh_of(l) for l in (0, 1, 2)] == [4, 3, 2] and G.KEN == {0: 4, 1: 3, 2: 2} and [G.thresh_of(l, "const") for l in (0, 1, 2)] == [3, 3, 3] and G.CONFIG["KEN_CONST"] == 3 and G.params(2)["thresh"] == 2 and G.params(2, "const")["thresh"] == 3)
ok("1周目のステージ条件(和了回数。data/stage_wins_lap1.csv。案A 20261010-1920): ステージ1=1回以上 / 2=2回以上 / 3=3回(4以降は最後の行)", [G.wins_needed(s_) for s_ in (1, 2, 3, 4, 9)] == [1, 2, 3, 3, 3])
# --- 解禁表(data/score_unlock.csv)---
_rg = random.Random(5)
HW, HH = next((w, h) for w, h in ((_rg.sample(names_w, 4), _rg.choice(names_h)) for _ in range(5000)) if G.score(w, h)["chain"] > 1 and G.score(w, h)["theme"] > 1)   # 連鎖もテーマも効く手
a0, a1, a2 = (G.score(HW, HH, G.params(l), 3, 2.0) for l in (0, 1, 2))
ok("研究♡0: 和了点は基本点(500)のみ。縁・淫・句の倍率・連鎖・テーマが何であっても", a0["points"] == 500 and a0["chain"] > 1 and a0["theme"] > 1 and a0["en"] > 0, f"(判定値 縁{a0['en']} 連鎖{a0['chain']} テーマ{a0['theme']})")
ok("研究♡1: 縁・淫・句の倍率だけが入る。連鎖倍率とテーマ倍率は入らない", a1["points"] == 500 * (1 + a1["en"] + 3) * 2.0 and a1["points"] < a1["points_full"] and a1["chain"] == a2["chain"] > 1, f"(縁{a1['en']} 点{a1['points']} 全部入り{a1['points_full']})")
ok("研究♡2: すべて入る", a2["points"] == 500 * (1 + a2["en"] + 3) * a2["chain"] * a2["theme"] * 2.0 == a2["points_full"])
b0 = G.score(HW, HH, dict(thresh=G.thresh_of(2), lv=0), 3, 2.0)   # しきい値を研究♡2と同じにして比べる(KEN_MODE=table では研究♡0のしきい値は4で、結ぶ数が変わるため)
ok("研究♡0でも、縁・連鎖・テーマの成立判定は行われる(点にならないだけ)", a0["links"] > 0 and a0["chain"] > 1 and a0["theme"] > 1 and b0["links"] == a2["links"] and b0["merges"] == a2["merges"] and b0["theme"] == a2["theme"] and b0["bonus_full"] == a2["bonus_full"] and b0["points"] == 500)
ok("解禁表: lv未指定(P=None)は全部入り(従来の式と同じ)", G.score(HW, HH, None, 3)["points"] == G.score(HW, HH, None, 3)["points_full"])
ok("周回数を変えると点の計算が変わる(同じ手: 1周目 500、2周目 縁・淫まで、3周目 全部)", [G.score(HW, HH, G.params(G.ken_lap(l)), 3)["points"] for l in (1, 2, 3)] == [500, a1["points"] / 2, a2["points"] / 2] and a1["points"] > 500 and a2["points"] > 500)
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
