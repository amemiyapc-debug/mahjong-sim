# template.html + data.json + core.js + ui.js から、1つのHTMLを作る。
#   出力先: 環境変数 HM_OUT_DIR(既定 /mnt/user-data/outputs。なければ ./out)
import os
HERE=os.path.dirname(os.path.abspath(__file__))
rd=lambda n: open(os.path.join(HERE,n),encoding="utf-8").read()
out=rd("template.html").replace("__DATA__",rd("data.json")).replace("__CORE__",rd("core.js")).replace("__UI__",rd("ui.js"))
d=os.environ.get("HM_OUT_DIR","/mnt/user-data/outputs")
if not os.path.isdir(d): d=os.path.join(HERE,"out"); os.makedirs(d,exist_ok=True)
p=os.path.join(d,"hiragana-mahjong-test.html")
open(p,"w",encoding="utf-8").write(out); print(p,len(out))
