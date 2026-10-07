"""results_dan6/pool.pkl・live.pkl → CSV と要約の表示(summary.txt)。python3 dan6/report_dan6.py"""
import pickle, sys, os, csv, statistics, collections, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import goro14 as G
OUT = os.path.join(ROOT, "results_dan6")
POOL = pickle.load(open(os.path.join(OUT, "pool.pkl"), "rb"))
LIVE = pickle.load(open(os.path.join(OUT, "live.pkl"), "rb")) if os.path.exists(os.path.join(OUT, "live.pkl")) else {}
NAME = {"strong": "強CPU", "weak": "弱CPU", "aim": "点を狙うCPU"}
LVN = G.LV_NAMES
fm = G.fmt_points
buf = io.StringIO()
def P(*a):
    print(*a); print(*a, file=buf)
def w(name, head, rows):
    with open(os.path.join(OUT, name), "w", encoding="utf-8-sig", newline="") as f:
        c = csv.writer(f); c.writerow(head); c.writerows(rows)
def dist(xs):
    xs = sorted(xs); n = len(xs)
    return dict(n=n, median=xs[n // 2], mean=sum(xs) / n, p90=xs[int(n * .9)], p99=xs[int(n * .99)], max=xs[-1])
def line(d): return f"中央値{fm(d['median'])} 平均{fm(d['mean'])} 上位10%{fm(d['p90'])} 上位1%{fm(d['p99'])} 最大{fm(d['max'])}"

# ===== 1. 研究♡0/1/2ごと: 語の組の接続率・500点止まり・点の分布 =====
rows = []
P("=== 研究♡0/1/2ごと(見送りなしの強・弱CPU=各2,000ゲームのアガリ手、点を狙うCPU=段階クリアで遊んだゲーム、無作為の手) ===")
src = {}
for k in ("strong", "weak"):
    src[k] = {lv: [dict(points=b["points"], raw=b["raw_links"], yin=b["yin"]) for b in POOL[k]["lv"][lv]] for lv in (0, 1, 2)}
src["rand"] = {lv: [dict(points=b["points"], raw=b["raw_links"], yin=0) for b in POOL["rand"][lv]] for lv in (0, 1, 2)}
if "aim" in LIVE:
    src["aim"] = {lv: [dict(points=g["points"], raw=g["raw_links"], yin=g["yin"]) for c in LIVE["aim"] for g in c["games"] if g["result"] == "win" and g["lv"] == lv] for lv in (0, 1, 2)}
for k in ("strong", "weak", "aim", "rand"):
    if k not in src: continue
    for lv in (0, 1, 2):
        xs = src[k][lv]
        if not xs: continue
        pts = [x["points"] for x in xs]; d = dist(pts); fl = 100 * sum(p == G.FLOOR for p in pts) / len(pts); pr = 100 * sum(x["raw"] for x in xs) / (10 * len(xs))
        rows.append([NAME.get(k, "無作為の手"), lv, LVN[lv], G.KEN[lv], len(xs), f"{pr:.1f}", f"{fl:.1f}", d["median"], f"{d['mean']:.0f}", d["p90"], d["p99"], d["max"]])
        P(f"{NAME.get(k,'無作為の手'):<8} 研究♡{lv}「{LVN[lv]}」(しきい値{G.KEN[lv]}) n={len(xs)}: 語の組の接続率{pr:.1f}% 500点止まり{fl:.1f}% {line(d)}")
w("goro_by_level.csv", ["CPU", "研究♡", "呼び名", "しきい値", "手数", "語の組の接続率%", "500点止まり%", "中央値", "平均", "上位10%", "上位1%", "最大"], rows)

# ===== 2. 名前つき役(淫) =====
P("\n=== 名前つき役(淫): 研究♡1(しきい値3)でのアガリ手 ===")
rows = []
for k in ("strong", "weak"):
    bs = POOL[k]["lv"][1]; n = len(bs)
    w_y = [b for b in bs if b["yin"] > 0]; wo = [b for b in bs if b["yin"] == 0]
    gain = statistics.mean(b["yin"] for b in w_y) if w_y else 0
    share = 100 * (1 - sum(b["points_noyaku"] for b in bs) / sum(b["points"] for b in bs))
    ratio = statistics.mean(b["points"] / b["points_noyaku"] for b in bs)
    mw = statistics.median(b["points"] for b in w_y) if w_y else 0; mo = statistics.median(b["points"] for b in wo) if wo else 0
    mn = sum(1 for b in bs if b["yaku_merges"]) / n * 100
    P(f"{NAME[k]}: 名前つき役が成立した手 {100*len(w_y)/n:.1f}%、成立した手の句ボーナス増加(=淫)の平均 +{gain:.2f} / 合計の点のうち名前つき役が占める割合 {share:.1f}%(外した場合との点の比: 平均 ×{ratio:.2f}) / 付いた手の点の中央値 {fm(mw)}・付かない手 {fm(mo)} / 名前つき合体 {mn:.1f}%")
    rows.append([NAME[k], n, f"{100*len(w_y)/n:.1f}", f"{gain:.2f}", f"{share:.1f}", f"{ratio:.2f}", mw, mo, f"{mn:.1f}"])
w("yaku_in.csv", ["CPU", "アガリ手", "名前つき役が成立した手%", "成立した手の淫の平均", "点に占める名前つき役%", "点の比(平均)", "付いた手の点の中央値", "付かない手の点の中央値", "名前つき合体%"], rows)

# ===== 3. 段階クリア(ステージ1〜8)・見送りなし/あり =====
P("\n=== 段階クリア(各 %d 挑戦。実際に遊んだ結果。ライフ3・3ゲーム/ステージ) ===" % (len(LIVE.get("strong", []))))
rows = []; srow = []
for k in ("strong", "weak", "aim"):
    if k not in LIVE: continue
    C = LIVE[k]; n = len(C)
    att = collections.defaultdict(lambda: [0, 0]); reach = collections.Counter(); clr = collections.Counter()
    for c in C:
        seen = set()
        for s_, ok in c["attempts"]:
            att[s_][1] += 1; att[s_][0] += ok; seen.add(s_)
            if ok: clr[s_] += 1
        for s_ in seen: reach[s_] += 1
    rc = [c["reached"] for c in C]; lost = [sum(1 for s_, ok in c["attempts"] if not ok) for c in C]
    P(f"{NAME[k]}: 平均到達ステージ {statistics.mean(rc):.2f}(中央値 {statistics.median(rc)} / p10 {sorted(rc)[n//10]} / p90 {sorted(rc)[int(n*.9)]}) 総ツモ 平均{statistics.mean(c['tsumo'] for c in C):.0f} / ライフ減少は全挑戦でゲームオーバーまで(失敗した挑戦=ライフ3消費)")
    P("   ステージ別(突破率=そのステージに着いた挑戦のうち、いつかクリアした割合 / 1挑戦(3ゲーム)達成率=挑戦の1回ごと): " +
      " ".join(f"{s_}:{100*clr[s_]/reach[s_]:.0f}%/{100*att[s_][0]/att[s_][1]:.0f}%" for s_ in range(1, 9) if reach[s_]))
    for s_ in range(1, 9):
        if reach[s_]: rows.append([NAME[k], s_, lvl := G.ken_stage(s_), min(s_, 8), reach[s_], f"{100*clr[s_]/reach[s_]:.1f}", att[s_][1], f"{100*att[s_][0]/att[s_][1]:.1f}"])
    ach = 100 * sum(c["ach"] for c in C) / n; g_all = sum(len(c["games"]) for c in C)
    P(f"   焦らしプレイ(3連続テンパイ): 1挑戦で1回以上 {ach:.1f}% / 1ゲームあたり {100*sum(c['seq3'] for c in C)/g_all:.2f}%")
w("stage_pass.csv", ["CPU", "ステージ", "研究♡", "条件", "着いた挑戦数", "突破率%", "挑戦(3ゲーム)の回数", "1挑戦の達成率%"], rows)


# ===== 3b. ステージ条件1〜8 × 研究♡0/1/2 の突破率(条件を研究♡を揃えて1つずつ。見送りなし。分母=1挑戦=3ゲーム。各 20,000 挑戦を、2,000ゲームの記録から引き直して推定) =====
import random as _r
from sim_dan6 import sat
P("\n=== 条件1〜8 × 研究♡0/1/2 の突破率(1回の挑戦=3ゲーム以内に条件を満たす確率%。見送りなし。20,000挑戦ずつ) ===")
rows = []
for k in ("strong", "weak"):
    games = POOL[k]["games"]; wins = iter(range(10 ** 9)); rec = {lv: [] for lv in (0, 1, 2)}
    wi = 0; seq = []
    for g in games:
        if g["result"] == "win": seq.append(("win", wi)); wi += 1
        else: seq.append((g["result"], None))
    rng = _r.Random(3)
    tab = {}
    for lv in (0, 1, 2):
        ms = POOL[k]["lv"][lv]
        for c in range(1, 9):
            ok_ = 0; N = 20000
            for _ in range(N):
                used = 0; hit = False
                while used < 3 and not hit:
                    res, i = seq[rng.randrange(len(seq))]
                    if res == "tenpai": continue
                    used += 1
                    if res == "win" and sat(ms[i], c): hit = True
                ok_ += hit
            tab[(c, lv)] = 100 * ok_ / N
            rows.append([NAME[k], c, lv, LVN[lv], f"{tab[(c, lv)]:.1f}"])
    P(f"{NAME[k]}: 条件(行)×研究♡0/1/2(列)")
    for c in range(1, 9): P(f"   条件{c}「{ {1:'句',2:'節',3:'節でテーマ語3',4:'文',5:'複合テーマ成立',6:'文でテーマ語4',7:'碑文',8:'碑文でテーマ語5'}[c] }」: " + " / ".join(f"{tab[(c, lv)]:.0f}%" for lv in (0, 1, 2)))
w("cond_by_level.csv", ["CPU", "条件", "研究♡", "呼び名", "3ゲーム以内に満たす確率%"], rows)
# ===== 3c. 見送りなし・点を狙う・条件を狙い直す の比較(段階クリアを実際に遊んだ結果) =====
P("\n=== 3つのCPUの比較(段階クリア。各1,000挑戦): 突破率(そのステージに着いた挑戦のうち、いつかクリアした割合) と 平均到達ステージ ===")
cmp_rows = []
for k, nm in (("strong", "見送りなし(強CPU)"), ("aim", "点を狙うCPU"), ("seek", "条件を狙い直すCPU")):
    if k not in LIVE: continue
    C = LIVE[k]; reach = collections.Counter(); clr = collections.Counter()
    for c in C:
        seen = set()
        for s_, ok in c["attempts"]:
            seen.add(s_); clr[s_] += ok
        for s_ in seen: reach[s_] += 1
    rc = [c["reached"] for c in C]
    P(f"{nm}: 平均到達ステージ {statistics.mean(rc):.2f} / 突破率 " + " ".join(f"{s_}:{100*clr[s_]/reach[s_]:.0f}%" for s_ in range(1, 9) if reach[s_]))
    cmp_rows.append([nm, f"{statistics.mean(rc):.2f}"] + [f"{100*clr[s_]/reach[s_]:.1f}" if reach[s_] else "" for s_ in range(1, 9)])
w("stage_compare.csv", ["CPU", "平均到達ステージ"] + [f"ステージ{i}突破率%" for i in range(1, 9)], cmp_rows)
if "seek" in LIVE:
    G_ = [g for c in LIVE["seek"] for g in c["games"]]; played = [g for g in G_ if g["result"] != "tenpai"]; sk = [g for g in played if g["skips"]]
    rew = [g for g in sk if g["result"] == "win"]; sat_after = [g for g in rew if g["sat"]]
    P(f"条件を狙い直すCPU: 見送りを使ったゲーム {100*len(sk)/len(played):.1f}% / 見送ったあとに再びアガれた {100*len(rew)/len(sk):.1f}% / 再アガリで条件を満たした {100*len(sat_after)/max(1,len(rew)):.1f}%(見送った全ゲームの {100*len(sat_after)/len(sk):.1f}%) / ノーテン扱い {100*sum(1 for g in sk if g['skipfail'])/len(sk):.1f}%")

# ===== 4. 見送り(点を狙うCPUのみ) =====
if "aim" in LIVE:
    P("\n=== 見送り(点を狙うCPU。見送り回数: 研究♡0=1 / 1=2 / 2=3回、1回の挑戦(3ゲーム)で共有) ===")
    G_ = [g for c in LIVE["aim"] for g in c["games"]]
    played = [g for g in G_ if g["result"] != "tenpai"]
    sk = [g for g in played if g["skips"]]
    rewin = [g for g in sk if g["result"] == "win"]; fail = [g for g in sk if g["skipfail"]]
    ev = [e for g in sk for e in g["skips"]]
    delta_all = [(g["points"] if g["result"] == "win" else 0) - g["skips"][0] for g in sk]
    delta_re = [g["points"] - g["skips"][0] for g in rewin]
    nsk = sum(len(g["skips"]) for g in G_)
    P(f"見送りを使ったゲーム {100*len(sk)/len(played):.1f}%(見送りの回数 {nsk}) / 見送ったあとに再びアガれた割合 {100*len(rewin)/len(sk):.1f}% / ノーテン扱い {100*len(fail)/len(sk):.1f}%(全ゲームの {100*len(fail)/len(played):.1f}%)")
    P(f"見送りでの点の増減(1回目に見送った手の点→最終): 全体の平均 {statistics.mean(delta_all):+.0f}点(ノーテン扱いは0点) / 再アガリできた場合の平均 {statistics.mean(delta_re):+.0f}点 / 見送った手の点の平均 {statistics.mean(g['skips'][0] for g in sk):.0f}・中央値 {statistics.median(g['skips'][0] for g in sk):.0f}")
    for lv in (0, 1, 2):
        s_l = [g for g in sk if g["lv"] == lv]; p_l = [g for g in played if g["lv"] == lv]
        if p_l: P(f"   研究♡{lv}: 見送り使用 {100*len(s_l)/len(p_l):.1f}% / 再アガリ {100*sum(1 for g in s_l if g['result']=='win')/max(1,len(s_l)):.1f}% / ノーテン扱い {100*sum(1 for g in s_l if g['skipfail'])/max(1,len(s_l)):.1f}%")
    w("skip_stats.csv", ["指標", "値"], [["見送りを使ったゲーム%", f"{100*len(sk)/len(played):.1f}"], ["見送りの回数", nsk], ["再アガリ率%", f"{100*len(rewin)/len(sk):.1f}"], ["ノーテン扱い%(見送ったゲーム中)", f"{100*len(fail)/len(sk):.1f}"],
                                   ["点の増減の平均(全体)", f"{statistics.mean(delta_all):.0f}"], ["点の増減の平均(再アガリ)", f"{statistics.mean(delta_re):.0f}"]])

# ===== 5. 役の出現・名前つき合体・後ろの部位語・スロット別(見送りなしの強・弱CPU。分母=アガリ手) =====
import sim14
S = sim14.Scorer(os.path.join(ROOT, "dan6"))
names = sorted({y["name"] for y in S.Y}); rowsy, rowsm, rows_s = [], [], []
P("\n=== 役・語の統計(見送りなし。分母=アガリ手) ===")
for k in ("strong", "weak"):
    wins = [g for g in POOL[k]["games"] if g["result"] == "win"]; nw = len(wins)
    yc = collections.Counter(y for g in wins for y in g["yaku"]); mc = collections.Counter(m for g in wins for m in g["merges"])
    yr = {n: 100 * yc.get(n, 0) / nw for n in names}
    z = [n for n, v in yr.items() if v == 0]; l01 = [n for n, v in yr.items() if 0 < v < 0.1]; l1 = [n for n, v in yr.items() if v < 1]
    P(f"{NAME[k]}: 87役中 出現率0% {len(z)}役 / 0.1%未満(0%除く) {len(l01)}役 / 1%未満(0%含む) {len(l1)}役。0%: {z}。0%超〜0.1%未満: {[(n, round(yr[n], 3)) for n in l01]}")
    mr = {m["name"]: 100 * mc.get(m["name"], 0) / nw for m in S.M}
    P(f"   名前つき合体の成立率: " + " ".join(f"{n}{v:.2f}%" for n, v in sorted(mr.items(), key=lambda kv: -kv[1])) + f" / いずれか {100*sum(1 for g in wins if g['merges'])/nw:.1f}%")
    wc = collections.Counter(i for g in wins for i in g["words"])
    back = sum(wc[i] for i, w_ in enumerate(S.W) if G.ROWS[w_["word"]]["part"] == "後ろ"); backh = sum(1 for g in wins if any(G.ROWS[S.W[i]["word"]]["part"] == "後ろ" for i in g["words"]))
    P(f"   後ろの部位語: アガリ手の語の {100*back/(4*nw):.1f}% / 手に1語以上 {100*backh/nw:.1f}%")
    for n in names: rowsy.append([NAME[k], n, f"{yr[n]:.3f}"])
    for n, v in mr.items(): rowsm.append([NAME[k], n, f"{v:.3f}"])
    for sl, nmk in enumerate(G.SLOT_NAMES):
        idx = {i for i, w_ in enumerate(S.W) if G.ROWS[w_["word"]]["slot_no"] == sl}
        rows_s.append([NAME[k], sl, nmk, len(idx), f"{100*sum(1 for g in wins if idx & set(g['words']))/nw:.1f}", f"{100*sum(wc[i] for i in idx)/(4*nw):.1f}"])
w("yaku_rates.csv", ["CPU", "役", "アガリ手での出現率%"], rowsy); w("merge_rates.csv", ["CPU", "名前つき合体", "アガリ手での成立率%"], rowsm)
w("slots.csv", ["CPU", "slot_no", "slot", "辞書の語数", "その語がアガリ手に入る%", "アガリ手の語に占める%"], rows_s)
P("   スロット別(強CPU: 辞書の語数/手に入る%/語の占有%): " + str([(r[2], r[3], round(float(r[4])), float(r[5])) for r in rows_s if r[0] == "強CPU"]))
# ===== 6. しきい値の変種(前回の依頼。名前つき役の淫は含めない)=====
P("\n=== しきい値の変種(アガリ手・無作為の手。淫なしの点) ===")
rows = []
for k in ("strong", "weak", "rand"):
    for vn, xs in POOL["variants"][k].items():
        pts = [x["points"] for x in xs]; d = dist(pts); fl = 100 * sum(p == G.FLOOR for p in pts) / len(pts)
        rows.append([NAME.get(k, "無作為の手"), vn, len(pts), f"{fl:.1f}", d["median"], f"{d['mean']:.0f}", d["p90"], d["p99"], d["max"]])
        if k != "weak": P(f"{NAME.get(k,'無作為の手'):<8}{vn:<16} 500点止まり{fl:.1f}% {line(d)}")
w("goro_variants.csv", ["CPU", "しきい値の変種", "手数", "500点止まり%", "中央値", "平均", "上位10%", "上位1%", "最大"], rows)
open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8").write(buf.getvalue())
