"""KEN_MODE=table の測定値(20261010-1210): 解禁表+KEN で、和了点の中央値が 500 / 4,500 / 354,375。
 測定結果(ichishuu/results_score_unlock_20261008.json。python3 ichishuu/measure_score_unlock.py で作る)を読み、設定と照合する。
 1周目のステージ条件の測定(ichishuu/results_stage_lap1_20261010.json)の形も確認する。 python3 tests/test_score_measure.py"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "dan6"))
import goro14 as G
res = []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
d = json.load(open(os.path.join(ROOT, "ichishuu", "results_score_unlock_20261008.json"), encoding="utf-8"))
m = {k: v["median"] for k, v in d["dist"].items()}
ok("設定は KEN_MODE=table(研究♡1=3・研究♡2=2)", G.CONFIG["KEN_MODE"] == "table" and G.thresh_of(1) == 3 and G.thresh_of(2) == 2)
ok("測定は、前回までと同じ試合(digest e4eadad994d27ee3)・691和了", d["same_games_as_before"] and d["wins"] == 691)
ok("研究♡0/1/2 の和了点の中央値 = 500 / 4,500 / 354,375(報告済みの「解禁表+KEN(4/3/2)」と一致)", [m["lv0"], m["lv1"], m["lv2"]] == [500, 4500, 354375], str([m["lv0"], m["lv1"], m["lv2"]]))
ok("倍率(中央値の比) ×9.0 / ×78.8", round(m["lv1"] / m["lv0"], 1) == 9.0 and round(m["lv2"] / m["lv1"], 1) == 78.8)
ok("研究♡2の上位10% = 7,796,250", d["dist"]["lv2"]["p90"] == 7796250)
ok("(参考)しきい値一定(KEN_CONST=3)に切り替えた場合の研究♡2の中央値は 60,000", m["const3_lv2"] == 60000)
s = json.load(open(os.path.join(ROOT, "ichishuu", "results_stage_lap1_20261010.json"), encoding="utf-8"))
ok("ステージ条件の測定は、設定(data/stage_wins_lap1.csv)と同じ条件で行われている", s["need"] == {str(i): G.wins_needed(i) for i in (1, 2, 3)} and s["runs"] > 1000)
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
