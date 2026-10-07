# words.csv / yaku.csv / heads.csv / tile_variants.csv から、ゲーム用の data.json を作る
import csv, json, os
HERE=os.path.dirname(os.path.abspath(__file__))
# 入力CSV(既定: ../v13m。環境変数 HM_DATA_DIR で変える)
D=os.environ.get("HM_DATA_DIR", os.path.join(HERE,"..","v13m"))+"/"
rd=lambda n: list(csv.DictReader(open(D+n,encoding="utf-8-sig")))
W,Y,Hd,V=rd("words.csv"),rd("yaku.csv"),rd("heads.csv"),rd("tile_variants.csv")
M=rd("yaku_merge.csv") if os.path.exists(D+"yaku_merge.csv") else []   # 合体役(CLAUDE.md §6-7)
data={"words":[{k:w[k] for k in ("word","type","modifier","modifiers","position","stem","tiles","part","tag","flavor")+(("slot_no",) if "slot_no" in w else ())} for w in W],
      "yaku":[{k:y[k] for k in ("name","group","tier","condition_type","params","han_provisional")} for y in Y],
      "heads":[{k:h[k] for k in ("head","tiles","type","flavor","stem")} for h in Hd],
      "variants":[{k:v[k] for k in ("tile","base","copies","name","mode")} for v in V],
      "merges":[{k:m[k] for k in ("name","source_yaku","han_provisional","level")} for m in M],
      "options":{"triplesOutOfDeckRule":True,"tileRule":os.environ.get("HM_TILE_RULE","new"),"merges":True,
                 "modx":float(os.environ.get("HM_MODX","0.1")),"fixed":({"×2":int(os.environ.get("HM_X2","13"))} if any("×2" in w["tiles"].split("|") for w in W) else {})}}
json.dump(data,open("data.json","w",encoding="utf-8"),ensure_ascii=False); print("data.json 語",len(W),"役",len(Y),"雀頭",len(Hd),"変種",len(V),"合体",len(M))
