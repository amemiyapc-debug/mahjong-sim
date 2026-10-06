# ひらがな麻雀(仮) dan5: 新辞書(343語)への移行。語・役・牌の枚数のCSVの生成と検証。
#   python3 dan5/gen.py            → dan5/ に words.csv / heads.csv / yaku.csv / yaku_merge.csv / tile_usage.csv / tile_variants.csv /
#                                     tile_copies.csv / tile_copies_conditions.csv を出力する
# 入力:
#   ../data/words_by_slot_v15.csv  新辞書の本体(語・スロット)。牌は、語の読みから決める(下の tokenize)
#   ../data/modifier_triples_B.csv 前置き(修飾牌だけの面子)58語(案B)
#   ../v13m/                       旧辞書(v1.3m。語の属性・雀頭・役・合体の元)。既存の語の属性は、ここから引き継ぐ
#   yaku_v13n_spec.csv / merge_v13n_spec.csv  v1.3n の役(試作HTMLの判定ロジックから取り出した177行・合体36)
# 検査(失敗したら止まる): 牌の組み合わせ(つ=っ・ぉ゛=お を同一視)が同じ語の重複 / 役・合体が参照する語がない / 語の読みと牌の不一致
import csv, math, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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
             "まめ": "女性器", "ちく": "胸", "くち": "口", "すじ": "女性器", "ちち": "胸"}     # 「ち-ち」語幹を胸の部位に含める(依頼 B)
STEM_CANON = {"まめ": "くり"}
STEMS_X2 = set(STEM_PART) | {"べろ", "すき", "きく", "おな", "あな", "めす", "おす", "ぱか", "くぱ", "くぽ", "まま", "いき", "ぱこ", "おち", "まけ"}

old = {}
for r in rd(os.path.join(V13M, "words.csv")):
    for x in r["word"].split("・"):
        old[x] = r

# ---------------- 語 ----------------
words, problems = [], []
for r in rd(os.path.join(DATA, "words_by_slot_v15.csv")):
    name = r["word"]; reads = name.split("・"); toks = [tokenize(x) for x in reads]; first = toks[0]
    x2 = r["source"] == "×2"
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
        if r["slot"] == "喘ぎ声" and not x2 and r["source"] != "×2":
            row["flavor"] = "オホ声系" if any(nrm(t) == "お" for t in tiles) else "可愛い系"
        if x2 and r["slot"] == "喘ぎ声":
            row["flavor"] = "オホ声系" if any(nrm(t) == "お" for t in tiles) else "可愛い系"
    words.append(row)
for r in rd(os.path.join(DATA, "modifier_triples_B.csv")):
    ts = [r["tile1"], r["tile2"], r["tile3"]]
    words.append(dict(word=r["name"], tiles="|".join(ts), slot_no="0", slot="前置き", sub=r["type"], source="前置き(案B)", note="修飾牌3つの語",
                      type="修飾3型", modifier="", modifiers="|".join(ts), position="", stem="", part="", tag="修飾3", flavor=""))

# 牌の組み合わせが同じ語は、「・」で1語にまとめる(CSVの「A・B」と同じ扱い)。ここに書いたものだけ。ほかの重複は、下の検査で失敗する。
#   ぉ゛っぉ゛っ は、おっおっ と牌の組み合わせが同じ(ぉ゛=お。ぉ゛を使えば、ぉ゛っぉ゛っと表示される)。要確認(×2語は62→61語になる)
DUP_MERGE = {"ぉ゛っぉ゛っ": "おっおっ"}
for dup, keep in DUP_MERGE.items():
    a = next(w for w in words if w["word"] == keep); b = next(w for w in words if w["word"] == dup)
    a["word"] = keep + "・" + dup; a["note"] = (a["note"] + " / " if a["note"] else "") + "ぉ゛っぉ゛っ と牌の組み合わせが同じ(ぉ゛=お)なので統合"; words.remove(b)
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
conds = [(0.1, 13), (0.05, 13), (0.0, 13), (0.1, 12), (0.1, 14)]
tot = []
for modx, n in conds:
    c = copies(modx, n); tot.append([modx, n, sum(c.values()), len(c)])
base = copies(0.1, 13)
wcsv("tile_copies.csv", ["tile", "used_in_words", "base_copies", "modifier_bonus", "copies"],
     [[t, used.get(t, 0), (base[t] - (int(0.1 * demand[t] + 0.5) if t in MODS else 0)) if t in used else base[t], int(0.1 * demand[t] + 0.5) if t in MODS else 0, base[t]]
      for t in sorted(base, key=lambda t: (-base[t], t))])
wcsv("tile_copies_conditions.csv", ["MODX", "x2_copies", "wall_tiles", "tile_types"], tot)
print("山(MODX,×2) =", [(m, n, t) for m, n, t, _ in tot])

# ---------------- 役(v1.3n) ----------------
def key(g, t, ct, p): return (g, int(t or 0), ct, p)
y13m = rd(os.path.join(V13M, "yaku.csv"))
spec = rd(os.path.join(HERE, "yaku_v13n_spec.csv"))
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

# ---------------- 合体(v1.3n)。元の役の翻から、元の合計+1(2役)/+2(3役)を計算し、試作HTMLの値と照合する ----------------
yhan = {r["name"]: int(r["han_provisional"]) for r in yaku}
m13 = {r["name"]: r for r in rd(os.path.join(V13M, "yaku_merge.csv"))}
mrows, diff = [], []
for i, s in enumerate(rd(os.path.join(HERE, "merge_v13n_spec.csv")), 1):
    src = s["source_yaku"].split("|"); assert all(x in yhan for x in src), (s["name"], src)
    tot_ = sum(yhan[x] for x in src); han = tot_ + (1 if len(src) == 2 else 2)
    if han != int(s["han_provisional"]): diff.append((s["name"], han, s["han_provisional"]))
    o = m13[s["name"]]
    lv = "大合体" if (len(src) >= 3 or han >= 9) else ("中合体" if han >= 5 else "小合体")
    mrows.append([f"M{i:03d}", s["name"], s["source_yaku"], tot_, han, lv, "仮", o["description"]])
wcsv("yaku_merge.csv", ["id", "name", "source_yaku", "source_han_total", "han_provisional", "level", "han_status", "description"], mrows)
print("合体", len(mrows), "/ 試作HTMLの翻と違うもの:", diff or "なし")
