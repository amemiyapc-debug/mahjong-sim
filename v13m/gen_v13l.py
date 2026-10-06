# ひらがな麻雀(仮) 語リスト・役リストの生成と検証 v1.2
# 使い方: python gen.py  → 同じフォルダに words.csv / yaku.csv / tile_usage.csv を出力
import csv, os
from collections import Counter
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------- 語 ----------------
STEM = {  # 語幹(2牌)
 "ちん":["ち","ん"], "まん":["ま","ん"], "けつ":["け","つ"], "ぱい":["ぱ","い"],
 "くり":["く","り"], "ちつ":["ち","つ"], "まぞ":["ま","ぞ"], "さど":["さ","ど"],
 "めす":["め","す"], "おす":["お","す"], "べろ":["べ","ろ"], "まま":["ま","ま"], "まめ":["ま","め"], "あな":["あ","な"], "ちく":["ち","く"], "くち":["く","ち"], "ぱか":["ぱ","か"], "くぱ":["く","ぱ"], "くぽ":["く","ぽ"], "おな":["お","な"], "すき":["す","き"], "きく":["き","く"],
}
STEM_PART = {"ちん":"男性器","まん":"女性器","けつ":"後ろ","ぱい":"胸","くり":"女性器","ちつ":"女性器","まぞ":"SM","さど":"SM","めす":"","おす":"","べろ":"","まま":"","まめ":"女性器","あな":"","ちく":"胸","くち":"口","ぱか":"","くぱ":"","くぽ":"","おな":"","すき":"","きく":""}
STEM_TAG={"ぱか":"擬音","くぱ":"擬音","くぽ":"擬音","あな":"穴","くち":"口","おな":"オナ","すき":"ラブ・キス","きく":"快感"}   # 部位のない語幹のタグ
STEM_CANON={"まめ":"くり"}   # 別名の語幹は、役の判定では、もとの語幹として数える
canon=lambda s_: STEM_CANON.get(s_,s_)
HEAD = {  # 語頭に付く修飾牌: 語幹の前
 "見せ":["ちん","まん","けつ","ぱい","くり","ちつ","べろ","まめ","あな","ちく"],
 "デカ":["ちん","けつ","ぱい","くり","まめ","ちく"],
 "エロ":["ちん","まん","けつ","ぱい","くり","ちつ","めす","おす","べろ","まめ","あな","ちく","おな"],
 "ぬれ":["まん","ちつ","くり","ぱい","まめ","おな"],
}
TAIL = {  # 語尾に付く修飾牌: 語幹の後
 "穴":["ちん","まん","けつ","まぞ","さど","めす","おす","くち"],
 "媚び":["ちん","まん","まぞ","さど","めす","おす","けつ","ちつ","ちく"],
 "♡":["ちん","まん","けつ","ぱい","くり","ちつ","めす","おす","べろ","まま","まめ","あな","くち","おな","ぱか","くぱ","くぽ"],
 "舐め":["ちん","まん","けつ","ぱい","くり","ちつ","まめ","あな","ちく"],
 "コキ":["ちん","まん","けつ","ぱい","くり","ちつ","まぞ","さど","まめ","ちく"],
}
SINGLES = [  # (語, 牌, 部位, タグ, 備考)
 ("ちんぽ",["ち","ん","ぽ"],"男性器","男性器","ぽは専用牌"),
 ("ちんこ",["ち","ん","こ"],"男性器","男性器",""),
 ("まんこ",["ま","ん","こ"],"女性器","女性器",""),
 ("おめこ",["お","め","こ"],"女性器","女性器",""),
 ("おまめ",["お","ま","め"],"女性器","女性器",""),
 ("ちくび",["ち","く","び"],"胸","胸",""),
 ("あなる",["あ","な","る"],"後ろ","後ろ",""),
 ("こうび",["こ","う","び"],"","行為",""),
 ("がんしゃ",["が","ん","しゃ"],"","部位射精","しゃ=拗音1牌"),
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
def add(word, wtype, mod, pos, stem, tiles, part, tag, note="", flavor="", modifiers=None):
    words.append(dict(modifiers=(mod if modifiers is None else modifiers), flavor=flavor, word=word, type=wtype, modifier=mod, position=pos, stem=stem,
        tiles="|".join(tiles), tile_count=len(tiles), part=part, tag=tag, note=note))
for w,t,p,tag,n in SINGLES: add(w,"単独","","","",t,p,tag,n)
# 3牌の喘ぎ声(面子タイプ)。牌の組み合わせが同じ語(あんっ/んあっ など)は、1つにまとめる
MOAN_WORDS=[("あんっ",["あ","ん","っ"],"可愛い系"),("ああっ",["あ","あ","っ"],"可愛い系"),
            ("おおっ",["お","お","っ"],"オホ声系"),("んおっ",["ん","お","っ"],"オホ声系"),("んんっ",["ん","ん","っ"],"どちらでも"),
            ("うおお",["う","お","お"],"オホ声系"),("あうう",["あ","う","う"],"可愛い系"),("うんん",["う","ん","ん"],"可愛い系")]
for w,t,fl in MOAN_WORDS: add(w,"単独","","","",t,"","喘ぎ声","3牌の喘ぎ声",fl)
# 命令語(3牌・既存の牌だけ)。強要や暴力を連想させる言い方は入れない
CMD_WORDS=[("なめろ","強め(〜ろ)"),("せめろ","強め(〜ろ)"),("あけろ","強め(〜ろ)"),("おちろ","強め(〜ろ)"),
           ("なめな","やさしい(〜な)"),("せめな","やさしい(〜な)"),("あけな","やさしい(〜な)"),("いきな","やさしい(〜な)"),
           ("いけっ","短い"),("なけっ","短い"),("さけべ","短い"),("いくな","禁止"),("おなめ","丁寧(お〜)")]
for w,fl in CMD_WORDS: add(w,"単独","","","",list(w),"","命令語","3牌の命令語",fl)
# 部位射精(しゃ=射)・割れ目の開き表現・赤ちゃん・快感
for w,t in (("まんしゃ",["ま","ん","しゃ"]),("けつしゃ",["け","つ","しゃ"]),("ぱいしゃ",["ぱ","い","しゃ"])): add(w,"単独","","","",t,"","部位射精","部位+しゃ(射)")
for w,t in (("ぱかあ",["ぱ","か","あ"]),("くぱあ",["く","ぱ","あ"]),("ぱかっ",["ぱ","か","っ"]),("くぱっ",["く","ぱ","っ"]),("ぱかん",["ぱ","か","ん"]),("くちゅっ",["く","ちゅ","っ"]),("くぽっ",["く","ぽ","っ"])): add(w,"単独","","","",t,"","擬音","割れ目の開き表現(擬音)")
add("ままあ","単独","","","",["ま","ま","あ"],"","赤ちゃん","まま♡と同じ面子(役: 赤ちゃんプレイ)")
add("きつく・きっく","単独","","","",["き","つ","く"],"","快感","つ=っ(互換)なので、きつく/きっく は同じ語")
add("きくう","単独","","","",["き","く","う"],"","快感","")
# すき(ラブ)/きす(キス)は、牌が同じなので、1つの語に2つの読み。穴・エロ・ぬれは語頭、♡は語尾
for nm,mod_,pos_,ts in (("すき♡・きす♡","♡","語尾",["す","き","♡"]),("穴すき・きす穴","穴","語頭",["穴","す","き"]),("エロすき・エロきす","エロ","語頭",["エロ","す","き"]),("ぬれすき・ぬれきす","ぬれ","語頭",["ぬれ","す","き"])):
    add(nm,mod_+"型",mod_,pos_,"すき",ts,"","ラブ・キス","すき(ラブ)ときす(キス)の両方に読める")
add("きく♡","♡型","♡","語尾","きく",["き","く","♡"],"","快感","")
add("穴きく","穴型","穴","語頭","きく",["穴","き","く"],"","快感","穴が語頭に付く例外")
# おな(オナ): 媚びは、おなの前に付く(語順の例外)
add("媚びおな","媚び型","媚び","語頭","おな",["媚び","お","な"],"","オナ","媚びが語頭に付く例外")
for m,ss in HEAD.items():
    for s in ss: add(m+s, m+"型", m, "語頭", canon(s), [m]+STEM[s], STEM_PART[s], STEM_TAG.get(s,STEM_PART[s] or "役割"))
for m,ss in TAIL.items():
    for s in ss: add(s+m, m+"型", m, "語尾", canon(s), STEM[s]+[m], STEM_PART[s], STEM_TAG.get(s,STEM_PART[s] or "役割"))
# 語順の例外: コキは、あなの前に付く(コキあな)。あなコキは語として成立しない。牌の組み合わせが同じなら、同じ語として1つにする
add("コキあな","コキ型","コキ","語頭","あな",["コキ","あ","な"],"","穴","コキが語頭に付く例外(あなコキは語ではない)")
for i,r in enumerate(words,1): r["id"]=f"W{i:03d}"
# 修飾牌3つで作る語(語感チェック済みのものだけ。名前は、チェックで決めた並び。modifier_triples_ok.csv から読む)
_tr=os.path.join(OUT,"modifier_triples_ok.csv")
if os.path.exists(_tr):
    for r_ in csv.DictReader(open(_tr,encoding="utf-8-sig")):
        ts=[r_["tile1"],r_["tile2"],r_["tile3"]]
        add(r_["name"],"修飾3型","","","",ts,"","修飾3","修飾牌3つの語",modifiers="|".join(ts))
# 牌が同じ語(ちく/くち の並べ替え)は、1つの語に2つの読みを付ける(部位は、もとの胸のまま)
for r_ in words:
    if r_["word"]=="ちくコキ": r_["word"]="ちくコキ・くちコキ"
    if r_["word"]=="エロちく": r_["word"]="エロちく・エロくち"
    if r_["word"]=="くぱ♡": r_["word"]="くぱ♡・ぱく♡"
_norm={"ぉ゛":"お","っ":"つ"}
_keys={}
for r in words:
    k=tuple(sorted(_norm.get(t,t) for t in r["tiles"].split("|")))
    assert k not in _keys, ("牌の組み合わせが同じ語", r["word"], _keys[k])
    _keys[k]=r["word"]
WORDSET = {r["word"] for r in words}


# ---------------- 雀頭(2牌の語) ----------------
# 喘ぎ声: いまある牌の2枚で作る。略称: 語幹(2牌)のうち、略称として成立するもの(「んぽ」のような語の一部は入れない)
MOANS=[("あん","可愛い系"),("あっ","可愛い系"),("んっ","可愛い系"),("んあ","可愛い系"),("ああ","可愛い系"),
       ("おっ","オホ声系"),("んお","オホ声系"),("おお","オホ声系"),("んん","どちらでも"),
       ("うお","オホ声系"),("あう","可愛い系"),("うん","可愛い系")]
ABBR=["ちん","まん","けつ","ぱい","くり","ちつ","まぞ","さど","めす","おす","べろ","まめ"]
heads=[]
def kana_tiles(txt):  # 1文字が1牌
    return list(txt)
for h,fl in MOANS: heads.append(dict(head=h,tiles="|".join(kana_tiles(h)),type="喘ぎ声",flavor=fl,stem="",note=""))
for h_,tl_ in (("いく",["い","く"]),("きく",["き","く"])): heads.append(dict(head=h_,tiles="|".join(tl_),type="快感",flavor="快感",stem="",note="快感の語"))
heads.append(dict(head="くぽ",tiles="く|ぽ",type="擬音",flavor="開き",stem="",note="擬音(開き)"))
for st in ABBR:   heads.append(dict(head=st,tiles="|".join(STEM[st]),type="略称",flavor=STEM_PART[st] or "役割",stem=canon(st),note="語幹の略称"))
for i,h in enumerate(heads,1): h["id"]=f"H{i:03d}"


# ---------------- 牌の変種(別の牌の代わりになる牌) ----------------
# ぉ゛ は「お」の代わりに使える牌(赤牌のようなもの)。語・雀頭では「お」として扱う。語から数える枚数ルールの対象外で、枚数は固定。
VARIANTS=[dict(tile="っ",base="つ",copies=0,name="互換",mode="replace",note="っとつは、互換の文字(きつく=きっく)。どちらの牌でも、つ・っの語に使える。表示は、使った牌に合わせる"),
          dict(tile="ぉ゛",base="お",copies=4,name="オホ声",mode="replace",note="おの代わりになる牌。持ってアガると『オホ声』の役が付く"),
          dict(tile="ちゅ",base="つ",copies=0,name="赤ちゃん言葉",mode="flex",note="ちゅは、つの代わりにも使える(ちつ→ちちゅ、けつ→けちゅ)。つは、ちゅの代わりにならない(つつ=ちゅっちゅとは認識できないため)。枚数は増やさない")]

# ---------------- 役 ----------------
# condition_type と params の書式は CLAUDE.md §6-2
KISSX = "すき♡・きす♡|穴すき・きす穴|エロすき・エロきす|ぬれすき・ぬれきす"
KISS = "ちゅっちゅ|べろちゅ|きっす|"+KISSX
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
 "媚び":("上目づかい","媚び媚び","媚び堕ち"),
 "♡":("ハート多め","ハートまみれ","愛より重く"),
 "舐め":("ぺろぺろ","舐め尽くし","全身舐め"),
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
PART_SHORT={"男性器":"ちん系","女性器":"まん系","胸":"ぱい系","後ろ":"けつ系"}   # 仮の名前
for pt,short in PART_SHORT.items():
    for n,suf,han in ((2,"コンビ",1),(3,"トリオ",2),(4,"カルテット",3)):
        Y(f"{short}{suf}","はしご(部位)",f"part:{pt}",n,"count_part",f"part={pt};n={n}",han,f"{pt}の語が{n}語以上")
Y("語尾そろい","構造型","",0,"count_tail_same_part","n=3",2,"語尾牌(穴・媚び・♡・舐め・コキ)を使う語が3語以上で、それらが同じ部位","未定")
Y("語頭づくし","構造型","",0,"all_in_set","set=pos:語頭",3,"4語すべて語頭の修飾牌付き(見せ・デカ・エロ・ぬれ)","仮")
Y("語尾づくし","構造型","",0,"all_in_set","set=pos:語尾",2,"4語すべて語尾の修飾牌付き(穴・媚び・♡・舐め・コキ)","仮")
Y("素の言葉","構造型","",0,"singles_eq","n=4",2,"単独語だけで4語")
Y("修飾づくし","構造型","",0,"singles_eq","n=0",1,"単独語なし(4語すべて修飾牌付き)")
Y("全身くまなく","構造型","",0,"one_from_each","part:男性器;part:女性器;part:胸;part:後ろ",1,"男性器・女性器・胸・後ろの語を1つずつ")
Y("奥まで全部","構造型","",0,"one_from_each","stem:まん|まんこ|おめこ|おまめ;stem:くり;stem:ちつ",1,"まんの語(まんこ・おめこ含む)・くりの語・ちつの語を1つずつ")
# カテゴリ集め型
Y("キスの雨","カテゴリ集め型","",0,"count_in_set",f"min=2;set={KISS}",1,"キス系が2語以上")
Y("絶頂そろい","カテゴリ集め型","",0,"count_in_set",f"min=2;set={ZETCHO}",2,"絶頂系が2語以上")
Y("まさかのキスアクメ","カテゴリ集め型","",0,"count_in_set",f"min=3;set={KISS}|{ZETCHO}",4,"キス系か絶頂系の語が3語以上","未定")
# ペア型
Y("淫語中毒","ペア型","",0,"contains_all","ちんぽ|まんこ",3,"ちんぽ + まんこ")
Y("前も後ろも","ペア型","",0,"contains_all","まんこ|あなる",3,"まんこ + あなる")
Y("見せ合い","ペア型","",0,"contains_all","見せちん|見せまん",3,"見せちん + 見せまん")
Y("らぶらぶ","ペア型","",0,"contains_all","ちん♡|まん♡",3,"ちん♡ + まん♡")
Y("シックスナイン","ペア型","",0,"contains_all","ちん舐め|まん舐め",3,"ちん舐め + まん舐め")
Y("連続絶頂","ペア型","zetcho_chain",1,"contains_all","いかせ|いくっ",3,"いかせ + いくっ")
Y("むちむちばんばん","ペア型","",0,"contains_all","デカけつ|デカぱい",3,"デカけつ + デカぱい","未定")
Y("M気質","ペア型","",0,"contains_all","まぞ穴|まぞ媚び",3,"まぞ穴 + まぞ媚び","未定")
Y("S気質","ペア型","",0,"contains_all","さど穴|さど媚び",3,"さど穴 + さど媚び","未定")
Y("主従","ペア型","",0,"contains_all","まぞ穴|さど穴/まぞ媚び|さど媚び/まぞコキ|さどコキ",2,"まぞ穴 + さど穴、まぞ媚び + さど媚び、またはまぞコキ + さどコキ")
# 行為→結末型
Y("子づくり","行為→結末型","",0,"contains_all","こうび|しゃせい",3,"こうび + しゃせい")
Y("ご奉仕フィニッシュ","行為→結末型","",0,"contains_all","ちん舐め|しゃせい",3,"ちん舐め + しゃせい")
Y("顔面フィニッシュ","行為→結末型","",0,"one_from_each","がんしゃ;ちんコキ|ちん舐め",2,"がんしゃ + ちんコキ/ちん舐め")
Y("準備万端","行為→結末型","",0,"one_from_each","mod:ぬれ;こうび",2,"ぬれの語 + こうび")
Y("攻め♀","行為→結末型","",0,"one_from_each","stem:さど;しゃせい",2,"さど系の語 + しゃせい","未定")
Y("M堕ち","行為→結末型","",0,"one_from_each","stem:まぞ;いくっ|あくめ|いかせ",1,"まぞ系の語 + いくっ/あくめ/いかせ")
Y("見られてイく","行為→結末型","",0,"one_from_each","mod:見せ;いくっ|あくめ",1,"見せの語 + いくっ/あくめ")
Y("濡れて絶頂","行為→結末型","",0,"one_from_each","mod:ぬれ;いくっ|あくめ",1,"ぬれの語 + いくっ/あくめ")
# 部位×行為型
Y("同時責め","部位×行為型","",0,"one_from_each","まんコキ|くりコキ;くり舐め|まん舐め",2,"まんコキ/くりコキ + くり舐め/まん舐め")
Y("胸責め","部位×行為型","",0,"one_from_each","ちくび;ぱいコキ|ぱい舐め",2,"ちくび + ぱいコキ/ぱい舐め")
Y("尻開発","部位×行為型","",0,"one_from_each","あなる;けつコキ|けつ舐め|けつ穴",2,"あなる + けつコキ/けつ舐め/けつ穴")
Y("デカぱい責め","部位×行為型","",0,"one_from_each","デカぱい;ぱいコキ|ぱい舐め|ちくび",2,"デカぱい + ぱいコキ/ぱい舐め/ちくび")
Y("調教","部位×行為型","",0,"one_from_each","いじり;stem:まぞ|stem:さど",2,"いじり + まぞ系/さど系の語(穴・媚び・コキ)")
Y("三点責め","部位×行為型","",0,"one_from_each","ちくび;stem:ぱい;stem:くり",2,"ちくび + ぱいの語 + くりの語")
Y("ダブル奉仕","部位×行為型","",0,"pair_same_stem_modifiers","コキ|舐め",1,"Xコキ + X舐め(Xは同じ語幹)")
# 物語型
Y("恋人のキス","物語型","love",1,"one_from_each",f"{KISS};mod:♡",1,"キス系 + ♡の語")
Y("らぶイキ","物語型","love",2,"one_from_each",f"{KISS};mod:♡;{ZETCHO}",3,"キス系 + ♡の語 + 絶頂系","未定")
Y("フルコース","物語型","",0,"one_from_each",f"{KISS};mod:コキ|mod:舐め;{ZETCHO}",3,"キス系 + コキ・舐めの語 + 絶頂系")
Y("アクメ地獄","物語型","zetcho_chain",2,"contains_all","あくめ|いくっ|いかせ",4,"あくめ + いくっ + いかせ")
Y("オホ声","特殊牌型","oho",1,"variant_count","tile=ぉ゛;min=1",1,"ぉ゛(おの代わりになる牌)を1枚以上使ってアガる","仮")
Y("オホ声・二","特殊牌型","oho",2,"variant_count","tile=ぉ゛;min=2",2,"ぉ゛を2枚以上使ってアガる","仮")

# ======== 新しい役(語の組み合わせ型・喘ぎ声面子型・雀頭型) ========
MOAN="あんっ|ああっ|おおっ|んおっ|んんっ|うおお|あうう|うんん"
# 語の組み合わせ型
Y("二組","構造型","",0,"stem_pairs","pairs=2",3,"同じ語幹が2語ずつ2組(ちん2語+まん2語など)")
Y("二色","構造型","",0,"modifier_pairs","pairs=2",3,"修飾牌が2種類で、2語ずつ(単独語なし)")
Y("二刀流","構造型","",0,"part_pairs","pairs=2",2,"部位が2種類で、2語ずつ")
Y("前後半々","構造型","",0,"position_split","head=2;tail=2",1,"語頭の修飾牌付き2語+語尾の修飾牌付き2語")
Y("ばらばら","構造型","",0,"distinct_stems","n=4",1,"語幹が4語とも別(単独語なし)")
Y("多色","構造型","",0,"distinct_modifiers","n=4",1,"修飾牌が4語とも別(単独語なし)")
Y("つがい","ペア型","",0,"one_from_each","stem:めす;stem:おす",2,"めす系の語+おす系の語")
Y("行為づくし","カテゴリ集め型","",0,"count_in_set","min=2;set=こうび|がんしゃ|いかせ|いじり",2,"行為系の単独語が2語以上")
# 喘ぎ声の面子(3牌)
Y("喘ぎ二重唱","カテゴリ集め型","moanchorus",2,"count_in_set",f"min=2;set={MOAN}",2,"喘ぎ声の面子が2語以上")
Y("喘ぎ三重奏","カテゴリ集め型","moanchorus",3,"count_in_set",f"min=3;set={MOAN}",4,"喘ぎ声の面子が3語以上")
Y("喘ぎながら絶頂","行為→結末型","",0,"one_from_each",f"{MOAN};{ZETCHO}",2,"喘ぎ声の面子 + 絶頂系の語")
Y("キスしながら喘ぐ","物語型","kmz",1,"one_from_each",f"{KISS};{MOAN}",2,"キス系の語 + 喘ぎ声の面子")
Y("キスから絶頂まで","物語型","kmz",2,"one_from_each",f"{KISS};{MOAN};{ZETCHO}",4,"キス系 + 喘ぎ声の面子 + 絶頂系")
# 雀頭型(雀頭の語と、手の語の関係)
Y("可愛い声","雀頭型","",0,"head_flavor","flavor=可愛い系",1,"雀頭が可愛い系の喘ぎ声(あん・あっ・んっ・んあ・ああ)")
Y("獣の声","雀頭型","",0,"head_flavor","flavor=オホ声系",1,"雀頭がオホ声系の喘ぎ声(おっ・んお・おお)")
Y("同じ部位の雀頭","雀頭型","",0,"head_part_match","",1,"略称の雀頭と、同じ部位の語が手にある")
for st in [x for x in ABBR if x not in STEM_CANON]:
    Y(f"{st}一筋","雀頭型",f"headstem:{st}",1,"head_stem_match",f"stem={st};min=1",2,f"雀頭が略称「{st}」で、語幹{st}の語が手に1語以上")
    Y(f"{st}ぞっこん","雀頭型",f"headstem:{st}",2,"head_stem_match",f"stem={st};min=2",3,f"雀頭が略称「{st}」で、語幹{st}の語が手に2語以上")
# 赤ちゃんプレイ・命令語
CMD="なめろ|せめろ|あけろ|おちろ|なめな|せめな|あけな|いきな|いけっ|なけっ|さけべ|いくな"
Y("赤ちゃんプレイ","単語きっかけ型","",0,"contains_all","まま♡",2,"まま♡が入る","仮")
Y("赤ちゃんプレイ","単語きっかけ型","",0,"contains_all","ままあ",2,"ままあが入る(まま♡と同じ面子)","仮")
Y("命令口調","命令語型","cmdchorus",2,"count_in_set",f"min=2;set={CMD}",2,"命令語が2語以上")
Y("命令口調・三","命令語型","cmdchorus",3,"count_in_set",f"min=3;set={CMD}",4,"命令語が3語以上")
Y("命令と服従","命令語型","",0,"one_from_each",f"{CMD};stem:まぞ",2,"命令語 + まぞ系の語")
Y("命令どおりに","命令語型","",0,"one_from_each",f"{CMD};mod:舐め|mod:コキ",1,"命令語 + 舐め系/コキ系の語")
Y("命令違反","命令語型","",0,"one_from_each","いくな;いくっ|あくめ|しゃせい",3,"いくな(禁止)+ 絶頂系の語(イってしまう)")
# ラブ系・快感系・オナニー・女王様(各1翻・仮)
PLEASURE="きく♡|穴きく|きつく・きっく|きくう"
ONA="エロおな|おな♡|媚びおな|ぬれおな"
Y("ラブ系","ラブ・快感系","",0,"count_in_set",f"min=1;set={KISSX}",1,"すき(ラブ)に読める語(すき♡・穴すき・エロすき・ぬれすき)が入る","仮")
Y("快感系","ラブ・快感系","",0,"count_in_set",f"min=1;set={PLEASURE}",1,"きく系の語(きく♡・穴きく・きつく・きくう)が入る","仮")
Y("快感系","ラブ・快感系","",0,"head_is","head=きく",1,"雀頭がきく","仮")
Y("オナニー","行為型","",0,"count_in_set",f"min=1;set={ONA}",1,"おな系の語(エロおな・おな♡・媚びおな・ぬれおな)が入る","仮")
Y("女王様","命令語型","",0,"contains_all","おなめ",1,"おなめ(命令語)が入る","仮")
# 単語きっかけ型
Y("本番","単語きっかけ型","",0,"contains_all","こうび",1,"こうびが入る","未定")
for i,r in enumerate(yaku,1): r["id"]=f"Y{i:03d}"

# ---------------- 検証 ----------------
by = {r["word"]:r for r in words}
def expand(token):
    if token.startswith("mod:"):  return {r["word"] for r in words if token[4:] in (r.get("modifiers") or r["modifier"]).split("|")}
    if token.startswith("pos:"):  return {r["word"] for r in words if r["position"]==token[4:]}
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
_wt={t for r in words for t in r['tiles'].split('|')}
for h in heads:
    for t in h['tiles'].split('|'): assert t in _wt, ('雀頭の牌が語にない',h['head'],t)
assert len({h['head'] for h in heads})==len(heads)
assert all(r["tile_count"]==3 for r in words)
assert len(WORDSET)==len(words)
ids=[(y["group"],y["tier"]) for y in yaku if y["group"]]
assert len(ids)==len(set(ids)), "同じgroup内でtierが重複"

# ---------------- 出力 ----------------
wcols=["id","word","type","modifier","modifiers","position","stem","tiles","tile_count","part","tag","flavor","note"]
with open(os.path.join(OUT,"words.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=wcols); w.writeheader(); w.writerows(words)
ycols=["id","name","pattern","group","tier","condition_type","params","han_provisional","han_status","description"]
with open(os.path.join(OUT,"yaku.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=ycols); w.writeheader(); w.writerows(yaku)
use=Counter(); cnt=Counter()
for r in [x for x in words if x["type"]!="修飾3型"]+[dict(tiles=h["tiles"]) for h in heads]:   # 修飾牌3つの語は、枚数ルールに数えない(山が大きくなりすぎるため)
    ts=r["tiles"].split("|")
    for t in set(ts): use[t]+=1
    for t in ts: cnt[t]+=1
with open(os.path.join(OUT,"tile_usage.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["tile","used_in_words","total_occurrences_in_all_words"])
    for t,c in use.most_common(): w.writerow([t,c,cnt[t]])

with open(os.path.join(OUT,"heads.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=["id","head","tiles","type","flavor","stem","note"]); w.writeheader(); w.writerows(heads)
with open(os.path.join(OUT,"tile_variants.csv"),"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=["tile","base","copies","name","mode","note"]); w.writeheader(); w.writerows(VARIANTS)
for v in VARIANTS: assert v["base"] in {t for r in words for t in r["tiles"].split("|")}
print("雀頭:",len(heads),Counter(h["type"] for h in heads))
print("語数:",len(words), Counter(r["type"] for r in words))
print("役の行数:",len(yaku),"/ 役名の種類:",len({y['name'] for y in yaku}))
print(Counter(y["pattern"] for y in yaku))
print("牌の種類:",len(use),"/ 専用牌:",[t for t,c in use.items() if c==1])
print("頻出:",use.most_common(8))
