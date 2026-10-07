"""results_dan6/report.pkl → CSV と要約の表示。python3 dan6/report_dan6.py"""
import pickle, sys, os, csv, statistics, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import goro14 as G
OUT = os.path.join(ROOT, "results_dan6"); R = pickle.load(open(os.path.join(OUT, "report.pkl"), "rb"))
NAME = {"hint": "強CPU", "weak": "弱CPU"}; VN = ["現状(しきい値3)", "しきい値を一律+1(4)", "前置き→部位だけしきい値+1"]
fm = lambda x: G.fmt_points(x)
def w(name, head, rows):
    with open(os.path.join(OUT, name), "w", encoding="utf-8-sig", newline="") as f:
        c = csv.writer(f); c.writerow(head); c.writerows(rows)
rows = []
for cpu in R:
    r = R[cpu]
    for vn in VN:
        for lab in ("win", "rand"):
            x = r[(vn, lab)]; d = x["dist"]
            rows.append([NAME[cpu], vn, "アガリ手" if lab == "win" else "無作為の手", r["wins"] if lab == "win" else 2000, f"{x['floor']:.1f}", d["median"], f"{d['mean']:.0f}", d["p90"], d["p99"], d["max"], f"{x['links']:.2f}", f"{x['raw']:.2f}"])
w("goro_points.csv", ["CPU", "語呂度のしきい値", "対象", "手数", "500点止まり%", "中央値", "平均", "上位10%(p90)", "上位1%(p99)", "最大", "つながり本数(まとめ後)", "つながり本数(まとめ前)"], rows)
rows = []
for cpu in R:
    r = R[cpu]
    for vn in VN:
        x = r[(vn, "win")]
        for k, v in sorted(x["ku"].items()): rows.append([NAME[cpu], vn, "つながり本数", k, f"{100*v/r['wins']:.1f}"])
        for k, v in sorted(x["size"].items()): rows.append([NAME[cpu], vn, "最大のつながった語数(語1・句2・節3・文4・碑文5)", k, f"{100*v/r['wins']:.1f}"])
        for k, v in sorted(x["merges"].items()): rows.append([NAME[cpu], vn, "連鎖数", k, f"{100*v/r['wins']:.1f}"])
        for k, v in sorted(x["theme"].items()): rows.append([NAME[cpu], vn, "最良テーマの倍率", k, f"{100*v/r['wins']:.1f}"])
        for k, v in x["theme_name"].most_common(): rows.append([NAME[cpu], vn, "最良テーマの種類", k, f"{100*v/r['wins']:.1f}"])
w("goro_dist.csv", ["CPU", "語呂度のしきい値", "指標", "値", "アガリ手に占める%"], rows)
rows = []
for cpu in R:
    for vn in VN:
        for k, v in sorted(R[cpu][(vn, "slotpair")].items()): rows.append([NAME[cpu], vn, G.SLOT_NAMES[k[0]], G.SLOT_NAMES[k[1]], f"{v:.1f}"])
w("goro_slotpair.csv", ["CPU", "語呂度のしきい値", "スロットA", "スロットB", "つながる%(アガリ手の語5つの組)"], rows)
rows = []
for cpu in R:
    for r_ in sorted(R[cpu]["yaku_rate"].items(), key=lambda kv: -kv[1]): rows.append([NAME[cpu], r_[0], f"{r_[1]:.3f}"])
w("yaku_rates.csv", ["CPU", "役", "アガリ手での出現率%"], rows)
rows = []
for cpu in R:
    for k, v in R[cpu]["merge_rate"].items(): rows.append([NAME[cpu], k, f"{v:.3f}"])
w("merge_rates.csv", ["CPU", "名前つき合体", "アガリ手での成立率%"], rows)
rows = []
for cpu in R:
    for k, nmk, nwd, hh, sh in R[cpu]["slots"]: rows.append([NAME[cpu], k, nmk, nwd, f"{hh:.1f}", f"{sh:.1f}"])
w("slots.csv", ["CPU", "slot_no", "slot", "辞書の語数", "その語がアガリ手に入る%", "アガリ手の語に占める%"], rows)
rows = []
for cpu in R:
    st = R[cpu]["stage"]
    for s_, (ok, n) in sorted(st["per"].items()): rows.append([NAME[cpu], s_, G.ken_stage(s_), min(s_, 8), n, f"{100*ok/n:.1f}"])
w("stage_pass.csv", ["CPU", "ステージ", "研究♡の段階", "条件", "挑戦数(ライフ消費を含む)", "1挑戦(3ゲーム)で達成%"], rows)
rows = []
for cpu in R:
    for (th, c), v in sorted(R[cpu]["cond_clear"].items(), reverse=True): rows.append([NAME[cpu], {4: "第一(4)", 3: "第二(3)", 2: "第三(2)"}[th], c, f"{v:.1f}"])
w("cond_clear.csv", ["CPU", "研究♡の段階(しきい値)", "条件", "3ゲーム以内に満たす確率%"], rows)
# ---- 表示 ----
for cpu in R:
    r = R[cpu]; print(f"\n=== {NAME[cpu]}: {r['n']}ゲーム アガリ {r['win_rate']:.1f}% テンパイ流局 {r['tenpai']:.1f}% ノーテン {r['noten']:.1f}% ===")
    x = r[(VN[0], "win")]
    print("つながり本数:", {k: f"{100*v/r['wins']:.1f}%" for k, v in sorted(x['ku'].items())})
    print("最大つながり語数:", {G.STAGE_NAMES[k]: f"{100*v/r['wins']:.1f}%" for k, v in sorted(x['size'].items())})
    print("連鎖数:", {k: f"{100*v/r['wins']:.1f}%" for k, v in sorted(x['merges'].items())})
    print("テーマ倍率:", {k: f"{100*v/r['wins']:.1f}%" for k, v in sorted(x['theme'].items())})
    print("テーマ種類 上位:", [(k, f"{100*v/r['wins']:.1f}%") for k, v in x['theme_name'].most_common(8)])
    print("語の組の接続率: アガリ手", {vn: round(r[(vn, 'pair')], 1) for vn in VN}, "無作為", {vn: round(r[(vn, 'pair_rand')], 1) for vn in VN})
    for vn in VN:
        for lab in ("win", "rand"):
            y = r[(vn, lab)]; d = y["dist"]
            print(f"  {vn:<14}{'アガリ手' if lab=='win' else '無作為  '} 500点止まり{y['floor']:.1f}% 中央値{fm(d['median'])} 平均{fm(d['mean'])} 上位10%{fm(d['p90'])} 上位1%{fm(d['p99'])} 最大{fm(d['max'])}")
    st = r["stage"]; rc = collections.Counter(st["reached"]); n = len(st["reached"])
    print(f"段階クリア: 平均到達ステージ {statistics.mean(st['reached']):.2f} 中央値 {statistics.median(st['reached'])} p10 {sorted(st['reached'])[n//10]} p90 {sorted(st['reached'])[int(n*.9)]} / ライフ減少 平均{statistics.mean(st['lives_lost']):.2f}(ゲームオーバーでは3) / 総ツモ 平均{statistics.mean(st['tsumo']):.0f} 中央値{statistics.median(st['tsumo'])}")
    print("  ステージ別 1挑戦(3ゲーム)達成%:", {s_: f"{100*ok/nn:.0f}" for s_, (ok, nn) in sorted(st['per'].items())[:10]})
    print("  条件別(3ゲーム以内) 第一/第二/第三:", {c: tuple(round(r['cond_clear'][(th, c)]) for th in (4, 3, 2)) for c in range(1, 9)})
    print(f"  焦らしプレイ(3連続テンパイ): 1挑戦で1回以上 {st['tenpai_run_pct']:.1f}% / 1ゲームあたり {100*st['seq3_per_game']:.2f}%")
    yr = r["yaku_rate"]; z = [k for k, v in yr.items() if v == 0]; l01 = [k for k, v in yr.items() if 0 < v < 0.1]; l1 = [k for k, v in yr.items() if v < 1]
    print(f"役の出現率: 87役中 0% {len(z)}役 / 0.1%未満(0%を除く) {len(l01)}役 / 1%未満(0%含む) {len(l1)}役")
    print("  0%:", z); print("  0%超〜0.1%未満:", [(k, round(yr[k], 3)) for k in l01])
    print("  名前つき合体: 成立率", {k: round(v, 2) for k, v in sorted(r['merge_rate'].items(), key=lambda kv: -kv[1])}, "いずれか", round(r["merge_any"], 1), "%")
    print(f"後ろの部位語: アガリ手の語に占める割合 {r['back_word_share']:.1f}% / 手に1語以上 {r['back_hand']:.1f}%")
    print("スロット別(辞書の語数/手に入る%/語の占有%):", [(nmk, nwd, round(hh), round(sh, 1)) for k, nmk, nwd, hh, sh in r["slots"]])
