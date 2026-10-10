"""試作HTMLへの追加(20261010-1925 作業6): エンディング。make_prototype.py から apply(s)。適用済み(/* dan6:h */)なら飛ばす。"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
ENDJS = open(os.path.join(HERE, "proto_end.js"), encoding="utf-8").read()
CSS = '''#ending{position:fixed;inset:0;z-index:55;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(8,10,14,.97);padding:12px;color:#fff;text-align:center}
#ending[hidden]{display:none}
#en-face{width:92px;height:92px;border-radius:14px;display:flex;align-items:center;justify-content:center;white-space:pre-line;font-size:.62rem;font-weight:800;color:#2a1a1a;border:3px solid #fff;margin-bottom:10px;transition:background .25s;line-height:1.3}
#en-pane{width:100%;max-width:440px;min-height:250px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.en-word{font-size:2.4rem;font-weight:900;color:#ffd43b;text-shadow:0 0 14px #ff9f1a}.en-role{font-size:.8rem;color:#9fb3ad}
.en-line{font-size:1.1rem;font-weight:800;line-height:1.6;color:#ffe3ea}.en-cap{font-size:.8rem;color:#9fb3ad}
#en-total{font-size:2.2rem;color:#ffd43b;text-shadow:0 0 12px #ff9f1a;font-variant-numeric:tabular-nums}
#ending .sh-btns{margin-top:12px}
'''
HTML = '''<div id="ending" hidden><div id="en-face"></div><div id="en-pane"></div><div class="sh-btns"><button class="b" id="en-skip">スキップ</button><button class="b" id="en-next" hidden>2周目へ</button></div></div>
'''


def apply(s):
    if "/* dan6:h */" in s:
        return s

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6h パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    sub1("function itemsHTML(sc){", ENDJS + "function itemsHTML(sc){")
    sub1('<div id="show" hidden>', HTML + '<div id="show" hidden>')
    sub1('$$("sh-close").onclick=()=>{$$("show").hidden=true;};', '$$("sh-close").onclick=()=>{$$("show").hidden=true;maybeEnding();};\n$$("en-skip").onclick=()=>{endJump=true;};\n$$("en-next").onclick=()=>{endToLap2();};')
    # 1周目で END_STAGE をクリアしたら、エンディング(アガリ演出のあと)
    sub1('if(STG.wins>=need){const done=STG.stage;STG.stage++;m+=" → ステージ"+done+"クリア!";newTry();}',
         'if(STG.wins>=need){const done=STG.stage;STG.stage++;m+=" → ステージ"+done+"クリア!";newTry();if(done===END_STAGE){pendingEnding=true;m+=" → 1周目クリア! エンディングへ";}}')
    # 演出なし(SHOW=OFF)のときは、アガリ画面のあとすぐ
    sub1("won.data=evalWin();render();renderIngo();refreshStar();playShow().catch(()=>{showRunning=false;});", "won.data=evalWin();render();renderIngo();refreshStar();if(SHOW)playShow().catch(()=>{showRunning=false;});else setTimeout(maybeEnding,400);")
    sub1(".sh-btns[hidden]{display:none}", ".sh-btns[hidden]{display:none}\n" + CSS)
    s = s.replace("/* dan6:g */", "/* dan6:g *//* dan6:h */", 1)
    return s
