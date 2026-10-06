"""試作HTML(prototype/hiragana_tap_prototype.html)を、dan5 の辞書・役・枚数に更新し、依頼 C の変更を入れる(何度実行しても同じ結果)。
  1. DATA を、dan5/ のCSVから作り直す(語342・役177・合体36・山の枚数。スロットは新しい7つ)
  2. okTile の ちゅ→つ/っ の代用を削除(つ=っ の互換は残す)
  3. 完成した面子の牌を、スロット別のパステル色にする(未完成の牌は白)
  4. 14牌を 21×30px・隙間なしで 320px 幅に収める
  python3 dan5/make_prototype.py [--modx 0.1] [--x2 13]
"""
import argparse, csv, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("--modx", type=float, default=0.1); ap.add_argument("--x2", type=int, default=13)
a = ap.parse_args()
sys.path.insert(0, ROOT)
from sim14 import tile_copies
rd = lambda n: list(csv.DictReader(open(os.path.join(HERE, n), encoding="utf-8-sig")))
W, H, Y, M = rd("words.csv"), rd("heads.csv"), rd("yaku.csv"), rd("yaku_merge.csv")
SL = ["前置き", "感情・誘い", "部位", "行為", "音", "反応", "喘ぎ声"]
data = {
    "W": [[w["word"], w["tiles"]] for w in W],
    "H": [[h["head"], h["tiles"]] for h in H],
    "C": dict(sorted(tile_copies(HERE, "new", a.modx, a.x2).items(), key=lambda kv: kv[0])),
    "A": [[w["type"], w["modifier"], w["modifiers"] if w["type"] != "単独" else "", w["position"], w["stem"], w["part"], w["tag"], int(w["slot_no"])] for w in W],
    "HA": [[h["type"], h["flavor"], h["stem"]] for h in H],
    "Y": [[y["name"], y["group"], int(y["tier"] or 0), y["condition_type"], y["params"], int(y["han_provisional"])] for y in Y],
    "M": [[m["name"], m["source_yaku"].split("|"), int(m["han_provisional"])] for m in M],
    "SL": SL,
}
# 山の牌の順(プロトタイプの C は、牌の字→枚数。ぉ゛・×2 を含む)
p = os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
s = open(p, encoding="utf-8").read()
i = s.index("const DATA=") + len("const DATA="); _, end = json.JSONDecoder().raw_decode(s[i:])
s = s[:i] + json.dumps(data, ensure_ascii=False) + s[i + end:]
# 2. ちゅ→つ/っ の代用を削除(決定3)
old = 'function okTile(a,r){ return a===r || (isTsu(r)&&(isTsu(a)||a==="ちゅ")) || (r==="お"&&a==="ぉ゛"); }'
new = 'function okTile(a,r){ return a===r || (isTsu(r)&&isTsu(a)) || (r==="お"&&a==="ぉ゛"); }   // つ=っ は互換。ちゅ→つ の代用は、廃止(dan5 決定3)'
if old in s: s = s.replace(old, new)
assert new in s, "okTile が見つからない"
# 3. スロット別の色(完成した面子の牌)。未完成の牌は白
COL = ["#E6E1EA", "#FFB8D4", "#FFD3C2", "#F0A0DC", "#BFD4FF", "#CDB0F5", "#FFF0A6"]
css_old = re.search(r"/\* dan5:slot-colors \*/.*?/\* /dan5 \*/\n", s, re.S)
css = "/* dan5:slot-colors */\n" + "".join(f".tile.s{k}{{background:{c};color:#1d1b17}}\n" for k, c in enumerate(COL)) + \
  "#hand{--tw:21px;--th:30px;gap:0}\n.tile{border-radius:3px;border-width:1px;box-shadow:none}\n.tile.tsumo{margin-left:6px}\n.grp{margin:0;gap:0}\n" \
  "@media (max-width:420px){main{padding:6px 4px 30px}.panel{padding:6px 3px 8px}#handwrap{padding:0}}\n/* /dan5 */\n"
if css_old: s = s.replace(css_old.group(0), css)
else: s = s.replace("</style>", css + "</style>", 1)
# tileHTML・render: 面子のグループに、スロットの色を付ける
old_t = 'function tileHTML(t){\n  const two=t.label.length>1?" two":"";'
new_t = 'function tileHTML(t,sc){\n  const two=t.label.length>1?" two":"";'
if old_t in s: s = s.replace(old_t, new_t)
old_b = '`<button class="tile${two}${s}${ts}${cp}" data-id="${t.id}">${t.label}</button>`'
new_b = '`<button class="tile${two}${s}${ts}${cp}${sc||""}" data-id="${t.id}">${t.label}</button>`'
if old_b in s: s = s.replace(old_b, new_b)
old_r = '${it.tiles.map(tileHTML).join("")}</div>`;\n  }).join("");'
new_r = '${it.tiles.map(t=>tileHTML(t,(it.kind==="meld"&&WI.has(it.name))?" s"+WA[WI.get(it.name)].slot:"")).join("")}</div>`;\n  }).join("");'
if old_r in s: s = s.replace(old_r, new_r)
assert new_r in s and new_b in s and new_t in s, "tileHTML/render の差し替えに失敗"
# 5. 搭子のラベル重複・リストの不一致: つ=っ・ぉ゛=お は同じ牌なので、搭子の候補(牌の組)と、待ち牌の表示を、同じものとして1つにまとめる
#    (以前: エロ+お と エロ+ぉ゛ が別々の搭子として並び、待ち牌にも「つ」と「っ」が別々に出た)
if "const nz=" not in s:
    s = s.replace("function findDazi(", 'const nz=x=>x==="っ"?"つ":(x==="ぉ゛"?"お":x);   // つ=っ・ぉ゛=お は、同じ牌として扱う\nfunction findDazi(', 1)
old_w = "waits.add(w.tiles[k]);"
if old_w in s: s = s.replace(old_w, "waits.add(nz(w.tiles[k]));")
old_k = 'const labs=[L[a].label,L[b].label],key=labs.slice().sort().join("|");'
if old_k in s: s = s.replace(old_k, 'const labs=[L[a].label,L[b].label],key=labs.map(nz).sort().join("|");')
assert "waits.add(nz(w.tiles[k]));" in s and 'key=labs.map(nz).sort().join("|");' in s, "搭子の修正が当たらなかった"
# 先頭の説明文(語数・山の枚数)を、新しい値に
s = re.sub(r"v1\.3m の語277・雀頭27・新しい牌の枚数\(山294枚\)", f"dan5 の語{len(W)}・雀頭{len(H)}・新しい牌の枚数(山{sum(data['C'].values())}枚)", s)
open(p, "w", encoding="utf-8").write(s)
print("試作HTMLを更新: 語", len(W), "役", len(Y), "合体", len(M), "山", sum(data["C"].values()), "枚")
