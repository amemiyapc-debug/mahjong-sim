import csv, os
OUT = os.path.dirname(os.path.abspath(__file__))  # gen.py と同じフォルダに出力
from collections import Counter

# 語幹(2牌)
STEM = {
 "ちん":["ち","ん"], "まん":["ま","ん"], "けつ":["け","つ"], "まぞ":["ま","ぞ"],
 "さど":["さ","ど"], "ぱい":["ぱ","い"], "くり":["く","り"], "ちつ":["ち","つ"],
}
TAG = {"ちん":"男性器","まん":"女性器","けつ":"後ろ","まぞ":"SM","さど":"SM","ぱい":"胸","くり":"女性器","ちつ":"女性器"}

rows = []
def add(word, wtype, mod, stem, tiles, han, tag, note=""):
    rows.append(dict(word=word, type=wtype, modifier=mod, stem=stem,
        tiles="|".join(tiles), tile_count=len(tiles), part="", tag=tag, note=note))

# 単独語 (名前, 牌, 仮翻, タグ, 備考)
singles = [
 ("ちんぽ",["ち","ん","ぽ"],3,"男性器","ぽは専用牌(ちんぽのみ)"),
 ("ちんこ",["ち","ん","こ"],2,"男性器",""),
 ("まんこ",["ま","ん","こ"],2,"女性器",""),
 ("おめこ",["お","め","こ"],2,"女性器",""),
 ("ちくび",["ち","く","び"],2,"胸",""),
 ("こうび",["こ","う","び"],2,"行為",""),
 ("あなる",["あ","な","る"],2,"後ろ",""),
 ("しゃせい",["しゃ","せ","い"],2,"絶頂","しゃ=拗音1牌"),
 ("がんしゃ",["が","ん","しゃ"],2,"行為","しゃ=拗音1牌"),
 ("あくめ",["あ","く","め"],2,"絶頂",""),
 ("いくっ",["い","く","っ"],2,"絶頂",""),
 ("いかせ",["い","か","せ"],2,"行為",""),
 ("いじり",["い","じ","り"],1,"行為",""),
 ("ちゅっちゅ",["ちゅ","っ","ちゅ"],1,"キス","ちゅ=拗音1牌・ちゅ2枚使用"),
 ("べろちゅ",["べ","ろ","ちゅ"],1,"キス","ちゅ=拗音1牌"),
 ("きっす",["き","っ","す"],1,"キス",""),
]
for w,t,h,tag,n in singles: add(w,"単独","","",t,h,tag,n)

def build(mod, stems, pos, han, tag_mod, label):
    for s in stems:
        tiles = [mod]+STEM[s] if pos=="前" else STEM[s]+[mod]
        word = (mod+s) if pos=="前" else (s+mod)
        add(word, label, mod, s, tiles, han, f"{tag_mod}/{TAG[s]}")

build("穴",["ちん","まん","けつ","まぞ","さど"],"後",1,"語尾","穴型")
build("媚",["ちん","まん","まぞ","さど"],"後",2,"語尾","媚型")
build("見せ",["ちん","まん","けつ","ぱい"],"前",1,"状況","見せ型")
build("手",["ちん","まん","けつ","ぱい"],"前",2,"行為","手型")
build("舐",["ちん","まん","けつ","ぱい"],"前",2,"行為","舐型")
build("デカ",["ちん","けつ","ぱい","くり"],"前",1,"大きさ","デカ型")
build("エロ",["ちん","まん","けつ","ぱい","くり","ちつ"],"前",1,"いやらしさ","エロ型")
build("♡",["ちん","まん","けつ","ぱい","くり","ちつ"],"前",1,"気持ち","♡型")
build("ぬれ",["まん","ちつ","くり","ぱい"],"前",1,"状態","ぬれ型")
# くり・ちつ組み合わせ
for mod,s in [("舐","くり"),("手","くり"),("見せ","くり"),("舐","ちつ"),("見せ","ちつ")]:
    add(mod+s,"組合せ型",mod,s,[mod]+STEM[s],2 if mod!="見せ" else 1,f"{ {'舐':'行為','手':'行為','見せ':'状況'}[mod]}/{TAG[s]}")


PART_STEM = {"ちん":"男性器","まん":"女性器","けつ":"後ろ","まぞ":"SM","さど":"SM","ぱい":"胸","くり":"女性器","ちつ":"女性器"}
PART_SINGLE = {"ちんぽ":"男性器","ちんこ":"男性器","まんこ":"女性器","おめこ":"女性器","ちくび":"胸","あなる":"後ろ"}
for r in rows:
    r["part"] = PART_STEM.get(r["stem"], "") if r["stem"] else PART_SINGLE.get(r["word"], "")

for i,r in enumerate(rows,1): r["id"]=f"W{i:03d}"
cols=["id","word","type","modifier","stem","tiles","tile_count","part","tag","note"]
with open(os.path.join(OUT,"words.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

# 検証
assert all(r["tile_count"]==3 for r in rows), "3牌でない語あり"
assert len({r["word"] for r in rows})==len(rows), "重複語あり"
print("語数:",len(rows))
print(Counter(r["type"] for r in rows))

# 牌の使用語数(何語で使われるか)
use=Counter(); cnt=Counter()
for r in rows:
    ts=r["tiles"].split("|")
    for t in set(ts): use[t]+=1
    for t in ts: cnt[t]+=1
with open(os.path.join(OUT,"tile_usage.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["tile","used_in_words","total_occurrences_in_all_words"])
    for t,c in use.most_common(): w.writerow([t,c,cnt[t]])
print("牌の種類:",len(use))
print(use.most_common(12))
print("専用牌(1語のみ):",[t for t,c in use.items() if c==1])

# ---- 役 (yaku.csv) ----
yaku = [
 # id, name, kind, group(同groupは最高位のみ適用), condition_type, params, han, description
 ("Y001","同じ修飾牌・二","汎用","same_modifier","count_same_modifier","2",1,"同じ修飾牌を使う語が2語"),
 ("Y002","同じ修飾牌・三","汎用","same_modifier","count_same_modifier","3",2,"同じ修飾牌を使う語が3語"),
 ("Y003","同じ修飾牌・四","汎用","same_modifier","count_same_modifier","4",3,"同じ修飾牌を使う語が4語"),
 ("Y004","同じ語幹・二","汎用","same_stem","count_same_stem","2",1,"同じ語幹の語が2語"),
 ("Y005","同じ語幹・三","汎用","same_stem","count_same_stem","3",2,"同じ語幹の語が3語"),
 ("Y006","同じ語幹・四","汎用","same_stem","count_same_stem","4",3,"同じ語幹の語が4語"),
 ("Y007","素の言葉","汎用","","singles_eq","4",2,"修飾牌なしの単独語だけで4語"),
 ("Y008","修飾づくし","汎用","","singles_eq","0",1,"単独語ゼロ(4語すべて修飾牌付きか組合せ型)"),
 ("Y009","語尾そろい","汎用","","count_tail_modifier","3",1,"語尾牌(穴・媚)を使う語が3語以上"),
 ("Y010","キスの雨","汎用","","count_in_set","min=2;set=ちゅっちゅ|べろちゅ|きっす",2,"キス系の語が2語以上"),
 ("Y011","絶頂そろい","汎用","","count_in_set","min=2;set=いくっ|あくめ|しゃせい",2,"絶頂系の語が2語以上"),
 ("Y012","同じ部位","汎用","","count_same_part","3",2,"同じ部位(男性器/女性器/後ろ/胸)の語が3語以上。SMは除く"),
 ("Y013","本番","名指し","","contains_all","ちんぽ|まんこ",2,"ちんぽとまんこが両方入る"),
 ("Y014","ダブル奉仕","名指し","","pair_same_stem_modifiers","手|舐",2,"手X+舐X(同じ語幹X)が両方入る。例: 手ちん+舐ちん、手まん+舐まん"),
 ("Y015","主従","名指し","","contains_all","まぞ穴|さど穴/まぞ媚|さど媚",2,"まぞ穴+さど穴、またはまぞ媚+さど媚。/はOR、|はAND"),
 ("Y016","前も後ろも","名指し","","contains_all","まんこ|あなる",2,"まんことあなるが両方入る"),
]
ycols=["id","name","kind","group","condition_type","params","han_provisional","description"]
with open(os.path.join(OUT,"yaku.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(ycols); w.writerows(yaku)
print("役数:",len(yaku))
