"""試作HTML(prototype/hiragana_tap_prototype.html)を、dan6 の辞書・役・枚数に更新し、依頼 C の変更を入れる(何度実行しても同じ結果)。
  1. DATA を、dan6/ のCSVから作り直す(語342・役177・合体36・山の枚数。スロットは新しい7つ)
  2. okTile の ちゅ→つ/っ の代用を削除(つ=っ の互換は残す)
  3. 完成した面子の牌を、スロット別のパステル色にする(未完成の牌は白)
  4. 14牌を 21×30px・隙間なしで 320px 幅に収める
  python3 dan6/make_prototype.py [--modx 0.1] [--x2 13]
"""
import argparse, csv, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(); ap.add_argument("--modx", type=float, default=0.05); ap.add_argument("--x2", type=int, default=13)
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
    "GR": {r["word"]: [int(r["slot_no"]), r["slot"], r["sub"], r["読み"], r["部位"], r["トーン"], r["命令の係り先"], r["種別"]]
           for r in csv.DictReader(open(os.path.join(ROOT, "data", "word_tags_v1.csv"), encoding="utf-8-sig"))},
    "KZ": sorted(r["name"] for r in rd("yaku_class.csv") if r["class"].startswith("飾り")),
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
s = re.sub(r"v1\.3m の語277・雀頭27・新しい牌の枚数\(山294枚\)", f"dan6 の語{len(W)}・雀頭{len(H)}・新しい牌の枚数(山{sum(data['C'].values())}枚)", s)
# ---- dan6 の追加 ----
def sub1(old, new):
    global s
    if "/* dan6:b */" in s:                                       # proto_patch2 まで適用済み
        return
    if new in s and (old not in s or old in new):                 # 適用済み(何度実行しても同じ結果)
        return
    if old not in s and "/* dan6:goro */" in s:                    # proto_patch2 で書き換え済みの箇所
        return
    assert old in s, "dan6 パッチが当たらない: " + old[:50]
    s = s.replace(old, new, 1)
# 6. はじめての語ボーナスを全部外す(計算・表示・演出カード・保存データ。語の図鑑用の seenWords は、収集の記録なので残す)
sub1("const total=own.total+ura+newWords.length;", "const total=own.total+ura;")
sub1("const seen=seenWords();const newWords=melds.map(g=>g.name).filter(n=>!seen.has(n));\n  melds.forEach(g=>seen.add(g.name));saveSeen(seen);",
     "const seen=seenWords();melds.forEach(g=>seen.add(g.name));saveSeen(seen);   // 図鑑用の記録のみ(ボーナスなし)")
sub1("count:parts.length,ura,newWords,total,", "count:parts.length,ura,total,")
sub1("  if(d.newWords.length)s+=`<div class=\"sc\">はじめての語ボーナス <span class=\"han\">+${d.newWords.length}翻</span> <small>(${d.newWords.join(\"・\")})</small></div>`;\n", "")
sub1("e.innerHTML=words[i]+(d.newWords.includes(d.own.names[i])?'<span class=\"nw\">NEW</span>':\"\");", "e.innerHTML=words[i];")
k0 = "  if(d.newWords.length){\n    const e=document.createElement(\"span\");e.className=\"ycard r2 pop\""
if k0 in s:
    i0 = s.index(k0)
    i1 = s.index("  }\n", i0) + 4
    s = s[:i0] + s[i1:]
assert "newWords" not in s and "はじめての語" not in s, "ボーナスの記述が残っている"
# 7. 大きな点の表示(万・億・兆・京)とハイスコア
FMT = ("function fmtPts(p){p=Math.floor(p);const U=[[1e16,'京'],[1e12,'兆'],[1e8,'億'],[1e4,'万']];for(const [u,n] of U)if(p>=u){const v=p/u;let t=v<100?(Math.floor(v*10)/10).toFixed(1):String(Math.floor(v));if(t.endsWith('.0'))t=t.slice(0,-2);return t+n;}return String(p);}\n"
       "const HI_KEY=\"hm-proto-hiscore\";\n"
       "function loadHi(){try{return Number(localStorage.getItem(HI_KEY)||0);}catch(e){return 0;}}\n"
       "function updateHi(p){const old=loadHi();if(p>old){try{localStorage.setItem(HI_KEY,String(p));}catch(e){}return {hi:p,isNew:old>0||p>0};}return {hi:old,isNew:false};}\n")
if "function fmtPts(" not in s:
    sub1("function pts(h){", FMT + "function pts(h){")
sub1("const entry={id:Date.now()", "const hiR=updateHi(pts(total));const entry={id:Date.now()")
sub1("ura,total,near,", "ura,total,hi:hiR,near,")
sub1("<h2>アガリ! ${d.total}翻 / ${pts(d.total)}点</h2>", "<h2>アガリ! ${d.total}翻 / ${fmtPts(pts(d.total))}点</h2><div class=\"hint\">ハイスコア ${fmtPts(d.hi.hi)}点${d.hi.isNew?\" ★更新!\":\"\"}</div>")
sub1("pts(T).toLocaleString()+'点", "fmtPts(pts(T))+'点")
sub1("${e.pts.toLocaleString()}点", "${fmtPts(e.pts)}点")
sub1(".wcard{position:relative}.wcard .nw{position:absolute;top:-9px;right:-6px;background:#ff2d7a;color:#fff;font-size:.6rem;border-radius:6px;padding:0 4px}", ".wcard{position:relative}")
# 8. 役エンジンの追加分(yaku14.py と同じ条件。slot: 選択子、語幹・修飾牌を変数にした1本化、種類(×2)、雀頭の系統の集合)
sub1('tag:a[6]||"",slot:a[7]}));', 'tag:a[6]||"",slot:a[7],type:a[0]}));')
sub1('  else if(tok.startsWith("part:")){const m=tok.slice(5);WA.forEach((x,i)=>{if(x.part===m)a[i]=1;});}',
     '  else if(tok.startsWith("part:")){const m=tok.slice(5);WA.forEach((x,i)=>{if(x.part===m)a[i]=1;});}\n  else if(tok.startsWith("slot:")){const m=tok.slice(5);WA.forEach((x,i)=>{if(String(x.slot)===m)a[i]=1;});}')
sub1('"head_is","variant_count"]);', '"head_is","variant_count","count_same_stem_any","count_same_modifier_any","count_type","head_stem_any","head_flavor_set","count_same_part"]);')
NEWC = ('    case"count_same_stem_any":{const n=+kv.n,ps=new Set(kv.parts.split("|"));const st=[...new Set(WA.filter(x=>x.stem&&ps.has(x.part)).map(x=>x.stem))].sort();const arr=st.map(t=>selTok("stem:"+t));R=union(arr);f=ws=>arr.some(a=>cnt(a,ws)>=n);break;}\n'
        '    case"count_same_modifier_any":{const n=+kv.n;const arr=ALLMODS.map(m=>selTok("mod:"+m));R=union(arr);f=ws=>arr.some(a=>cnt(a,ws)>=n);break;}\n'
        '    case"count_type":{const a=new Uint8Array(NW);WA.forEach((x,i)=>{if(x.type===kv.type)a[i]=1;});const n=+kv.n;R=a;f=ws=>cnt(a,ws)>=n;break;}\n'
        '    case"head_stem_any":{const n=+kv.min;const m={};ALLSTEMS.forEach(t=>{m[t]=selTok("stem:"+t);});f=(ws,hd)=>hd>=0&&HA[hd].type==="略称"&&!!m[HA[hd].stem]&&cnt(m[HA[hd].stem],ws)>=n;break;}\n'
        '    case"head_flavor_set":{const a=inset(kv.set),n=+kv.min;R=a;f=(ws,hd)=>hd>=0&&HA[hd].type==="喘ぎ声"&&HA[hd].flavor===kv.flavor&&cnt(a,ws)>=n;break;}\n')
NEWC += '    case"count_same_part":{const n=+kv.n;const arr=PARTS.map(pt=>selTok("part:"+pt));R=union(arr);f=ws=>arr.some(a=>cnt(a,ws)>=n);break;}\n'
sub1('    default:throw new Error("未対応の条件: "+ct);', NEWC + '    default:throw new Error("未対応の条件: "+ct);')
sys.path.insert(0, HERE)
import proto_patch2
s = proto_patch2.apply(s)
open(p, "w", encoding="utf-8").write(s)
print("試作HTMLを更新: 語", len(W), "役", len(Y), "合体", len(M), "山", sum(data["C"].values()), "枚")
