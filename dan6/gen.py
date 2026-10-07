# ひらがな麻雀(仮) dan6: 新辞書v16(307語+前置き58語=365語)・役の再定義(87種)・名前つき合体17。語・役・牌の枚数のCSVの生成と検証。
#   (dan5/gen.py を拡張した版。dan5 の gen.py は、そのまま残してある)
#   python3 dan6/gen.py            → dan6/ に words.csv / heads.csv / yaku.csv / yaku_merge.csv / tile_usage.csv / tile_variants.csv /
#                                     tile_copies.csv / tile_copies_conditions.csv を出力する
# 入力:
#   ../data/words_by_slot_v16.csv  新辞書の本体(語・スロット)。牌は、語の読みから決める(下の tokenize)
#   ../data/modifier_triples_B.csv 前置き(修飾牌だけの面子)58語(案B)
#   ../v13m/                       旧辞書(v1.3m。語の属性・雀頭・役・合体の元)。既存の語の属性は、ここから引き継ぐ
#   ../dan5/yaku_v13n_spec.csv  v1.3n の役(177行)。ここから、yaku_final_v2.csv(87種)に絞る・変える
#   ../data/yaku_final_v2.csv・yaku_reclass_v1.csv・merge_final_v3.csv  役の最終一覧(87種)・区分・名前つき合体17
# 検査(失敗したら止まる): 牌の組み合わせ(つ=っ・ぉ゛=お を同一視)が同じ語の重複 / 役・合体が参照する語がない / 語の読みと牌の不一致
import csv, math, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D5 = os.path.join(ROOT, "dan5")
DATA = os.path.join(ROOT, "data")
V13M = os.path.join(ROOT, "v13m")
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))

def wcsv(name, header, rows):
    with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

X2 = "×2"                                                  # 新しい牌: 語幹2牌+×2 で、語幹を重ねた語(ちんちん など)
MODS = ["見せ", "デカ", "エロ", "ぬれ", "舐め", "媚び", "コキ", "穴", "♡"]
SPECIAL = ["ぉ゛", "しゃ", "ちゅ"]
TOKS = sorted(MODS + SPECIAL, key=len, reverse=True)
NORM = {"ぉ゛": "お", "っ": "つ"}                           # 重複検査・判定で、同じ牌として扱う(つ=っ、ぉ゛=お)。ちゅ→つ の代用は廃止(決定3)
nrm = lambda t: NORM.get(t, t)

def tokenize(s):
    out, i = [], 0
    while i < len(s):
        for t in TOKS:
            if s.startswith(t, i):
                out.append(t); i += len(t); break
        else:
            out.append(s[i]); i += 1
    return out

# 語幹(2牌の略称・別名)と、その部位。v1.3m の gen.py と同じ。新しい語幹: ちち(胸)・いき・ぱこ・おち・まけ
STEM_PART = {"ちん": "男性器", "まん": "女性器", "けつ": "後ろ", "ぱい": "胸", "くり": "女性器", "ちつ": "女性器", "まぞ": "SM", "さど": "SM",
             "まめ": "女性器", "ちく": "胸", "くち": "口", "すじ": "女性器", "ちち": "胸", "しり": "後ろ"}     # 「ち-ち」語幹を胸の部位に含める(依頼 B)
STEM_CANON = {"まめ": "くり"}
STEMS_X2 = set(STEM_PART) | {"べろ", "すき", "きく", "おな", "あな", "めす", "おす", "ぱか", "くぱ", "くぽ", "まま", "いき", "ぱこ", "おち", "まけ", "しり", "ぱち", "しつ", "しこ"}

old = {}
for r in rd(os.path.join(V13M, "words.csv")):
    for x in r["word"].split("・"):
        old[x] = r

# ---------------- 語 ----------------
words, problems = [], []
for r in rd(os.path.join(DATA, "words_by_slot_v16.csv")):
    name = r["word"]; reads = name.split("・"); toks = [tokenize(x) for x in reads]; first = toks[0]
    x2 = r["source"] == "×2" or (len(first) == 4 and first[:2] == first[2:])   # v16 は、しこしこ・しめしめ を「追加(面子)」としているが、構造は×2語(63語)
    if x2:
        for t in toks:
            if not (len(t) == 4 and t[:2] == t[2:]):
                problems.append(("×2語の読みが、語幹の繰り返しでない", name))
        tiles = first[:2] + [X2]
        for t in toks[1:]:
            if Counter(map(nrm, t[:2])) != Counter(map(nrm, first[:2])):
                problems.append(("読み違いの牌の組み合わせが違う", name))
    else:
        tiles = list(first)
        if len(tiles) != 3: problems.append(("3牌でない", name, tiles))
        for t in toks[1:]:
            if Counter(map(nrm, t)) != Counter(map(nrm, first)):
                problems.append(("読み違いの牌の組み合わせが違う", name))
    o = next((old[x] for x in reads if x in old), None)
    row = dict(word=name, tiles="|".join(tiles), slot_no=r["slot_no"], slot=r["slot"], sub=r["sub"], source=r["source"], note=r["note"])
    if o and not x2:
        if Counter(map(nrm, o["tiles"].split("|"))) != Counter(map(nrm, tiles)):
            problems.append(("旧辞書と牌が違う", name, o["tiles"], tiles))
        row.update({k: o[k] for k in ("type", "modifier", "modifiers", "position", "stem", "part", "tag", "flavor")})
        row["tiles"] = o["tiles"]                         # 既存の語は、旧辞書の牌の字(つ・っ)のまま
        row["note"] = (o["note"] + " / " if o["note"] and r["note"] else o["note"]) + r["note"] if (o["note"] or r["note"]) else ""
    else:
        row.update(modifier="", modifiers="", position="", stem="", part="", flavor="", tag=r["sub"])
        if x2:
            X = "".join(first[:2]); stem = STEM_CANON.get(X, X) if X in STEMS_X2 else ""
            row.update(type="×2", stem=stem, part=STEM_PART.get(X, ""))
        else:
            ms = [t for t in first if t in MODS]
            if len(ms) == 1 and first.count(ms[0]) == 1:
                m = ms[0]; rest = [t for t in first if t != m]
                if first[0] == m: pos = "語頭"
                elif first[-1] == m: pos = "語尾"
                else: pos = ""; problems.append(("修飾牌が語の途中", name))
                stem = "".join(rest)
                row.update(type=f"{m}型", modifier=m, modifiers=m, position=pos, stem=STEM_CANON.get(stem, stem), part=STEM_PART.get(stem, ""))
            else:
                row.update(type="単独")
                if name == "おちち": row["part"] = "胸"      # 単独語・ち2枚使用(胸)
                if name in ("おしり", "おけつ", "うしろ", "しっぽ"): row["part"] = "後ろ"   # 後ろの単独語(v16)
        if r["slot"] == "喘ぎ声" and not x2:
            row["flavor"] = "オホ声系" if any(nrm(t) == "お" for t in tiles) else "可愛い系"
        if x2 and r["slot"] == "喘ぎ声":
            row["flavor"] = "オホ声系" if any(nrm(t) == "お" for t in tiles) else "可愛い系"
    words.append(row)
for r in rd(os.path.join(DATA, "modifier_triples_B.csv")):
    ts = [r["tile1"], r["tile2"], r["tile3"]]
    words.append(dict(word=r["name"], tiles="|".join(ts), slot_no="0", slot="前置き", sub=r["type"], source="前置き(案B)", note="修飾牌3つの語",
                      type="修飾3型", modifier="", modifiers="|".join(ts), position="", stem="", part="", tag="修飾3", flavor=""))

# 牌の組み合わせが同じ語は、v16 のCSVで、すでに「A・B」の1語にまとめてある(おっおっ・ぉ゛っぉ゛っ、ぱんっ・ぱんつ など)。
# 牌の組み合わせが同じ語の重複検査(つ=っ・ぉ゛=お)。重複があれば失敗(決定2)
keys = {}
for w in words:
    k = tuple(sorted(nrm(t) for t in w["tiles"].split("|")))
    if k in keys: problems.append(("牌の組み合わせが同じ語の重複", keys[k], w["word"], "|".join(k)))
    keys[k] = w["word"]
names = [w["word"] for w in words]
dn = [n for n, c in Counter(names).items() if c > 1]
if dn: problems.append(("語名の重複", dn))
for i, w in enumerate(words, 1):
    w["id"] = f"W{i:03d}"; w["tile_count"] = len(w["tiles"].split("|"))
if problems:
    for p in problems: print("エラー:", *p)
    sys.exit(1)
WCOLS = ["id", "word", "type", "modifier", "modifiers", "position", "stem", "tiles", "tile_count", "part", "tag", "flavor", "note", "slot_no", "slot", "sub", "source"]
wcsv("words.csv", WCOLS, [[w[c] for c in WCOLS] for w in words])
widx = {x: i for i, w in enumerate(words) for x in [w["word"]] + w["word"].split("・")}   # 役の指定は「A・B」の全体で書く
print("語", len(words), Counter(w["source"] for w in words))

# ---------------- 雀頭・牌の変種 ----------------
heads = rd(os.path.join(V13M, "heads.csv"))
heads.append(dict(id=f"H{len(heads)+1:03d}", head="しり", tiles="し|り", type="略称", flavor="後ろ", stem="しり", note="語幹の略称(v16で追加)"))
wcsv("heads.csv", list(heads[0].keys()), [list(h.values()) for h in heads])
VAR = [["っ", "つ", 0, "互換", "replace", "っとつは、互換の文字(きつく=きっく)。どちらの牌でも、つ・っの語に使える"],
       ["ぉ゛", "お", 4, "オホ声", "replace", "おの代わりになる牌。持ってアガると『オホ声』の役が付く"]]      # ちゅ→つ(flex)は廃止(決定3)
wcsv("tile_variants.csv", ["tile", "base", "copies", "name", "mode", "note"], VAR)

# ---------------- 牌の枚数 ----------------
used, demand, occ = Counter(), Counter(), Counter()
for w in words:
    ts = w["tiles"].split("|")
    occ.update(ts)
    if w["type"] == "修飾3型": demand.update(ts)
    else: used.update(set(ts))
for h in heads: used.update(set(h["tiles"].split("|")))
def copies(modx, x2n):
    c = {}
    for t, u in used.items():
        if t == X2: continue
        c[t] = min(10, max(2, math.ceil(u / 2))) + (int(modx * demand[t] + 0.5) if t in MODS else 0)
    c["ぉ゛"] = 4; c[X2] = x2n
    return c
wcsv("tile_usage.csv", ["tile", "used_in_words", "total_occurrences_in_all_words", "triple_demand"],
     [[t, used[t], occ[t], demand[t]] for t in sorted(used, key=lambda t: (-used[t], t))] + [[X2, 0, occ[X2], 0]])
conds = [(0.05, 13), (0.1, 13), (0.0, 13)]
tot = []
for modx, n in conds:
    c = copies(modx, n); tot.append([modx, n, sum(c.values()), len(c)])
base = copies(0.05, 13)
wcsv("tile_copies.csv", ["tile", "used_in_words", "base_copies", "modifier_bonus", "copies"],
     [[t, used.get(t, 0), (base[t] - (int(0.05 * demand[t] + 0.5) if t in MODS else 0)) if t in used else base[t], int(0.05 * demand[t] + 0.5) if t in MODS else 0, base[t]]
      for t in sorted(base, key=lambda t: (-base[t], t))])
wcsv("tile_copies_conditions.csv", ["MODX", "x2_copies", "wall_tiles", "tile_types"], tot)
print("山(MODX,×2) =", [(m, n, t) for m, n, t, _ in tot])

# ---------------- 役(v1.3n) ----------------
def key(g, t, ct, p): return (g, int(t or 0), ct, p)
y13m = rd(os.path.join(V13M, "yaku.csv"))
spec = rd(os.path.join(D5, "yaku_v13n_spec.csv"))
byk = defaultdict(list)
for r in y13m: byk[key(r["group"], r["tier"], r["condition_type"], r["params"])].append(r)
yaku, renames, used_keys = [], {}, Counter()
for s in spec:
    k = key(s["group"], s["tier"], s["condition_type"], s["params"])
    cand = byk.get(k, [])
    j = used_keys[k]; used_keys[k] += 1
    if j < len(cand):
        r = dict(cand[j])
        if r["name"] != s["name"]: renames[r["name"]] = s["name"]
        r["name"] = s["name"]; r["han_provisional"] = s["han_provisional"]
    else:
        r = dict(name=s["name"], pattern="v1.3n追加", group=s["group"], tier=s["tier"], condition_type=s["condition_type"], params=s["params"],
                 han_provisional=s["han_provisional"], han_status="仮", description="v1.3n で追加(試作HTMLの役エンジンから取り込み)")
    yaku.append(r)
left = [r["name"] for k, v in byk.items() for r in v[used_keys[k]:]]
if left: print("警告: v1.3n にない旧役:", left)
print("役: v1.3m", len(y13m), "→ v1.3n", len(yaku), "行 / 改名", renames, "/ 新役", [r["name"] for r in yaku if r["pattern"] == "v1.3n追加"])

# 役の語集合の拡張(依頼 B): キス語・絶頂・結末(25語)・喘ぎ声(×2の喘ぎを含む)
sub_words = lambda sub: [w["word"] for w in words if w["sub"] == sub]
OLD_KISS = ["ちゅっちゅ", "べろちゅ", "きっす", "すき♡・きす♡", "穴すき・きす穴", "エロすき・エロきす", "ぬれすき・ぬれきす"]
OLD_ZET = ["いくっ", "あくめ", "しゃせい"]
OLD_MOAN = ["あんっ", "ああっ", "おおっ", "んおっ", "んんっ", "うおお", "あうう", "うんん"]
NEW_KISS = OLD_KISS + [x for x in sub_words("キス・吸い") if x not in OLD_KISS]
NEW_ZET = sub_words("絶頂・結末")
NEW_MOAN = sub_words("喘ぎ声")
ext_log = Counter()
def repl(tokens):
    for tag, old_l, new_l in (("KISS", OLD_KISS, NEW_KISS), ("ZETCHO", OLD_ZET, NEW_ZET), ("MOAN", OLD_MOAN, NEW_MOAN)):
        if set(old_l) <= set(tokens):
            i = min(tokens.index(x) for x in old_l); rest = [t for t in tokens if t not in old_l]
            tokens = rest[:i] + new_l + rest[i:]; ext_log[tag] += 1
    return tokens
for r in yaku:
    ct, p = r["condition_type"], r["params"]
    if ct == "count_in_set":
        kv = dict(x.split("=", 1) for x in p.split(";")); toks = repl(kv["set"].split("|")); kv["set"] = "|".join(toks)
        r["params"] = ";".join(f"{k}={v}" for k, v in kv.items())
    elif ct == "one_from_each":
        r["params"] = ";".join("|".join(repl(g.split("|"))) for g in p.split(";"))
    elif ct == "contains_all":
        pass
print("語集合の拡張(置き換えた箇所):", dict(ext_log), "/ キス語", len(NEW_KISS), "絶頂・結末", len(NEW_ZET), "喘ぎ声", len(NEW_MOAN))
# ---- 役の再定義(yaku_final_v2.csv 87種): 絞り込み・翻・1本化・新規。区分は yaku_reclass_v1.csv ----
fin = rd(os.path.join(DATA, "yaku_final_v2.csv")); rcl = {r["name"]: r for r in rd(os.path.join(DATA, "yaku_reclass_v1.csv"))}
KISSX = "すき♡・きす♡|穴すき・きす穴|エロすき・エロきす|ぬれすき・ぬれきす"; PLEASURE = "きく♡|穴きく|きつく・きっく|きくう"
OPEN = "ぱかあ|くぱあ|ぱかっ|くぱっ|ぱかん|くちゅっ|くぽっ|ぱか♡|くぱ♡・ぱく♡|くぽ♡"
BODY = "parts=男性器|女性器|胸|後ろ"
NEWY = {   # 名前 -> (pattern, group, tier, condition_type, params, 説明)。部位名・語幹名・修飾牌名を変数にした1本化の役は、変数式のまま
 "語幹好き": ("1本化(語幹)", "stemladder", 2, "count_same_stem_any", f"n=2;{BODY}", "同じ語幹(ちん・まん・けつ・しり等。部位のある語幹)の語が2語"),
 "語幹に夢中": ("1本化(語幹)", "stemladder", 3, "count_same_stem_any", f"n=3;{BODY}", "同じ語幹の語が3語以上"),
 "部位コンビ": ("1本化(部位)", "partladder", 2, "count_same_part", "n=2", "同じ部位(男性器・女性器・胸・後ろ)の語が2語以上"),
 "部位トリオ": ("1本化(部位)", "partladder", 3, "count_same_part", "n=3", "同じ部位の語が3語以上"),
 "部位カルテット": ("1本化(部位)", "partladder", 4, "count_same_part", "n=4", "同じ部位の語が4語以上"),
 "雀頭一筋": ("1本化(雀頭)", "headstem", 1, "head_stem_any", "min=1", "雀頭が略称で、同じ語幹の語が手に1語以上"),
 "雀頭ぞっこん": ("1本化(雀頭)", "headstem", 2, "head_stem_any", "min=2", "雀頭が略称で、同じ語幹の語が手に2語以上"),
 "修飾牌三昧": ("1本化(修飾牌)", "", 0, "count_same_modifier_any", "n=3", "同じ修飾牌を使う語が3語以上"),
 "繰り返し": ("×2型", "x2", 2, "count_type", "type=×2;n=2", "×2語が2語以上"),
 "連呼地獄": ("×2型", "x2", 3, "count_type", "type=×2;n=3", "×2語が3語以上"),
 "純愛": ("句(雀頭+語)", "", 0, "head_flavor_set", f"flavor=可愛い系;min=1;set={KISSX}", "雀頭が可愛い系の喘ぎで、手にラブ系の語(すき♡・きす♡/穴すき/エロすき/ぬれすき)が1語以上"),
 "理性崩壊": ("句(雀頭+語)", "", 0, "head_flavor_set", f"flavor=オホ声系;min=1;set={PLEASURE}", "雀頭がオホ声系の喘ぎで、手に快感系の語(きく♡・穴きく・きつく・きくう)が1語以上"),
 "ぱっくり": ("擬音型", "", 0, "one_from_each", f"slot:2;{OPEN}", "部位語(スロット2)1語+開き系の擬音1語の句"),
}
by_name = defaultdict(list)
for r in yaku: by_name[r["name"]].append(r)
final_rows, notfound = [], []
for f in fin:
    n = f["name"]
    if n in NEWY:
        pt, g, t, ct, p, d = NEWY[n]
        final_rows.append(dict(name=n, pattern=pt, group=g, tier=t, condition_type=ct, params=p, han_provisional=f["han"], han_status="仮", description=d))
    elif n in by_name:
        for r in by_name[n]:
            r = dict(r); r["han_provisional"] = f["han"]; final_rows.append(r)
    else: notfound.append(n)
if notfound: print("エラー: 役の定義が見つからない:", notfound); sys.exit(1)
dropped = sorted(set(by_name) - {f["name"] for f in fin})
print("役の再定義: v1.3n", len(by_name), "種 → 最終", len(fin), "種(削除", len(dropped), "/ 1本化・新規", len(NEWY), ")")
yaku = final_rows
for i, r in enumerate(yaku, 1): r["id"] = f"Y{i:03d}"
YCOLS = ["id", "name", "pattern", "group", "tier", "condition_type", "params", "han_provisional", "han_status", "description"]
wcsv("yaku.csv", YCOLS, [[r[c] for c in YCOLS] for r in yaku])

# 役が参照する語・セレクターが、辞書にあるか
bad = []
for r in yaku:
    p = r["params"]
    for g in p.replace("/", ";").split(";"):
        for t in g.split("|"):
            t = t.split("=", 1)[-1] if "=" in t else t
            if r["condition_type"] in ("count_in_set", "one_from_each", "contains_all", "all_in_set") and t and ":" not in t and t not in widx and not t.isdigit() and t not in ("set", "min"):
                bad.append((r["name"], t))
if bad: print("エラー: 役が参照する語が辞書にない:", bad); sys.exit(1)

wcsv("yaku_class.csv", ["name", "han", "class", "note"], [[f["name"], f["han"], rcl[f["name"]]["新区分"], rcl[f["name"]]["備考"]] for f in fin])
print("区分:", dict(Counter(rcl[f["name"]]["新区分"].split("(")[0] for f in fin)))

# ---------------- 名前つき合体17(merge_final_v3.csv)。翻 = 元の翻の合計 + 1(小・中合体)/ + 2(大合体) ----------------
yhan = {}
for r in yaku: yhan.setdefault(r["name"], int(r["han_provisional"]))
mrows, diff, missing = [], [], []
for i, m in enumerate(rd(os.path.join(DATA, "merge_final_v3.csv")), 1):
    src = m["source_yaku"].split("|")
    miss = [x for x in src if x not in yhan]
    if miss: missing.append((m["name"], miss)); continue
    tot_ = sum(yhan[x] for x in src); han = tot_ + (2 if m["level"] == "大合体" else 1)
    if han != int(m["han(新)"]): diff.append((m["name"], han, m["han(新)"]))
    mrows.append([m["id"], m["name"], m["source_yaku"], tot_, han, m["level"], "仮", m["note"]])
wcsv("yaku_merge.csv", ["id", "name", "source_yaku", "source_han_total", "han_provisional", "level", "han_status", "description"], mrows)
print("名前つき合体", len(mrows), "/ 元の役が新しい一覧にない合体:", missing or "なし", "/ CSVの翻(新)と違うもの:", diff or "なし")
