# ひらがな麻雀(仮) 語リスト・役リストの生成と検証 v1.2
# 使い方: python gen.py  → 同じフォルダに words.csv / yaku.csv / tile_usage.csv を出力
import csv, os
from collections import Counter
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------- 語 ----------------
STEM = {  # 語幹(2牌)
 "ちん":["ち","ん"], "まん":["ま","ん"], "けつ":["け","つ"], "ぱい":["ぱ","い"],
 "くり":["く","り"], "ちつ":["ち","つ"], "まぞ":["ま","ぞ"], "さど":["さ","ど"],
}
STEM_PART = {"ちん":"男性器","まん":"女性器","けつ":"後ろ","ぱい":"胸","くり":"女性器","ちつ":"女性器","まぞ":"SM","さど":"SM"}
HEAD = {  # 語頭に付く修飾牌: 語幹の前
 "見せ":["ちん","まん","けつ","ぱい","くり","ちつ"],
 "デカ":["ちん","けつ","ぱい","くり"],
 "エロ":["ちん","まん","けつ","ぱい","くり","ちつ"],
 "ぬれ":["まん","ちつ","くり","ぱい"],
}
TAIL = {  # 語尾に付く修飾牌: 語幹の後
 "穴":["ちん","まん","けつ","まぞ","さど"],
 "媚":["ちん","まん","まぞ","さど"],
 "♡":["ちん","まん","けつ","ぱい","くり","ちつ"],
 "舐":["ちん","まん","けつ","ぱい","くり","ちつ"],
 "コキ":["ちん","まん","けつ","ぱい","くり","ちつ"],
}
SINGLES = [  # (語, 牌, 部位, タグ, 備考)
 ("ちんぽ",["ち","ん","ぽ"],"男性器","男性器","ぽは専用牌"),
 ("ちんこ",["ち","ん","こ"],"男性器","男性器",""),
 ("まんこ",["ま","ん","こ"],"女性器","女性器",""),
 ("おめこ",["お","め","こ"],"女性器","女性器",""),
 ("ちくび",["ち","く","び"],"胸","胸",""),
 ("あなる",["あ","な","る"],"後ろ","後ろ",""),
 ("こうび",["こ","う","び"],"","行為",""),
 ("がんしゃ",["が","ん","しゃ"],"","行為","しゃ=拗音1牌"),
 ("いかせ",["い","か","せ"],"","行為",""),
 ("いじり",["い","じ","り"],"","行為",""),
 ("しゃせい",["しゃ","せ","い"],"","絶頂","しゃ=拗音1牌"),
 ("あくめ",["あ","く","め"],"","絶頂",""),
 ("いくっ",["い","く","っ"],"","絶頂",""),
 ("ちゅっちゅ",["ちゅ","っ","ちゅ"],"","キス","ちゅ=拗音1牌・2枚使用"),
 ("べろちゅ",["べ","ろ","ちゅ"],"","キス","ちゅ=拗音1牌"),
 ("きっす",["き","っ","す"],"","キス",""),
]
words = []
def add(word, wtype, mod, pos, stem, tiles, part, tag, note=""):
    words.append(dict(word=word, type=wtype, modifier=mod, position=pos, stem=stem,
        tiles="|".join(tiles), tile_count=len(tiles), part=part, tag=tag, note=note))
for w,t,p,tag,n in SINGLES: add(w,"単独","","","",t,p,tag,n)
for m,ss in HEAD.items():
    for s in ss: add(m+s, m+"型", m, "語頭", s, [m]+STEM[s], STEM_PART[s], STEM_PART[s])
for m,ss in TAIL.items():
    for s in ss: add(s+m, m+"型", m, "語尾", s, STEM[s]+[m], STEM_PART[s], STEM_PART[s])
for i,r in enumerate(words,1): r["id"]=f"W{i:03d}"
WORDSET = {r["word"] for r in words}

# ---------------- 役 ----------------
# condition_type と params の書式は CLAUDE.md §6-2
KISS = "ちゅっちゅ|べろちゅ|きっす"
ZETCHO = "いくっ|あくめ|しゃせい"
yaku = []
def Y(name, pattern, group, tier, ctype, params, han, desc, han_status="仮"):
    yaku.append(dict(name=name, pattern=pattern, group=group, tier=tier,
        condition_type=ctype, params=params, han_provisional=han, han_status=han_status, description=desc))

# はしご(修飾牌): 二/三/四
MOD_LADDER = {
 "見せ":("ちら見せ","見せたがり","露出狂"),
 "デカ":("デカめ","デカ盛り","規格外"),
 "エロ":("ちょいエロ","エロ全開","エロの化身"),
 "ぬれ":("しっとり","びしょ濡れ","大洪水"),
 "穴":("穴ふたつ","穴だらけ","穴という穴"),
 "媚":("上目づかい","媚び媚び","媚び堕ち"),
 "♡":("ハート多め","ハートまみれ","愛より重く"),
 "舐":("ぺろぺろ","舐め尽くし","全身舐め"),
 "コキ":("しこしこ","搾り取り","搾り尽くし"),
}
for m,names in MOD_LADDER.items():
    for n,(nm,han) in zip((2,3), zip(names[:2],(1,2))):
        Y(nm,"はしご(修飾牌)",f"mod:{m}",n,"count_same_modifier",f"mod={m};n={n}",han,f"{m}を使う語が{n}語")
# はしご(語幹): 二/三/四(四は語幹共通の名前)
for s in ["ちん","まん","けつ","ぱい","くり","ちつ"]:
    Y(f"{s}好き","はしご(語幹)",f"stem:{s}",2,"count_same_stem",f"stem={s};n=2",1,f"語幹{s}の語が2語")
    Y(f"{s}に夢中","はしご(語幹)",f"stem:{s}",3,"count_same_stem",f"stem={s};n=3",2,f"語幹{s}の語が3語")
    Y("童貞目線","はしご(語幹)",f"stem:{s}",4,"one_from_each",f"stem:{s};stem:{s};stem:{s};part:{STEM_PART[s]}",3,f"語幹{s}の語が3語以上で、残り1語も同じ部位(4語とも{STEM_PART[s]})")
# 構造型
Y("同じ部位","構造型","",0,"count_same_part","n=3",2,"同じ部位(男性器/女性器/胸/後ろ)の語が3語以上。SMと部位なしは除く")
Y("語尾そろい","構造型","",0,"count_tail_same_part","n=3",2,"語尾牌(穴・媚・♡・舐・コキ)を使う語が3語以上で、それらが同じ部位","未定")
Y("語頭づくし","構造型","",0,"all_in_set","set=mod:見せ|mod:デカ|mod:エロ|mod:ぬれ",3,"4語すべて語頭の修飾牌付き(見せ・デカ・エロ・ぬれ)","仮")
Y("語尾づくし","構造型","",0,"all_in_set","set=mod:穴|mod:媚|mod:♡|mod:舐|mod:コキ",2,"4語すべて語尾の修飾牌付き(穴・媚・♡・舐・コキ)","仮")
Y("素の言葉","構造型","",0,"singles_eq","n=4",2,"単独語だけで4語")
Y("修飾づくし","構造型","",0,"singles_eq","n=0",1,"単独語なし(4語すべて修飾牌付き)")
Y("全身くまなく","構造型","",0,"one_from_each","part:男性器;part:女性器;part:胸;part:後ろ",1,"男性器・女性器・胸・後ろの語を1つずつ")
Y("奥まで全部","構造型","",0,"one_from_each","stem:まん|まんこ|おめこ;stem:くり;stem:ちつ",1,"まんの語(まんこ・おめこ含む)・くりの語・ちつの語を1つずつ")
# カテゴリ集め型
Y("キスの雨","カテゴリ集め型","",0,"count_in_set",f"min=2;set={KISS}",1,"キス系が2語以上")
Y("絶頂そろい","カテゴリ集め型","",0,"count_in_set",f"min=2;set={ZETCHO}",2,"絶頂系が2語以上")
Y("まさかのキスアクメ","カテゴリ集め型","",0,"count_in_set",f"min=3;set={KISS}|{ZETCHO}",4,"キス系か絶頂系の語が3語以上","未定")
# ペア型
Y("淫語中毒","ペア型","",0,"contains_all","ちんぽ|まんこ",3,"ちんぽ + まんこ")
Y("前も後ろも","ペア型","",0,"contains_all","まんこ|あなる",3,"まんこ + あなる")
Y("見せ合い","ペア型","",0,"contains_all","見せちん|見せまん",3,"見せちん + 見せまん")
Y("らぶらぶ","ペア型","",0,"contains_all","ちん♡|まん♡",3,"ちん♡ + まん♡")
Y("シックスナイン","ペア型","",0,"contains_all","ちん舐|まん舐",3,"ちん舐 + まん舐")
Y("連続絶頂","ペア型","zetcho_chain",1,"contains_all","いかせ|いくっ",3,"いかせ + いくっ")
Y("むちむちばんばん","ペア型","",0,"contains_all","デカけつ|デカぱい",3,"デカけつ + デカぱい","未定")
Y("M気質","ペア型","",0,"contains_all","まぞ穴|まぞ媚",3,"まぞ穴 + まぞ媚","未定")
Y("S気質","ペア型","",0,"contains_all","さど穴|さど媚",3,"さど穴 + さど媚","未定")
Y("主従","ペア型","",0,"contains_all","まぞ穴|さど穴/まぞ媚|さど媚",2,"まぞ穴 + さど穴、またはまぞ媚 + さど媚")
# 行為→結末型
Y("子づくり","行為→結末型","",0,"contains_all","こうび|しゃせい",3,"こうび + しゃせい")
Y("ご奉仕フィニッシュ","行為→結末型","",0,"contains_all","ちん舐|しゃせい",3,"ちん舐 + しゃせい")
Y("顔面フィニッシュ","行為→結末型","",0,"one_from_each","がんしゃ;ちんコキ|ちん舐",2,"がんしゃ + ちんコキ/ちん舐")
Y("準備万端","行為→結末型","",0,"one_from_each","mod:ぬれ;こうび",2,"ぬれの語 + こうび")
Y("攻め♀","行為→結末型","",0,"one_from_each","さど穴|さど媚;しゃせい",2,"さど穴/さど媚 + しゃせい","未定")
Y("M堕ち","行為→結末型","",0,"one_from_each","まぞ穴|まぞ媚;いくっ|あくめ|いかせ",1,"まぞ穴/まぞ媚 + いくっ/あくめ/いかせ")
Y("見られてイく","行為→結末型","",0,"one_from_each","mod:見せ;いくっ|あくめ",1,"見せの語 + いくっ/あくめ")
Y("濡れて絶頂","行為→結末型","",0,"one_from_each","mod:ぬれ;いくっ|あくめ",1,"ぬれの語 + いくっ/あくめ")
# 部位×行為型
Y("同時責め","部位×行為型","",0,"one_from_each","まんコキ|くりコキ;くり舐|まん舐",2,"まんコキ/くりコキ + くり舐/まん舐")
Y("胸責め","部位×行為型","",0,"one_from_each","ちくび;ぱいコキ|ぱい舐",2,"ちくび + ぱいコキ/ぱい舐")
Y("尻開発","部位×行為型","",0,"one_from_each","あなる;けつコキ|けつ舐|けつ穴",2,"あなる + けつコキ/けつ舐/けつ穴")
Y("デカぱい責め","部位×行為型","",0,"one_from_each","デカぱい;ぱいコキ|ぱい舐|ちくび",2,"デカぱい + ぱいコキ/ぱい舐/ちくび")
Y("調教","部位×行為型","",0,"one_from_each","いじり;まぞ穴|まぞ媚|さど穴|さど媚",2,"いじり + まぞ穴/まぞ媚/さど穴/さど媚")
Y("三点責め","部位×行為型","",0,"one_from_each","ちくび;stem:ぱい;stem:くり",2,"ちくび + ぱいの語 + くりの語")
Y("ダブル奉仕","部位×行為型","",0,"pair_same_stem_modifiers","コキ|舐",1,"Xコキ + X舐(Xは同じ語幹)")
# 物語型
Y("恋人のキス","物語型","love",1,"one_from_each",f"{KISS};mod:♡",1,"キス系 + ♡の語")
Y("らぶイキ","物語型","love",2,"one_from_each",f"{KISS};mod:♡;{ZETCHO}",3,"キス系 + ♡の語 + 絶頂系","未定")
Y("フルコース","物語型","",0,"one_from_each",f"{KISS};mod:コキ|mod:舐;{ZETCHO}",3,"キス系 + コキ・舐の語 + 絶頂系")
Y("アクメ地獄","物語型","zetcho_chain",2,"contains_all","あくめ|いくっ|いかせ",4,"あくめ + いくっ + いかせ")
# 単語きっかけ型
Y("本番","単語きっかけ型","",0,"contains_all","こうび",1,"こうびが入る","未定")
for i,r in enumerate(yaku,1): r["id"]=f"Y{i:03d}"

# ---------------- 検証 ----------------
by = {r["word"]:r for r in words}
def expand(token):
    if token.startswith("mod:"):  return {r["word"] for r in words if r["modifier"]==token[4:]}
    if token.startswith("stem:"): return {r["word"] for r in words if r["stem"]==token[5:]}
    if token.startswith("part:"): return {r["word"] for r in words if r["part"]==token[5:]}
    assert token in WORDSET, f"辞書にない語: {token}"
    return {token}
for y in yaku:
    ct,p = y["condition_type"], y["params"]
    if ct=="one_from_each":
        for g in p.split(";"):
            s=set().union(*[expand(t) for t in g.split("|")]); assert s, (y["name"],g)
    elif ct=="contains_all":
        for alt in p.split("/"):
            for w in alt.split("|"): expand(w)
    elif ct in ("count_in_set","all_in_set"):
        for w in p.split("set=")[1].split("|"): expand(w)
    elif ct=="count_same_modifier":
        m=dict(kv.split("=") for kv in p.split(";")); 
        assert len(expand("mod:"+m["mod"]))>=int(m["n"]), y["name"]
    elif ct=="count_same_stem":
        m=dict(kv.split("=") for kv in p.split(";"))
        assert len(expand("stem:"+m["stem"]))>=int(m["n"]), y["name"]
assert all(r["tile_count"]==3 for r in words)
assert len(WORDSET)==len(words)
ids=[(y["group"],y["tier"]) for y in yaku if y["group"]]
assert len(ids)==len(set(ids)), "同じgroup内でtierが重複"

# ---------------- 出力 ----------------
wcols=["id","word","type","modifier","position","stem","tiles","tile_count","part","tag","note"]
with open(os.path.join(OUT,"words.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=wcols); w.writeheader(); w.writerows(words)
ycols=["id","name","pattern","group","tier","condition_type","params","han_provisional","han_status","description"]
with open(os.path.join(OUT,"yaku.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=ycols); w.writeheader(); w.writerows(yaku)
use=Counter(); cnt=Counter()
for r in words:
    ts=r["tiles"].split("|")
    for t in set(ts): use[t]+=1
    for t in ts: cnt[t]+=1
with open(os.path.join(OUT,"tile_usage.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["tile","used_in_words","total_occurrences_in_all_words"])
    for t,c in use.most_common(): w.writerow([t,c,cnt[t]])

print("語数:",len(words), Counter(r["type"] for r in words))
print("役の行数:",len(yaku),"/ 役名の種類:",len({y['name'] for y in yaku}))
print(Counter(y["pattern"] for y in yaku))
print("牌の種類:",len(use),"/ 専用牌:",[t for t,c in use.items() if c==1])
print("頻出:",use.most_common(8))
