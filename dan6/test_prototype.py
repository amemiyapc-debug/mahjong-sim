"""試作HTML(prototype/hiragana_tap_prototype.html)の確認(依頼 C): スロット別の色・ちゅ代替の削除・320px幅に14牌。
  python3 dan6/test_prototype.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "game"))
from pw import sync_playwright, launch
URL = "file://" + os.path.abspath(os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html"))
res, errs = [], []
def ok(n, c, extra=""):
    res.append(bool(c)); print(("OK  " if c else "NG  ") + n + (" " + extra if extra else ""))
COL = ["#E6E1EA", "#FFB8D4", "#FFD3C2", "#F0A0DC", "#BFD4FF", "#CDB0F5", "#FFF0A6"]
rgb = lambda h: "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
with sync_playwright() as p:
    b = launch(p); pg = b.new_page(viewport={"width": 320, "height": 800})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    ok("読み込めて、エラーがない(語365・山361枚)", not errs and pg.evaluate("DICT.words.length")==365 and pg.evaluate("newDeck().length")==361, str(errs[:1]))
    # ちゅ→つ の代用の削除
    r = pg.evaluate("""()=>({a:!!findWord(DICT,['け','ちゅ','穴']), b:!!findWord(DICT,['け','っ','穴']), c:!!findWord(DICT,['け','つ','穴']),
        d:!!findWord(DICT,['ちゅ','っ','ちゅ']), e:okTile('ちゅ','つ'), f:okTile('っ','つ'), g:okTile('ぉ゛','お')})""")
    ok("ちゅは、つ・っの代わりにならない(け・ちゅ・穴 は けつ穴 にならない)", not r["a"] and not r["e"])
    ok("つ=っ の互換は残る(け・っ・穴 / け・つ・穴 = けつ穴)、ちゅっちゅ・ぉ゛=お も使える", r["b"] and r["c"] and r["d"] and r["f"] and r["g"])
    # 手牌を作る: 面子3(部位・行為・反応)+雀頭1+搭子1+ツモ牌 = 14牌
    pg.evaluate("""()=>{ reset(); let id=1000; const T=l=>({id:id++,label:l});
      const grp=(kind,name,labs)=>({k:'group',kind,name,text:name,tiles:labs.map(T)});
      items=[ grp('meld','ちんぽ',['ち','ん','ぽ']), grp('meld','くちゅっ',['く','ちゅ','っ']), grp('meld','デカぬれ♡',['デカ','ぬれ','♡']),
              grp('meld','あんあん',['あ','ん','×2']), grp('head','いく',['い','く']), ];
      tsumoId=items[items.length-1].tiles[1].id; render(); }""")
    n = pg.evaluate("flat().length"); ok("14牌を並べた(面子4・雀頭1・牌)", n == 14, str(n))
    geo = pg.evaluate("""()=>{ const t=document.querySelector('#hand .tile'), w=document.getElementById('handwrap'), h=document.getElementById('hand');
      const r=t.getBoundingClientRect(); const gs=[...document.querySelectorAll('#hand .grp')].map(g=>{const a=g.getBoundingClientRect(), l=g.querySelector('.lab').getBoundingClientRect(); return [a.left,a.right,l.left,l.right];});
      return {tw:r.width,th:r.height,wrapOver:w.scrollWidth>w.clientWidth+0.5,docOver:document.documentElement.scrollWidth>window.innerWidth,handW:h.scrollWidth,vw:window.innerWidth,gs}; }""")
    ok("牌が 21×30px", abs(geo["tw"] - 21) < 0.6 and abs(geo["th"] - 30) < 0.6, f"({geo['tw']:.1f}×{geo['th']:.1f})")
    ok("320px幅で、14牌+グループが、横にはみ出さない", not geo["wrapOver"] and not geo["docOver"], f"(手牌 {geo['handW']}px / 画面 {geo['vw']}px)")
    ok("グループのラベルが、グループ幅を超えない・隣と重ならない", all(g[2] >= g[0] - 0.5 and g[3] <= g[1] + 0.5 for g in geo["gs"]) and all(geo["gs"][i][1] <= geo["gs"][i + 1][0] + 0.5 for i in range(len(geo["gs"]) - 1)))
    cols = pg.evaluate("""()=>[...document.querySelectorAll('#hand .grp.meld')].map(g=>getComputedStyle(g.querySelector('.tile')).backgroundColor)""")
    ok("完成した面子の牌が、スロット別の色(ちんぽ=部位 #FFD3C2 / くちゅっ=音 #BFD4FF / デカぬれ♡=前置き #E6E1EA / あんあん=喘ぎ声 #FFF0A6)",
       cols == [rgb(COL[2]), rgb(COL[4]), rgb(COL[0]), rgb(COL[6])], str(cols))
    pg.evaluate("""()=>{ let id=2000; const T=l=>({id:id++,label:l}); const grp=(kind,name,labs)=>({k:'group',kind,name,text:name,tiles:labs.map(T)});
      items=[ grp('meld','ちんぽ',['ち','ん','ぽ']), grp('meld','くちゅっ',['く','ちゅ','っ']), grp('meld','デカぬれ♡',['デカ','ぬれ','♡']), grp('head','いく',['い','く']),
              {k:'tile',tile:T('き')}, {k:'tile',tile:T('エロ')}, {k:'tile',tile:T('ぉ゛')}]; tsumoId=items[items.length-1].tile.id; render(); }""")
    ok("(未完成の牌の確認用)14牌: 面子3・雀頭1・牌3", pg.evaluate("flat().length")==14 and not pg.evaluate("document.getElementById('handwrap').scrollWidth>document.getElementById('handwrap').clientWidth+0.5"))
    loose = pg.evaluate("""()=>[...document.querySelectorAll('#hand > .tile')].map(t=>getComputedStyle(t).backgroundColor)""")
    hd = pg.evaluate("""()=>getComputedStyle(document.querySelector('#hand .grp.head .tile')).backgroundColor""")
    ok("未完成の牌・雀頭は、色が付かない(白いまま)", len(set(loose)) == 1 and loose[0] == hd and loose[0] not in [rgb(c) for c in COL], loose[0])
    # 搭子のラベル重複・リストの不一致(つ=っ・ぉ゛=お は同じ牌)
    r = pg.evaluate("""()=>{ reset(); let id=3000; const T=l=>({id:id++,label:l});
      items=['エロ','お','ぉ゛','い','く','っ','つ','き','す','け','ち','ん','ろ','あ'].map(l=>({k:'tile',tile:T(l)})); tsumoId=null; render();
      const nz=x=>x==='っ'?'つ':(x==='ぉ゛'?'お':x); const H=computeHints();
      const keys=H.dazis.map(d=>d.tiles.map(t=>nz(t.label)).sort().join('|'));
      return {n:H.dazis.length, dupKeys:keys.length-new Set(keys).size, dupWaits:H.dazis.filter(d=>d.waits.some(w=>w==='っ'||w==='ぉ゛')||new Set(d.waits).size!==d.waits.length).length,
        remainOk:H.dazis.every(d=>d.remain===deck.filter(t=>d.waits.some(w=>okTile(t,w))).length), sorted:H.dazis.every((d,i,a)=>i===0||a[i-1].remain>=d.remain), top:H.dazis.slice(0,3).map(d=>d.tiles.map(t=>t.label).join('+')+' 待ち'+d.waits.join('・')+' 残'+d.remain)}; }""")
    ok("搭子の候補に、同じ牌の組(エロ+お と エロ+ぉ゛ など)の重複がない", r["n"] > 0 and r["dupKeys"] == 0, str(r["top"]))
    ok("搭子の待ち牌が、つ・っ/お・ぉ゛ で重複しない。残り枚数は、待ち牌(互換を含む)の山の枚数と一致し、多い順", r["dupWaits"] == 0 and r["remainOk"] and r["sorted"])
    # ---- dan6 の追加 ----
    html = open(os.path.join(ROOT, "prototype", "hiragana_tap_prototype.html"), encoding="utf-8").read()
    ok("はじめての語ボーナスが、どこにもない(計算・表示・演出カード・保存データ)", "newWords" not in html and "はじめての語" not in html and "NEW</span>" not in html)
    f = pg.evaluate("()=>[fmtPts(500),fmtPts(12345),fmtPts(99999),fmtPts(32e8),fmtPts(77e12),fmtPts(1e17),fmtPts(123e8)]")
    ok("大きな点の表示(万・億・兆・京)", f == ["500", "1.2万", "9.9万", "32億", "77兆", "10京", "123億"], str(f))
    r = pg.evaluate("""()=>{ localStorage.removeItem(HI_KEY); const a=updateHi(8000), b=updateHi(5000), c=updateHi(12000); return [a,b,c,loadHi()]; }""")
    ok("ハイスコアが記録され、高い点でだけ更新される", r[0]["hi"]==8000 and not r[1]["isNew"] and r[1]["hi"]==8000 and r[2]["hi"]==12000 and r[3]==12000, str(r))
    # 14牌のアガリ手を作って、アガリ画面(evalWin)に、ボーナス行・NEW が出ず、ハイスコアが出る
    pg.evaluate("""()=>{ reset(); localStorage.removeItem(HI_KEY); let id=5000; const T=l=>({id:id++,label:l});
      const grp=(kind,name,labs)=>({k:'group',kind,name,text:name,tiles:labs.map(T)});
      items=[ grp('meld','ちんぽ',['ち','ん','ぽ']), grp('meld','ぬれまん',['ぬれ','ま','ん']), grp('meld','ぱこぱこ',['ぱ','こ','×2']), grp('meld','いくう',['い','く','う']), grp('head','あん',['あ','ん']) ]; tsumoId=items[items.length-1].tiles[1].id; render(); }""")
    r = pg.evaluate("()=>{ won={kept:0,total:5,data:null}; try{ const d=evalWin(); return {ok:true,total:d.total,hi:d.hi,html:(()=>{won={data:d,kept:0,total:0};return winHTML();})(),own:d.own.sc.total}; }catch(e){return {ok:false,err:String(e)}} }")
    ok("evalWin がエラーなく動く(辞書365語)", r["ok"], str(r)[:200])
    if r["ok"]:
        ok("アガリ画面: ボーナス行なし・翻=役の合計(裏読み込み)・ハイスコア表示", "はじめての" not in r["html"] and "ハイスコア" in r["html"] and r["total"]>=r["own"], str(r["total"]) + "翻")
    # Python(yaku14.py)と、試作HTMLの判定の照合: 同じ14牌で、最大翻・成立した役が一致するか
    import random, itertools, csv, collections
    sys.path.insert(0, ROOT)
    from yaku14 import Scorer
    S = Scorer(HERE)
    rng = random.Random(20261007)
    def mk(ws, h):
        t = []
        for i in ws: t += S.W[i]["tiles"].split("|")
        t += S.H[h]["tiles"].split("|")
        return t
    hands = [mk(rng.sample(range(len(S.W)), 4), rng.randrange(len(S.H))) for _ in range(400)]
    # 役が付きやすい手も混ぜる: 同じ部位・同じ語幹を多めに
    byslot = collections.defaultdict(list)
    for i, w in enumerate(S.W): byslot[w["part"]].append(i)
    for part, ids in byslot.items():
        if len(ids) >= 4 and part:
            for _ in range(40): hands.append(mk(rng.sample(ids, 4), rng.randrange(len(S.H))))
    py = []
    for hnd in hands:
        r_ = S.best(hnd); py.append(None if not r_ else [r_["han"], sorted(set(r_["yaku"]))])
    js = pg.evaluate("""(hands)=>hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
        for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true); if(!best||sc.total>best.total)best={total:sc.total,names:sc.items.map(x=>x.name)}; }
        return best; })""", hands)
    cmp_ = lambda: [(i, py[i], js[i]) for i in range(len(hands)) if (py[i] is None) != (js[i] is None) or (py[i] and js[i] and py[i][0] != js[i]["total"])]
    bad0 = cmp_()
    print(f"   [確認事項] 試作HTMLの構造型3役(二色・ばらばら・多色)は、game/core.js・yaku14.py と判定が違う(修飾3型の語の扱い)。そのままの不一致: {len(bad0)}/{len(hands)}手")
    # 構造型3役を、core.js / yaku14.py と同じ判定に差し替えて照合(これ以外の役・分割・合体・翻の選択が、Python と完全一致するかの確認)
    js = pg.evaluate("""(hands)=>{ const ST=['distinct_stems','distinct_modifiers','modifier_pairs'];
      for(const r of YR){ if(!ST.includes(r.ct))continue; const y=DATA.Y.find(x=>x[0]===r.name); const kv=kvOf(y[4]);
        if(r.ct==='distinct_stems')r.f=(ws,hd,full)=>full&&ws.every(w=>WA[w].stem)&&new Set(ws.map(w=>WA[w].stem)).size===4;
        if(r.ct==='distinct_modifiers')r.f=(ws,hd,full)=>{if(!full||!ws.every(w=>WA[w].mods.length>=1))return false;const tk=[];ws.forEach(w=>WA[w].mods.forEach(m=>tk.push(m)));return new Set(tk).size===tk.length;};
        if(r.ct==='modifier_pairs')r.f=(ws,hd,full)=>{if(!full||!ws.every(w=>WA[w].mods.length===1))return false;const c={};ws.forEach(w=>{const m=WA[w].mods[0];c[m]=(c[m]||0)+1;});return Object.values(c).filter(v=>v===2).length===+kv.pairs;};
      }
      return hands.map(h=>{ const parts=allPartitions(DICT,h,500); let best=null; const oho=h.filter(l=>l==='ぉ゛').length;
        for(const p of parts){ const ws=p.melds.map(m=>WI.get(m.word.name)),hd=HI.get(p.head.name); const sc=scoreHand(ws,hd,oho,true); if(!best||sc.total>best.total)best={total:sc.total,names:sc.items.map(x=>x.name)}; }
        return best; }); }""", hands)
    bad = cmp_()
    ok(f"構造型3役を同じ判定にすると、Python(yaku14.py)と試作HTMLの最大翻が一致({len(hands)}手)", not bad, f"(不一致 {len(bad)}: {bad[:2]})")
    covered = set(y for p_ in py if p_ for y in p_[1])
    print("   照合した手で成立した役の種類:", len(covered), "/ 87")
    pg.screenshot(path="/tmp/proto_320.png")
    b.close()
print("エラー:", errs or "なし"); print("すべてOK" if all(res) and not errs else "失敗")
sys.exit(0 if all(res) and not errs else 1)
