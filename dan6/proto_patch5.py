"""試作HTMLへの追加(20261010-1925 作業3): アガリ演出を段階ごとの画面に作り直す(proto_show2.js)。make_prototype.py から apply(s)。適用済み(/* dan6:e */)なら飛ばす。"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
SHOW2 = open(os.path.join(HERE, "proto_show2.js"), encoding="utf-8").read()

CSS = '''.sh-btns[hidden]{display:none}
#sh-stage{font-size:.7rem;color:#9fb3ad;letter-spacing:.1em;min-height:1.2em;margin-bottom:4px}
#sh-pane{min-height:330px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;opacity:0}
#sh-pane.in{opacity:1;transition:opacity .25s}
.sh-big{font-size:2.6rem;font-weight:900;color:#ffd43b;text-shadow:0 0 14px #ff9f1a}
.stone.big{width:100%;min-height:260px;display:flex;align-items:center;justify-content:center;box-sizing:border-box;transition:min-height .7s,padding .7s}
.stone.big .tw{text-align:center;width:100%;min-height:0;word-break:keep-all;white-space:normal;transition:font-size .7s}
.stone.big.shrunk{min-height:44px;padding:6px 8px}
.stone.mosaic .tw{filter:url(#mos)}
.sh-words{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;transition:opacity .6s}.sh-words.hid{opacity:0}
.sh-words .sw{padding:6px 10px;border-radius:8px;color:#1d1b17;font-weight:900;font-size:1rem}.sh-words .sw.hd{background:#fff}
.sh-phrase .pb{padding:14px 16px;border-radius:12px;background:linear-gradient(135deg,#3a1d5c,#7a2a74);border:2px solid #f15bb5;color:#fff;font-weight:800;font-size:1.05rem;line-height:1.5;box-shadow:0 0 18px #c94ad899}
.sh-list{width:100%}.sh-li{padding:8px 12px;margin:4px 0;border-radius:10px;background:#2a2342;color:#fff;font-weight:800;animation:pop .3s;text-align:left}.sh-li b{color:#ffd43b;float:right}
.sh-sum{font-size:1.5rem;font-weight:900;color:#f15bb5;text-shadow:0 0 10px #c94ad8}
.sh-graph2{position:relative;width:100%;height:170px;border-radius:12px;background:rgba(155,93,229,.08);transition:box-shadow .3s,background .3s}
.sh-graph2 svg{position:absolute;inset:0;width:100%;height:100%}
.sh-graph2 .nd{position:absolute;transform:translate(-50%,-50%);padding:2px 6px;border-radius:8px;background:#1b1530;color:#efe6ff;border:2px solid #6b4fa0;font-weight:800;font-size:.8rem;white-space:nowrap}
.sh-graph2 .nd.on{border-color:var(--pc,#c77dff);box-shadow:0 0 12px var(--pc,#c77dff);background:#2a1b4d}
.sh-graph2 .nd.near{animation:near .3s}
.sh-total2 .reel{font-size:2.1rem;color:#ffd43b;text-shadow:0 0 12px #ff9f1a;font-variant-numeric:tabular-nums;max-width:100%;white-space:nowrap}
.sh-base .reel{font-size:2.2rem;color:#ffd43b;text-shadow:0 0 12px #ff9f1a}
.sh-mosaic{font-size:1.8rem;font-weight:900;letter-spacing:.08em;color:#c9b8ff;font-variant-numeric:tabular-nums;margin:6px 0;text-shadow:0 0 8px #7b2cbf}
.sh-result .reel.big{font-size:2rem;color:#ffd43b;text-shadow:0 0 12px #ff9f1a;white-space:nowrap}
.sh-break{margin-top:8px;font-size:.95rem;color:#e8e2ff;line-height:1.7}.sh-st{margin-top:6px;color:#9fb3ad}
'''
SVGDEF = '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><filter id="mos" x="0" y="0" width="100%" height="100%"><feFlood x="1" y="1" width="1" height="1"/><feComposite width="3" height="3"/><feTile result="t"/><feComposite in="SourceGraphic" in2="t" operator="in"/><feMorphology operator="dilate" radius="1.5"/></filter></svg>\n'
SHOWHTML = '''<div id="show" hidden><div class="sh-box" id="shbox">
 <div id="sh-stage"></div>
 <div id="sh-pane"></div>
 <div class="sh-btns" id="sh-ingo" hidden><button class="b" id="sh-star">☆ 傑作にする</button><button class="b" id="sh-copy">コピー</button></div>
 <div class="sh-btns"><button class="b" id="sh-skip">スキップ</button><button class="b" id="sh-close" hidden>とじる</button></div>
</div></div>
'''
HANDLERS = '''$$("sh-skip").onclick=()=>{showJump=true;};
(function(){let tm=null;const R=$$("show");
  R.addEventListener("pointerdown",e=>{if(!showRunning||e.target.closest("button"))return;tm=setTimeout(()=>{showJump=true;},600);});   // 長押し: リザルトへ
  const clr=()=>{if(tm){clearTimeout(tm);tm=null;}};R.addEventListener("pointerup",clr);R.addEventListener("pointercancel",clr);R.addEventListener("pointerleave",clr);
  R.addEventListener("click",e=>{if(showRunning&&!showJump&&!e.target.closest("button"))showFF=true;});})();   // タップ: いまの段階を早送り
'''


def apply(s):
    if "/* dan6:e */" in s:
        return s

    def region(start, end, new):
        nonlocal s
        i0 = s.index(start); i1 = s.index(end, i0)
        s = s[:i0] + new + s[i1:]

    def sub1(old, new):
        nonlocal s
        assert old in s, "dan6e パッチが当たらない: " + old[:70]
        s = s.replace(old, new, 1)

    region("async function playShow(){", "/* /dan6:show */", SHOW2 + "\n")
    region('<div id="show" hidden>', "<script>", SVGDEF + SHOWHTML)
    sub1('$$("sh-skip").onclick=()=>{skipShow=true;$$("show").classList.add("noanim");};\n$$("show").addEventListener("click",e=>{if(showRunning&&!showJump&&!e.target.closest("button")){skipShow=true;$$("show").classList.add("noanim");}});\n'
         if False else '$$("sh-skip").onclick=()=>{skipShow=true;$$("show").classList.add("noanim");};', HANDLERS)
    region('$$("show").addEventListener("click",e=>{if(showRunning&&!e.target.closest("button")){', '$$("sh-close").onclick=', "")
    sub1("ura,total,gs,lv:lvNow,", "ura,total,gs,gsReal:(lvNow===0?g6score(ws.map(w=>DICT.words[w].name),DICT.heads[hd].name,1,total):gs),lv:lvNow,")
    sub1("#shflash{position:fixed", CSS + "#shflash{position:fixed")
    s = s.replace("/* dan6:d */", "/* dan6:d *//* dan6:e */", 1)
    return s
