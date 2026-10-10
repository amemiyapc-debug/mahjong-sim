"""手牌固定の確認(20261010-1925 作業1): 自分で組んだ面子・搭子・雀頭は、その形のまま確定する。画面を実際にクリックして確認する。
  a. 面子4つ+ばらの1牌に和了牌が来て雀頭になる / b. 面子3つ+搭子2つで、和了牌で一方が完成し、他方が雀頭になる(どちらの完成でも)
  c. 何も組まずに14牌目が来る / d. 分け方が複数ある手(自分の組んだ形が、解読点最大でなくても、その形のまま) / e. 組んだ形を壊さないとアガれない場合だけ、組み替えて、そう表示する
  python3 dan6/test_hold.py [html]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "game"))
from pw import sync_playwright, launch
HTML = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html")
URL = "file://" + os.path.abspath(HTML)
SHOTS = os.path.join(ROOT, "results_dan6", "shots"); os.makedirs(SHOTS, exist_ok=True)
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
SETUP = """([dk,labels])=>{ STG.stage=1; STG.game=1; STG.lives=3; STG.streak=0; STG.msg=''; newTry(); dealRandom(); items=labels.map(l=>({k:'tile',tile:mk(l)})); deck=dk.slice(); draws=0; won=null; over=false; choice=false; skipMode=false; pendingWin=null; skipCount=0; tsumoId=null; sel=[]; render(); return flat().length; }"""
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    def tap(label):   # ばらの牌(グループに入っていない)を、画面でクリックする
        i = pg.evaluate("""(l)=>{const t=[...document.querySelectorAll('#hand > .tile:not(.sel)')].find(x=>x.textContent===l);return t?+t.dataset.id:null;}""", label)
        assert i is not None, "牌がない: " + label
        pg.click(f'#hand > .tile[data-id="{i}"]')
    def make(kind, labels):
        for l in labels: tap(l)
        if kind == "dazi": pg.click('[data-a="dazi"]')
        elif kind == "head": pg.click('[data-a="head"]')
    def finish():   # ツモして、見送りの選択が出たら「アガる」を押す
        pg.evaluate("()=>draw()"); pg.wait_for_timeout(150)
        if pg.evaluate("()=>choice"): pg.click('[data-a="agaru"]'); pg.wait_for_timeout(150)
        pg.wait_for_timeout(400)
        return pg.evaluate("()=>({won:!!won, melds:won&&won.melds, head:won&&won.head, kept:won&&won.kept, user:won&&won.user, rearr:won&&won.rearr, html:document.getElementById('win').innerHTML})")
    W13 = ['ち', 'ん', 'ぽ', 'ぬれ', 'ま', 'ん', 'ぱ', 'こ', '×2', 'い', 'く', 'あ']      # ちんぽ・ぬれまん・ぱこぱこ・(い,く)・(あ)。13牌目と14牌目で いくう と あん
    # a. 面子4つ(いくう はツモの前に う を持つ形ではなく、いくう の ち)... 面子3つ+ばらの いく+あ、ではなく: 面子4つ=ちんぽ・ぬれまん・ぱこぱこ・いくう、ばら=あ、和了牌=ん → 雀頭あん
    pg.evaluate(SETUP, [["ん"], W13 + ["う"]]); 
    for grp in (["ち", "ん", "ぽ"], ["ぬれ", "ま", "ん"], ["ぱ", "こ", "×2"], ["い", "く", "う"]): make("meld", grp)
    ok("a. 面子4つ+ばらの1牌 → 和了牌(ん)で雀頭あんになる。組んだ面子4つは、そのまま", pg.evaluate("flat().length") == 13)
    r = finish(); pg.screenshot(path=os.path.join(SHOTS, "hold_a.png"))
    ok("a. 結果: 面子4つがそのまま(kept=4)、雀頭は あん、組み替えなし", r["won"] and r["kept"] == 4 and r["head"] == "あん" and not r["rearr"] and "組み替えました" not in r["html"], str(r)[:200])
    # b1. 面子3つ+搭子(い,く)+搭子(あ,ん)。和了牌(う)で いくう が完成し、(あ,ん)はそのまま雀頭
    pg.evaluate(SETUP, [["う"], ["ち", "ん", "ぽ", "ぬれ", "ま", "ん", "ぱ", "こ", "×2", "い", "く", "あ", "ん"]])
    for grp in (["ち", "ん", "ぽ"], ["ぬれ", "ま", "ん"], ["ぱ", "こ", "×2"]): make("meld", grp)
    make("dazi", ["い", "く"]); make("dazi", ["あ", "ん"])
    ok("b. 面子3つ+搭子2つが、画面で組めた(グループ5つ)", pg.evaluate("items.filter(i=>i.k==='group').length") == 5 and pg.evaluate("items.filter(i=>i.k==='group'&&i.kind==='dazi').length") == 2)
    r = finish(); pg.screenshot(path=os.path.join(SHOTS, "hold_b.png"))
    ok("b. 結果: 搭子(い,く)は いくう に完成し、搭子(あ,ん)は雀頭あんになる。5つとも、そのまま(kept=5・組み替えなし)", r["won"] and r["kept"] == 5 and r["user"] == 5 and r["head"] == "あん" and any("いくう" in m for m in r["melds"]) and not r["rearr"], str(r)[:220])
    # b2. 搭子(あ,ん)が雀頭ではなく面子になる形 ...(あんあん は あ,ん,×2)。面子3つ(ちんぽ・ぬれまん・いくう)+搭子(ぱ,こ)+搭子(×2,あ)... は固定の対象が増えるため、b1 の入れ替えで確認する
    pg.evaluate(SETUP, [["×2"], ["ち", "ん", "ぽ", "ぬれ", "ま", "ん", "い", "く", "う", "あ", "ん", "ぱ", "こ"]])
    for grp in (["ち", "ん", "ぽ"], ["ぬれ", "ま", "ん"], ["い", "く", "う"]): make("meld", grp)
    make("dazi", ["ぱ", "こ"]); make("dazi", ["あ", "ん"])
    r = finish()
    ok("b'. 面子3つ+搭子(ぱ,こ)+搭子(あ,ん)。和了牌(×2)で ぱこぱこ が完成し、搭子(あ,ん)は雀頭。そのまま", r["won"] and r["kept"] == 5 and r["head"] == "あん" and any("ぱこぱこ" in m for m in r["melds"]) and not r["rearr"], str(r)[:220])
    # c. 何も組まずに14牌目が来る
    pg.evaluate(SETUP, [["ん"], W13 + ["う"]])
    r = finish()
    ok("c. 何も組まずに14牌目 → 自動で組む(kept=0)。組み替えの表示は出ない", r["won"] and r["kept"] == 0 and r["user"] == 0 and not r["rearr"] and "組み替えました" not in r["html"], str(r)[:200])
    # d. 分け方が複数ある手: 自分で組んだ形(解読点が最大でない分け方の面子2つ)が、そのまま確定する。手は、この辞書から探す(語の集合に依存しない)
    pg.evaluate("()=>{LAP=3;}")   # 3周目(研究♡2)にして、分け方ごとの解読点に差が出るようにする(1周目は500固定で、最大かどうかが決まらない)
    plan = pg.evaluate("""()=>{ let seed=12345;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;};const lv=lvOf(STG.stage);
      for(let k=0;k<4000;k++){
        const ws=[];while(ws.length<4){const w=DICT.words[Math.floor(rnd()*DICT.words.length)];if(!ws.includes(w))ws.push(w);}
        const hd=DICT.heads[Math.floor(rnd()*DICT.heads.length)];let labels=[];ws.forEach(w=>labels.push(...w.tiles));labels.push(...hd.tiles);
        const tsumo=labels[labels.length-1];const parts=allPartitions(DICT,labels,2000);if(parts.length<3)continue;
        const oho=labels.filter(l=>l==='ぉ゛').length;
        const pts=parts.map(p=>{const w2=p.melds.map(m=>WI.get(m.word.name)),h2=HI.get(p.head.name),sc=scoreHand(w2,h2,oho,true);return g6score(w2.map(w=>DICT.words[w].name),DICT.heads[h2].name,lv,sc.yin).points;});
        const mx=Math.max(...pts);
        for(let i=0;i<parts.length;i++){if(pts[i]===mx)continue;
          const ms=parts[i].melds.filter(m=>m.assigned.every(l=>nz(l)!==nz(tsumo)));   // 和了牌(最後の牌)を含まない面子
          if(ms.length>=2)return {hand:labels,tsumo,melds:ms.slice(0,2).map(m=>m.assigned.slice()),names:ms.slice(0,2).map(m=>m.word.name),n:parts.length,pts:pts[i],max:mx};}
      }
      return null; }""")
    ok("d. 分け方が複数ある手で、解読点が最大でない分け方の面子2つを選べた", plan is not None and plan["n"] >= 3 and plan["pts"] < plan["max"], str(plan)[:200])
    H13 = plan["hand"][:-1]
    pg.evaluate(SETUP, [[plan["tsumo"]], H13])
    for m in plan["melds"]: make("meld", m)
    r = finish(); pg.screenshot(path=os.path.join(SHOTS, "hold_d.png"))
    got = pg.evaluate("()=>won&&won.melds") or []
    ok("d. 結果: 自分で組んだ2つの面子が、そのまま残る(最大の分け方に組み替えない)。kept=2・組み替えなし", r["won"] and r["kept"] == 2 and not r["rearr"] and all(any(nm == g or nm.split("・")[0] == g.split("・")[0] for g in got) for nm in plan["names"]), str(r)[:200] + str(plan["names"]) + str(got))
    # e. 組んだ形を壊さないとアガれない場合だけ、組み替える(表示あり)
    pg.evaluate(SETUP, [[plan["tsumo"]], H13])
    bad = pg.evaluate("""(ts)=>{ const labels=flat().map(t=>t.label).concat([ts]),parts=allPartitions(DICT,labels,2000),inAny=new Set();parts.forEach(p=>p.melds.forEach(m=>inAny.add(m.word.name)));
      const L=flat().map(t=>t.label);
      for(let a=0;a<L.length;a++)for(let b=a+1;b<L.length;b++)for(let c=b+1;c<L.length;c++){const tr=[L[a],L[b],L[c]],r=findWord(DICT,tr,new Set());if(r&&!inAny.has(r.word.name))return {labels:tr,name:r.word.name};}
      return null; }""", plan["tsumo"])
    ok("e. どの分け方にも入らない語(組むと、アガれなくなる面子)が、この手にある", bad is not None, str(bad))
    if bad:
        make("meld", bad["labels"])
        r = finish(); pg.screenshot(path=os.path.join(SHOTS, "hold_e.png"))
        ok("e. 結果: 組んだ形を壊さないとアガれないので組み替える。「組み替えました」と、解いた形と新しい語を出す(kept<user)", r["won"] and r["user"] == 1 and r["kept"] == 0 and "組み替えました" in r["html"] and r["rearr"] and r["rearr"].startswith("面子「"), r["rearr"])
    ok("ページエラーがない", not errs, str(errs[:1]))
    b.close()
print("すべてOK" if all(res) else "失敗"); sys.exit(0 if all(res) else 1)
