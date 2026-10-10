"""プレイの記録(試作の「記録を書き出す」で出る JSON)を読んで、時間がかかった場面と、判断が結果に効かなかった場面を要約する。20261010-1925 F
  python3 dan6/summarize_playlog.py hm-playlog.json [--top 5]
定義(仮。企画側が決めるまでの暫定):
  ・時間がかかった場面: 「ツモ → 次の捨て牌・組み」までの時間が、全体の中央値の2倍以上かつ上位 N 件。ゲーム全体の時間も出す。
  ・判断が結果に効かなかった場面: (a) 捨て牌がすべてツモ切りのゲーム(選んでいない) (b) 手を1つも組まずに和了したゲーム(自動で組んだ) (c) 見送りの直後の捨て牌が、そのまま流局になったゲーム(見送りの判断が、得にならなかった)。"""
import json, sys, statistics, argparse
ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--top", type=int, default=5); a = ap.parse_args()
log = json.load(open(a.path, encoding="utf-8")); games = log["games"]
print(f"ゲーム数 {len(games)}(結果: " + ", ".join(f"{k} {sum(1 for g in games if g['result'] and g['result']['kind']==k)}" for k in ("win", "tenpai", "nowin")) + f"、未完了 {sum(1 for g in games if not g['result'])})")
# 時間
think = []
for g in games:
    last = 0
    for e in g["events"]:
        if e["type"] == "draw": last = e["t"]
        elif e["type"] in ("discard", "group") and last is not None:
            think.append((e["t"] - last, g["no"], e["type"], e.get("tile") or e.get("text"))); last = e["t"]
med = statistics.median(t[0] for t in think) if think else 0
print(f"\n1手(ツモ→次の操作)の時間: 中央値 {med/1000:.1f}秒、最大 {max((t[0] for t in think), default=0)/1000:.1f}秒")
print(f"時間がかかった場面(中央値の2倍以上、上位{a.top}件):")
for t, no, ty, what in sorted(think, reverse=True)[:a.top]:
    if t >= 2 * med: print(f"  ゲーム{no}: {t/1000:.1f}秒({ty} {what})")
durs = [(g["result"]["ms"], g["no"], g["result"]["kind"]) for g in games if g["result"]]
if durs:
    print(f"ゲーム全体の時間: 中央値 {statistics.median(d[0] for d in durs)/1000:.1f}秒、最長 ゲーム{max(durs)[1]}({max(durs)[0]/1000:.1f}秒・{max(durs)[2]})")
# 判断が効かなかった場面
print("\n判断が結果に効かなかった場面(仮の定義):")
na = nb = nc = 0
for g in games:
    dis = [e for e in g["events"] if e["type"] == "discard"]; grp = [e for e in g["events"] if e["type"] == "group"]
    r = g["result"]
    if dis and all(e.get("tsumogiri") for e in dis): na += 1; print(f"  ゲーム{g['no']}: (a) 捨て牌がすべてツモ切り({len(dis)}回)")
    if r and r["kind"] == "win" and not grp: nb += 1; print(f"  ゲーム{g['no']}: (b) 手を組まずに和了(自動で組んだ)")
    if r and r["kind"] in ("nowin", "tenpai") and any(e.get("afterSkip") for e in dis): nc += 1; print(f"  ゲーム{g['no']}: (c) 見送ったが、{r['kind']} で終わった")
print(f"件数: (a) {na} / (b) {nb} / (c) {nc}")
wins = [g["result"] for g in games if g["result"] and g["result"]["kind"] == "win"]
if wins:
    print(f"\n和了 {len(wins)}回: 解読点の合計 {sum(w['points'] for w in wins):,.0f}、モザイク前の本当の解読点の合計 {sum(w['real'] for w in wins):,.0f}")
