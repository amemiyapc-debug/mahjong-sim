// ひらがな麻雀(仮) テストプレイ版: ゲームの中身(画面に依存しない部分)
// アガリ形: 別々の4語(12牌) + 雀頭(2牌の語) = 14牌
(function(root){
"use strict";
const MOD_ORDER=["見せ","デカ","エロ","ぬれ","穴","媚び","♡","舐め","コキ"];
const KANA="あいうえおかがきぎくぐけげこごさざしじすずせぜそぞただちぢつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもやゆよらりるれろわをんっ";
const PARTS4=["男性器","女性器","胸","後ろ"];
const TAIL=new Set(["穴","媚び","♡","舐め","コキ"]);
const DISPLAY={"見せ":["見","せ"],"デカ":["デ","カ"],"エロ":["エ","ロ"],"ぬれ":["ぬ","れ"],"コキ":["コ","キ"],"舐め":["舐","め"],"媚び":["媚","び"],"しゃ":["し","ゃ"],"ちゅ":["ち","ゅ"]};
function pointsFor(han,table){
  if(table==="x"||han<=4) return han*1000;
  if(han===5) return 8000; if(han<=7) return 12000; if(han<=10) return 16000; if(han<=12) return 24000; return 32000;
}
function tileKey(t){
  const m=MOD_ORDER.indexOf(t); if(m>=0) return 100+m;
  if(t==="しゃ"||t==="ちゅ") return 500+(t==="しゃ"?0:1);
  if(t==="ぉ゛") return 200+KANA.indexOf("お")+0.5;
  const k=KANA.indexOf(t); return k>=0? 200+k : 450;
}
function sortHand(h){ return h.slice().sort((a,b)=>tileKey(a)-tileKey(b)); }
function shuffle(a,rng){ rng=rng||Math.random; for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1)); [a[i],a[j]]=[a[j],a[i]];} return a; }
const mkNeed=tiles=>{ const need={}; tiles.forEach(t=>need[t]=(need[t]||0)+1); return need; };

function setup(data){
  const VARS=(data.variants||[]).map(v=>({tile:v.tile,base:v.base,copies:+v.copies,mode:v.mode||"replace"}));
  const VAR={}; VARS.filter(v=>v.mode==="replace").forEach(v=>VAR[v.tile]=v.base);   // ぉ゛ → お(語・雀頭では、おとして扱う)
  const FLEX=VARS.filter(v=>v.mode==="flex");                                         // ちゅ: ちゅとしても、つとしても使える(つは、ちゅの代わりにならない)
  const norm=t=>VAR[t]||t;
  const mergeWall=wc=>{ const w2=Object.assign({},wc); VARS.forEach(v=>{ w2[v.base]=(w2[v.base]||0)+(wc[v.tile]||0); }); return w2; };
  // 手牌を、変種の使い方ごとに展開(ちゅ を b 枚だけ つ として使う、b=0..)。位置は変えない
  function handVariants(hand){
    const base=hand.map(norm), out=[base];
    FLEX.forEach(f=>{ const P=[]; base.forEach((t,i)=>{ if(t===f.tile) P.push(i); });
      for(let b=1;b<=P.length;b++){ const arr=base.slice(); for(let k=0;k<b;k++) arr[P[k]]=f.base; out.push(arr); } });
    return out;
  }
  const countsOf=arr=>{ const c={}; arr.forEach(t=>c[t]=(c[t]||0)+1); return c; };
  const W=data.words.map((w,i)=>{ const tiles=w.tiles.split("|"), need=mkNeed(tiles.map(norm));
    return {i,word:w.word,type:w.type,modifier:w.modifier,mods:(w.modifiers||w.modifier||"").split("|").filter(Boolean),position:w.position||"",stem:w.stem,part:w.part,tag:w.tag||"",flavor:w.flavor||"",tiles,need,kinds:Object.keys(need),rawKinds:[...new Set(tiles)]}; });
  const idx={}; W.forEach(w=>idx[w.word]=w.i);
  const H=(data.heads||[]).map((h,i)=>{ const tiles=h.tiles.split("|"), need=mkNeed(tiles.map(norm));
    return {i,head:h.head,type:h.type,flavor:h.flavor,stem:h.stem||"",tiles,need,kinds:Object.keys(need),rawKinds:[...new Set(tiles)]}; });
  const hidx={}; H.forEach(h=>hidx[h.head]=h.i);
  const headByKey={}; H.forEach(h=>headByKey[h.tiles.map(norm).sort().join("|")]=h);
  // 表示名: 手牌の牌を語に割り当てて、ぉ゛(お)・つ/っ/ちゅ(つ・っ)を使った語は、使った牌の字に置き換える(ぉ゛まめ・ちちゅ♡・きっく など)
  const PREF={"お":["ぉ゛","お"],"つ":["ちゅ","つ","っ"],"っ":["っ","つ","ちゅ"]};
  function displayNames(items,hand){
    const avail={}; hand.forEach(t=>avail[t]=(avail[t]||0)+1);
    const take=t=>{ if((avail[t]||0)>0){ avail[t]--; return true; } return false; };
    const alloc=items.map(it=>it.tiles.map(()=>null));
    items.forEach((it,a)=>it.tiles.forEach((t,b)=>{ if(FLEX.some(f=>f.tile===t)){ take(t); alloc[a][b]=t; } }));   // ちゅを必要とする語(ちゅっちゅ・べろちゅ)を先に
    items.forEach((it,a)=>it.tiles.forEach((t,b)=>{ if(alloc[a][b]!==null) return;
      const cands=PREF[t]||[t]; let got=null;
      for(const c of cands){ if(take(c)){ got=c; break; } } alloc[a][b]=got===null?t:got; }));
    return items.map((it,a)=>{
      if(it.name.includes("・")) return it.name;
      let out="", cnt={}; for(const ch of it.name){ const k=(cnt[ch]=(cnt[ch]||0)+1)-1; let rep=ch;
        if(ch==="お"||ch==="つ"||ch==="っ"){ let n=-1; for(let b=0;b<it.tiles.length;b++){ if(it.tiles[b]===ch){ n++; if(n===k){ const act=alloc[a][b]; if(act!==ch&&(act==="ぉ゛"||act==="ちゅ"||act==="つ"||act==="っ")) rep=act; break; } } } }
        out+=rep; } return out; });
  }

  // ---- タップ操作の補助 ----
  // 手牌の牌(実牌)を、語の牌の並びに割り当てる(ちゅの必要を先に。ぉ゛・っ・ちゅは、その語の牌の字に近いものを先に使う)。語の並びの実牌を返す(足りない所は null)
  function allocTiles(rawTiles,avail){
    const left=avail.slice(), out=rawTiles.map(()=>null);
    const take=t=>{ const k=left.indexOf(t); if(k>=0){ left.splice(k,1); return true; } return false; };
    rawTiles.forEach((t,b)=>{ if(FLEX.some(f=>f.tile===t)&&take(t)) out[b]=t; });
    rawTiles.forEach((t,b)=>{ if(out[b]!==null) return; const n=norm(t);
      const cands=(PREF[n]||[n]).slice(); if(!cands.includes(t)) cands.unshift(t);
      for(const c of cands){ if(norm(c)===n||(FLEX.some(f=>f.tile===c&&f.base===n))){ if(take(c)){ out[b]=c; break; } } } });
    return out;
  }
  // 選んだ牌(実牌のリスト)が、ちょうど1つの語になる語の一覧: [{w,flex}](flex=ちゅをつとして使った枚数。少ない順)
  function matchWords(tiles){
    if(tiles.length!==3) return [];
    const out=[]; handVariants(tiles).forEach((arr,b)=>{ const c=countsOf(arr);
      W.forEach(w=>{ if(w.kinds.length===Object.keys(c).length&&w.kinds.every(t=>(c[t]||0)===w.need[t])&&!out.some(o=>o.w===w.i)) out.push({w:w.i,flex:b}); }); });
    return out;
  }
  // 2牌が、雀頭の辞書の語になるか(牌の組み合わせが同じ雀頭は、最初の1つ)
  function matchHeads(tiles){
    if(tiles.length!==2) return [];
    const out=[]; handVariants(tiles).forEach(arr=>{ const h=headByKey[arr.slice().sort().join("|")]; if(h&&!out.includes(h.i)) out.push(h.i); }); return out;
  }
  // 2牌が、あと1枚で語になる搭子か: [{w,missing}](missing=足りない牌(語の牌のまま))
  function matchTatsu(tiles){
    if(tiles.length!==2) return [];
    const out=[]; handVariants(tiles).forEach(arr=>{ const c=countsOf(arr);
      W.forEach(w=>{ if(out.some(o=>o.w===w.i)) return; if(!Object.keys(c).every(t=>(c[t]||0)<=(w.need[t]||0))) return;
        let miss=null; for(const t of w.kinds){ if((c[t]||0)<w.need[t]) miss=t; } if(miss!==null) out.push({w:w.i,missing:miss}); }); });
    return out;
  }
  // 語の表示名(最初の読み。ぉ゛・っ・ちゅを使ったら、その字に置き換える)。items=[{name,tiles}] を、使った実牌 hand に合わせる
  function labelOf(item,hand){
    const parts=item.name.split("・"); let best=parts[0];
    if(parts.length>1){ const cnt=c=>hand.filter(t=>t===c).length; let bs=1e9;
      parts.forEach(p=>{ const sc=Math.abs([...p].filter(x=>x==="っ").length-cnt("っ"))+Math.abs([...p].filter(x=>x==="つ").length-cnt("つ")); if(sc<bs){ bs=sc; best=p; } }); }
    return displayNames([{name:best,tiles:item.tiles}],hand)[0];
  }

  function expand(tok){
    const s=new Set();
    if(tok.startsWith("mod:")){ W.forEach(w=>{ if(w.mods.includes(tok.slice(4))) s.add(w.i); }); }
    else if(tok.startsWith("pos:")){ W.forEach(w=>{ if(w.position===tok.slice(4)) s.add(w.i); }); }
    else if(tok.startsWith("stem:")){ W.forEach(w=>{ if(w.stem===tok.slice(5)) s.add(w.i); }); }
    else if(tok.startsWith("part:")){ W.forEach(w=>{ if(w.part===tok.slice(5)) s.add(w.i); }); }
    else { if(!(tok in idx)) throw new Error("辞書にない語: "+tok); s.add(idx[tok]); }
    return s;
  }
  const union=(toks)=>{ const s=new Set(); toks.forEach(t=>expand(t).forEach(x=>s.add(x))); return s; };
  const kv=p=>{ const o={}; p.split(";").forEach(x=>{ const k=x.indexOf("="); o[x.slice(0,k)]=x.slice(k+1); }); return o; };
  const cnt=(set,four)=>{ let c=0; for(const w of four) if(set.has(w)) c++; return c; };

  // 役ナビ用: 語が増えても成立が崩れない条件(組んだ語だけで「いま成立」と言える)。
  // 4語+雀頭がそろって初めて決まる条件(singles_eq・all_in_set・stem_pairs・distinct_*・modifier_pairs・position_split・part_pairs)と、
  // アガリの14牌で決まる variant_count は含めない。雀頭の条件は、雀頭を組んだあとだけ成立する(head が null なら不成立)。
  const MONO=new Set(["count_same_modifier","count_same_stem","count_same_part","count_tail_same_part","count_in_set","contains_all","one_from_each",
    "pair_same_stem_modifiers","count_part","head_is","head_flavor","head_stem_match","head_part_match"]);
  const rows=data.yaku.map(y=>{
    const ct=y.condition_type, p=y.params; let f;
    if(ct==="count_same_modifier"){ const a=kv(p), s=expand("mod:"+a.mod), n=+a.n; f=four=>cnt(s,four)>=n; }
    else if(ct==="count_same_stem"){ const a=kv(p), s=expand("stem:"+a.stem), n=+a.n; f=four=>cnt(s,four)>=n; }
    else if(ct==="count_same_part"){ const n=+kv(p).n, ss=PARTS4.map(pt=>expand("part:"+pt)); f=four=>ss.some(s=>cnt(s,four)>=n); }
    else if(ct==="count_tail_same_part"){ const n=+kv(p).n, ss=PARTS4.map(pt=>{ const s=new Set(); W.forEach(w=>{ if(w.part===pt&&TAIL.has(w.modifier)) s.add(w.i); }); return s; }); f=four=>ss.some(s=>cnt(s,four)>=n); }
    else if(ct==="singles_eq"){ const n=+kv(p).n, s=new Set(); W.forEach(w=>{ if(w.type==="単独") s.add(w.i); }); f=four=>cnt(s,four)===n; }
    else if(ct==="count_in_set"){ const a=kv(p), s=union(a.set.split("|")), m=+a.min; f=four=>cnt(s,four)>=m; }
    else if(ct==="all_in_set"){ const a=kv(p), s=union(a.set.split("|")); f=four=>cnt(s,four)===4; }
    else if(ct==="contains_all"){ const alts=p.split("/").map(a=>a.split("|").map(w=>idx[w])); f=four=>alts.some(al=>al.every(w=>four.includes(w))); }
    else if(ct==="one_from_each"){
      const gs=p.split(";").map(g=>union(g.split("|")));
      f=four=>{ const used=[false,false,false,false];
        const go=gi=>{ if(gi===gs.length) return true; for(let k=0;k<4;k++){ if(!used[k]&&gs[gi].has(four[k])){ used[k]=true; if(go(gi+1)){used[k]=false;return true;} used[k]=false; } } return false; };
        return go(0); };
    }
    else if(ct==="pair_same_stem_modifiers"){
      // 同じ語幹 X の、Xコキ と X舐め(語幹で数える。別名 まめ=くり も同じ語幹。CLAUDE.md §5-7・§6-3。以前は語名の連結で探していたので、まめコキ+くり舐めを数えなかった)
      const ms=p.split("|"); const stems=new Set(W.map(w=>w.stem).filter(x=>x));
      f=four=>[...stems].some(st=>ms.every(m=>four.some(i=>W[i].stem===st&&W[i].mods.length===1&&W[i].mods[0]===m)));
    }
    else if(ct==="count_part"){ const a=kv(p), s=expand("part:"+a.part), n=+a.n; f=four=>cnt(s,four)>=n; }
    else if(ct==="stem_pairs"){ const P=+kv(p).pairs; f=four=>{ const cs={}; four.forEach(i=>{ const s=W[i].stem; if(s) cs[s]=(cs[s]||0)+1; }); return Object.values(cs).filter(v=>v===2).length===P; }; }
    else if(ct==="distinct_stems"){ f=four=>four.every(i=>W[i].stem)&&new Set(four.map(i=>W[i].stem)).size===4; }
    else if(ct==="distinct_modifiers"){ f=four=>{ if(!four.every(i=>W[i].mods.length>=1)) return false; const tk=[]; four.forEach(i=>W[i].mods.forEach(m=>tk.push(m))); return new Set(tk).size===tk.length; }; }
    else if(ct==="modifier_pairs"){ const P=+kv(p).pairs; f=four=>{ if(!four.every(i=>W[i].mods.length===1)) return false; const cm={}; four.forEach(i=>{ const m=W[i].mods[0]; cm[m]=(cm[m]||0)+1; }); return Object.values(cm).filter(v=>v===2).length===P; }; }
    else if(ct==="position_split"){ const a=kv(p), h=+a.head, t=+a.tail; f=four=>four.filter(i=>W[i].position==="語頭").length===h&&four.filter(i=>W[i].position==="語尾").length===t; }
    else if(ct==="part_pairs"){ const P=+kv(p).pairs; f=four=>{ const cp={}; four.forEach(i=>{ const pt=W[i].part; if(PARTS4.includes(pt)) cp[pt]=(cp[pt]||0)+1; }); return Object.values(cp).filter(v=>v===2).length===P; }; }
    else if(ct==="head_is"){ const hs=kv(p).head.split("|"); f=(four,tiles,head)=>!!head&&hs.includes(head.head); }
    else if(ct==="head_flavor"){ const fl=kv(p).flavor; f=(four,tiles,head)=>!!head&&head.type==="喘ぎ声"&&head.flavor===fl; }
    else if(ct==="head_stem_match"){ const a=kv(p), st=a.stem, m=+a.min; f=(four,tiles,head)=>!!head&&head.type==="略称"&&head.stem===st&&four.filter(i=>W[i].stem===st).length>=m; }
    else if(ct==="head_part_match"){ f=(four,tiles,head)=>!!head&&head.type==="略称"&&(PARTS4.includes(head.flavor)||head.flavor==="SM")&&four.some(i=>W[i].part===head.flavor); }
    else if(ct==="variant_count"){ const a=kv(p), tile=a.tile, m=+a.min; f=(four,tiles)=>(tiles||[]).filter(t=>t===tile).length>=m; }
    else throw new Error("未対応の条件: "+ct);
    return {name:y.name,group:y.group,tier:+y.tier,han:+y.han_provisional,f,ct,mono:MONO.has(ct)};
  });
  const groups={}; rows.forEach((r,i)=>{ if(r.group){ (groups[r.group]=groups[r.group]||[]).push(i); } });
  Object.values(groups).forEach(ids=>ids.sort((a,b)=>rows[a].tier-rows[b].tier));
  // 役の判定(group の絞り込み・同名の役は1回だけ加算)。合体は含まない
  function computeYaku(four,tiles,head){
    const raw=rows.map(r=>r.f(four,tiles,head)), eff=raw.slice();
    for(const ids of Object.values(groups)) for(let a=0;a<ids.length;a++) for(let b=a+1;b<ids.length;b++) if(raw[ids[b]]) eff[ids[a]]=false;
    const seen=new Set(), out=[]; let han=1;
    rows.forEach((r,i)=>{ if(eff[i]&&!seen.has(r.name)){ seen.add(r.name); out.push({name:r.name,han:r.han}); han+=r.han; } });
    return {yaku:out,han,raw:rows.filter((r,i)=>raw[i]).map(r=>r.name)};
  }
  // 合体役(CLAUDE.md §6-7): group の絞り込みの【前】に成立している役で判定。各役は1つの合体にだけ使う/同時に最大2つ/翻の増分が最大の組み合わせ。
  // 合体は、元の役が実際に加算していた翻(絞り込みで消えた役は0)を、合体の翻に置き換える。連鎖なし。
  const MERGES=(data.merges||[]).map(m=>({name:m.name,src:m.source_yaku.split("|"),han:+m.han_provisional,level:m.level||""}));
  const MERGE_MAX=2;
  function chooseMerges(rawNames,added){
    const cand=[]; MERGES.forEach((m,mi)=>{ if(m.src.every(x=>rawNames.has(x))) cand.push({mi,d:m.han-m.src.reduce((a,x)=>a+(added[x]||0),0)}); });
    // 組み合わせは、合体の数が少ないものから順に(同じ増分なら、少ないほう・定義順が先のものを採る。sim 側 yaku14.py と同じ)
    let best=[],bd=0;
    for(let k=1;k<=MERGE_MAX;k++){
      const go=(start,chosen,used,d)=>{
        if(chosen.length===k){ if(d>bd){ bd=d; best=chosen.slice(); } return; }
        for(let j=start;j<cand.length;j++){ const m=MERGES[cand[j].mi]; if(m.src.some(x=>used.has(x))) continue;
          chosen.push(cand[j].mi); m.src.forEach(x=>used.add(x)); go(j+1,chosen,used,d+cand[j].d); m.src.forEach(x=>used.delete(x)); chosen.pop(); } };
      go(0,[],new Set(),0);
    }
    return {merges:best,delta:bd};
  }
  // 4語+雀頭の採点: 役(絞り込み後)+合体。han = 1 + 役の加算 + 合体による増分
  function scoreFour(four,tiles,head){
    const r=computeYaku(four,tiles,head);
    if(!MERGES.length||!(OPT.merges)) return {han:r.han,hanNoMerge:r.han,yaku:r.yaku,merges:[],raw:r.raw};
    const added={}; r.yaku.forEach(y=>added[y.name]=y.han);
    const {merges,delta}=chooseMerges(new Set(r.raw),added);
    const absorbed=new Set(); merges.forEach(mi=>MERGES[mi].src.forEach(x=>absorbed.add(x)));
    return {han:r.han+delta,hanNoMerge:r.han,yaku:r.yaku.filter(y=>!absorbed.has(y.name)),
      merges:merges.map(mi=>({name:MERGES[mi].name,han:MERGES[mi].han,level:MERGES[mi].level,sources:MERGES[mi].src.slice(),
        removed:MERGES[mi].src.reduce((a,x)=>a+(added[x]||0),0)})),raw:r.raw};
  }
  // ---- 役ナビ(組んだ語だけの、途中の判定) ----
  // 組んだ語(four は4語未満でよい)と雀頭(なければ null)で、いま成立している役(mono のものだけ。group の絞り込み・同名1回)
  function partialYaku(four,head){
    const raw=rows.map(r=>r.mono&&r.f(four,[],head)), eff=raw.slice();
    for(const ids of Object.values(groups)) for(let a=0;a<ids.length;a++) for(let b=a+1;b<ids.length;b++) if(raw[ids[b]]) eff[ids[a]]=false;
    const seen=new Set(), out=[]; rows.forEach((r,i)=>{ if(eff[i]&&!seen.has(r.name)){ seen.add(r.name); out.push({name:r.name,han:r.han}); } });
    return out;
  }
  // 組んだ語だけで成立している mono の役(group の絞り込み前)の名前の集合(テスト・照合用)
  const partialRaw=(four,head)=>new Set(rows.filter(r=>r.mono&&r.f(four,[],head)).map(r=>r.name));
  const headObj=h=>h?{head:h.head,type:h.type,flavor:h.flavor,stem:h.stem}:null;
  // ある語(か雀頭)を足すと、新しく成立する役(翻の高い順)
  function gainBy(four,head,addWord,addHead){
    const cur=new Set(partialYaku(four,head).map(y=>y.name));
    const f2=addWord==null?four:four.concat([addWord]), h2=addHead!=null?headObj(H[addHead]):head;
    return partialYaku(f2,h2).filter(y=>!cur.has(y.name)).sort((a,b)=>b.han-a.han);
  }
  // 語 w を足したあと、さらに1語(か雀頭)を足せば新しく成立する役(「組んだあと、あと1語で成立」)。足す語の候補は、辞書の全語。
  function gainByNext(four,head,w){
    const base=new Set(partialYaku(four.concat([w]),head).map(y=>y.name)), out={};
    for(let j=0;j<W.length;j++){ if(j===w||four.includes(j)) continue; if(four.length+2>4) break;
      for(const y of partialYaku(four.concat([w,j]),head)) if(!base.has(y.name)&&!(y.name in out)) out[y.name]={name:y.name,han:y.han,by:W[j].word}; }
    return Object.values(out).sort((a,b)=>b.han-a.han);
  }
  // 惜しかった役(アガリ): 4語のうち1語を替えれば成立した役(完全な判定。雀頭・牌の条件も含む)。上位 top
  function nearSwap(four,tiles,head,top){
    const have=new Set(computeYaku(four,tiles,head).raw), out={};
    const grpHave={}; rows.forEach(r=>{ if(r.group&&have.has(r.name)) grpHave[r.group]=Math.max(grpHave[r.group]||0,r.tier); });
    rows.forEach(r=>{
      if(have.has(r.name)||r.ct==="variant_count"||(r.group&&grpHave[r.group]>=r.tier&&r.group in grpHave)) return;
      for(let p=0;p<four.length;p++) for(let j=0;j<W.length;j++){ if(four.includes(j)) continue;
        const f2=four.slice(); f2[p]=j; if(r.f(f2,tiles,head)){ if(!(r.name in out)||out[r.name].han<r.han) out[r.name]={name:r.name,han:r.han,from:W[four[p]].word,to:W[j].word}; break; } }
    });
    return Object.values(out).sort((a,b)=>b.han-a.han).slice(0,top||5);
  }
  // 惜しかった役(流局): 組んだ語(four)に、あと1語(か雀頭)を足せば成立した役(mono のものだけ)。上位 top
  function nearAdd(four,head,top){
    const cur=new Set(partialYaku(four,head).map(y=>y.name)), out={};
    if(four.length<4) for(let j=0;j<W.length;j++){ if(four.includes(j)) continue;
      for(const y of partialYaku(four.concat([j]),head)) if(!cur.has(y.name)&&(!(y.name in out)||out[y.name].han<y.han)) out[y.name]={name:y.name,han:y.han,by:W[j].word}; }
    if(!head) for(let k=0;k<H.length;k++) for(const y of partialYaku(four,headObj(H[k]))) if(!cur.has(y.name)&&!(y.name in out)) out[y.name]={name:y.name,han:y.han,by:H[k].head+"(雀頭)"};
    return Object.values(out).sort((a,b)=>b.han-a.han).slice(0,top||5);
  }
  // ある語が関わる役(語の指定・セレクターに、その語が入る役)の名前
  const relatedMemo={};
  function relatedYaku(w){
    if(relatedMemo[w]) return relatedMemo[w];
    const word=W[w], names=new Set();
    data.yaku.forEach(y=>{
      const toks=y.params.split(/[;/|]/).map(t=>t.includes("=")?t.split("=").pop():t).filter(Boolean);
      for(const t of toks){
        if(t===word.word||(t.startsWith("mod:")&&word.mods.includes(t.slice(4)))||(t.startsWith("pos:")&&word.position===t.slice(4))||(t.startsWith("stem:")&&word.stem===t.slice(5))||(t.startsWith("part:")&&word.part===t.slice(5))){ names.add(y.name); break; } }
      const a=kv(y.params.includes("=")?y.params:"x=0");
      if(y.condition_type==="count_same_modifier"&&word.mods.includes(a.mod)) names.add(y.name);
      if((y.condition_type==="count_same_stem"||y.condition_type==="head_stem_match")&&word.stem&&word.stem===a.stem) names.add(y.name);
      if(y.condition_type==="count_part"&&word.part===a.part) names.add(y.name);
    });
    return relatedMemo[w]=[...names];
  }

  // 山の枚数。options.tileRule: "new"(v1.3m: min(10,max(2,ceil(使う語・雀頭の数/2))) + 修飾牌は修飾3型の需要の10%(四捨五入))/ "old"(max(4,使う語・雀頭の数))
  // 使う語の数には、修飾3型を数えない(options.triplesOutOfDeckRule)。ぉ゛は variants の枚数(4枚固定)。
  const OPT=data.options||{}, RULE=OPT.tileRule||"old", MODX=OPT.modx!=null?+OPT.modx:0.1;
  const inRule=w=>!(OPT.triplesOutOfDeckRule&&w.type==="修飾3型");
  const used={}, demand={}; W.forEach(w=>{ if(inRule(w)) w.rawKinds.forEach(t=>used[t]=(used[t]||0)+1); if(w.type==="修飾3型") w.tiles.forEach(t=>demand[t]=(demand[t]||0)+1); });
  H.forEach(h=>h.rawKinds.forEach(t=>used[t]=(used[t]||0)+1));
  const deckCounts={}; Object.keys(used).forEach(t=>{
    deckCounts[t]= RULE==="new" ? Math.min(10,Math.max(2,Math.ceil(used[t]/2)))+(MOD_ORDER.includes(t)?Math.floor((demand[t]||0)*MODX+0.5):0) : Math.max(4,used[t]); });
  Object.keys(OPT.fixed||{}).forEach(t=>{ if(t in deckCounts) deckCounts[t]=+OPT.fixed[t]; });   // 枚数を固定する牌(dan5: ×2)
  function buildDeck(){ const d=[]; Object.keys(deckCounts).forEach(t=>{ for(let k=0;k<deckCounts[t];k++) d.push(t); }); (data.variants||[]).forEach(v=>{ for(let k=0;k<(+v.copies);k++) d.push(v.tile); }); return d; }

  // 14枚の、すべての分け方(別々の4語 + 雀頭1つ)。変種(ぉ゛・っ・ちゅ)は handVariants に従う。同じ(4語,雀頭)は1つにまとめる。limit 通りまで
  function allPartitions(hand,limit){
    if(hand.length!==14) return [];
    const out=[], seen=new Set(); limit=limit||Infinity;
    for(const arr of handVariants(hand)){
      const c=countsOf(arr);
      const cand=W.filter(w=>w.kinds.every(t=>(c[t]||0)>=w.need[t]));
      if(cand.length<4) continue;
      const chosen=[];
      (function dfs(start,k){
        if(out.length>=limit) return;
        if(k===4){
          const rest=[]; for(const t in c) for(let i=0;i<c[t];i++) rest.push(t);
          const h=headByKey[rest.sort().join("|")]; if(!h) return;
          const four=chosen.map(w=>w.i), key=four.join(",")+"/"+h.i; if(seen.has(key)) return; seen.add(key);
          out.push({four,head:h.i});
          return;
        }
        for(let j=start;j<=cand.length-(4-k);j++){
          const w=cand[j]; if(!w.kinds.every(t=>c[t]>=w.need[t])) continue;
          w.kinds.forEach(t=>c[t]-=w.need[t]); chosen.push(w); dfs(j+1,k+1); chosen.pop(); w.kinds.forEach(t=>c[t]+=w.need[t]);
        }
      })(0,0);
      if(out.length>=limit) break;
    }
    return out;
  }
  const isWin14=hand=>allPartitions(hand,1).length>0;
  // 分け方を採点する(合体を含む)
  function scorePartition(hand,p){ const h=H[p.head]; return scoreFour(p.four,hand,headObj(h)); }
  // アガリ判定(14枚): 別々の4語 + 雀頭1つ。翻が最大の分け方を返す(limit 通りまでの分け方から)
  function win14(hand,limit){
    if(hand.length!==14) return null;
    let best=null;
    for(const p of allPartitions(hand,limit)){
      const h=H[p.head], r=scorePartition(hand,p);
      if(!best||r.han>best.han||(r.han===best.han&&r.yaku.length+r.merges.length>best.yaku.length+best.merges.length)){
        const dn=displayNames(p.four.map(x=>({name:W[x].word,tiles:W[x].tiles})).concat([{name:h.head,tiles:h.tiles}]),hand);
        best={words:p.four.slice(),wordsDisp:dn.slice(0,4),head:h.head,headIdx:h.i,headDisp:dn[4],headTiles:h.tiles.slice(),headType:h.type,headFlavor:h.flavor,han:r.han,hanNoMerge:r.hanNoMerge,yaku:r.yaku,merges:r.merges,raw:r.raw};
      }
    }
    if(best) best.partitions=undefined;
    return best;
  }
  // テンパイ: 13枚に、山の牌を1枚足すと完成する(待ちの牌を返す)
  function tenpaiWaits(hand,wallCount){
    if(hand.length!==13) return [];
    const origWall=wallCount, wc=mergeWall(wallCount); const waits=new Set();
    for(const arr of handVariants(hand)){
      const c=countsOf(arr);
      const defOf=x=>{ let miss=0,mt=null; for(const t of x.kinds){ const m=Math.max(0,x.need[t]-(c[t]||0)); if(m){ miss+=m; mt=t; } } return {miss,mt}; };
      const cw=W.filter(w=>defOf(w).miss<=1), ch=H.filter(h=>defOf(h).miss<=1);
      const takeFrom=x=>{ const taken=[]; let miss=0,mt=null; for(const t of x.kinds){ const have=Math.min(c[t]||0,x.need[t]); taken.push([t,have]); if(have<x.need[t]){ miss+=x.need[t]-have; mt=t; } } return {taken,miss,mt}; };
      (function dfs(s,k,def,dt){
        if(k===4){
          for(const h of ch){ const r=takeFrom(h); if(def+r.miss!==1) continue; const w=r.miss?r.mt:dt; if(w!==null&&(wc[w]||0)>0) waits.add(w); }
          return;
        }
        for(let j=s;j<cw.length;j++){ const r=takeFrom(cw[j]); if(def+r.miss>1) continue;
          r.taken.forEach(([t,n])=>c[t]=(c[t]||0)-n); dfs(j+1,k+1,def+r.miss,r.miss?r.mt:dt); r.taken.forEach(([t,n])=>c[t]+=n); }
      })(0,0,0,null);
    }
    const out=new Set(); waits.forEach(w=>{ if((origWall[w]||0)>0) out.add(w); VARS.forEach(v=>{ if(v.base===w&&(origWall[v.tile]||0)>0) out.add(v.tile); }); });
    return [...out];
  }
  // 手牌で作れる語/あと1枚の語(手牌に近い順)
  function statusOf(list,nameKey,hand,wall){
    wall=mergeWall(wall); const doneSet=new Set(), oneMap={};
    for(const arr of handVariants(hand)){ const c=countsOf(arr);
      list.forEach(x=>{ let miss=0,mt=null; for(const t of x.kinds){ const m=Math.max(0,x.need[t]-(c[t]||0)); if(m){ miss+=m; mt=t; } }
        const nm=x[nameKey]; if(miss===0) doneSet.add(nm); else if(miss===1&&!(nm in oneMap)) oneMap[nm]={need:mt,left:wall[mt]||0}; }); }
    const done=list.filter(x=>doneSet.has(x[nameKey])).map(x=>x[nameKey]);
    const one=Object.keys(oneMap).filter(nm=>!doneSet.has(nm)).map(nm=>Object.assign({[nameKey]:nm},oneMap[nm]));
    one.sort((a,b)=>(b.left-a.left)||(a[nameKey]<b[nameKey]?-1:1)); return {done,one};
  }
  const wordStatus2=(hand,wall)=>statusOf(W,"word",hand,wall);
  const headStatus=(hand,wall)=>statusOf(H,"head",hand,wall);
  // ある牌を使う語(手牌に近い順)/雀頭
  // 語の牌を、手牌の牌に割り当てる(ちゅの必要を先に。つの必要には、つを先に、足りなければ余ったちゅを使う)
  function ownedFlags(rawTiles,c){
    const rem=Object.assign({},c), res=new Array(rawTiles.length); let miss=0,missTiles=[];
    const order=rawTiles.map((t,i)=>({t:norm(t),i})).sort((a,b)=>FLEX.some(f=>f.tile===b.t)-FLEX.some(f=>f.tile===a.t));
    order.forEach(({t,i})=>{ let owned=false; if((rem[t]||0)>0){ rem[t]--; owned=true; } else { const f=FLEX.find(f=>f.base===t&&(rem[f.tile]||0)>0); if(f){ rem[f.tile]--; owned=true; } }
      res[i]={t:rawTiles[i],owned}; if(!owned){ miss++; missTiles.push(t); } });
    return {tiles:res,miss,missTiles};
  }
  function usesTile(rawTiles,tn){ return rawTiles.some(t=>norm(t)===tn)||FLEX.some(f=>f.tile===tn&&rawTiles.some(t=>norm(t)===f.base)); }
  function wordsUsingTile(tile,hand,wall){
    const tn=norm(tile); wall=mergeWall(wall); const c=countsOf(hand.map(norm)); const out=[];
    W.forEach(w=>{ if(!usesTile(w.tiles,tn)) return; const r=ownedFlags(w.tiles,c);
      out.push({word:w.word,tiles:r.tiles,miss:r.miss,minWall:r.miss?Math.min(...r.missTiles.map(t=>wall[t]||0)):1e9}); });
    out.sort((a,b)=>(a.miss-b.miss)||(b.minWall-a.minWall)||(a.word<b.word?-1:1)); return out;
  }
  function headsUsingTile(tile,hand,wall){
    const tn=norm(tile); const c=countsOf(hand.map(norm)); const out=[];
    H.forEach(h=>{ if(!usesTile(h.tiles,tn)) return; const r=ownedFlags(h.tiles,c);
      out.push({word:h.head,tiles:r.tiles,miss:r.miss,flavor:h.flavor,type:h.type}); });
    out.sort((a,b)=>(a.miss-b.miss)||(a.word<b.word?-1:1)); return out;
  }
  function idxsForTiles(tiles,hand){
    const avail={}; hand.forEach((t,i)=>{ const n=norm(t); (avail[n]=avail[n]||[]).push(i); }); const out=[];
    const raw=tiles.map(norm);
    raw.forEach(t=>{ if(FLEX.some(f=>f.tile===t)&&avail[t]&&avail[t].length) out.push(avail[t].shift()); });          // ちゅの必要を先に
    raw.forEach(t=>{ if(FLEX.some(f=>f.tile===t)) return;
      if(avail[t]&&avail[t].length) out.push(avail[t].shift());
      else { const f=FLEX.find(f=>f.base===t&&avail[f.tile]&&avail[f.tile].length); if(f) out.push(avail[f.tile].shift()); } });
    return out;
  }
  const idxsForWord=(word,hand)=>idxsForTiles(W[idx[word]].tiles,hand);
  const idxsForHead=(head,hand)=>idxsForTiles(H[hidx[head]].tiles,hand);

  // ---- 牌効率のヒント: 面子(完成した語)→搭子(あと1枚の語)→雀頭→余り ----
  function analyzeOne(hand,wall,opt){
    opt=opt||{}; const locked=opt.locked||0, headLocked=!!opt.headLocked, maxW=Math.max(0,4-locked), maxH=headLocked?0:1;
    const handN=hand; const c={}; handN.forEach(t=>c[t]=(c[t]||0)+1);
    function mk(x,isHead){
      let miss=0,mt=null; const take={};
      for(const t of x.kinds){ const have=Math.min(c[t]||0,x.need[t]); take[t]=have; if(have<x.need[t]){ miss+=x.need[t]-have; mt=t; } }
      if(miss===0) return {x,isHead,complete:true,uke:0,mt:null,take};
      if(miss===1&&(wall[mt]||0)>0) return {x,isHead,complete:false,uke:wall[mt],mt,take};
      return null;
    }
    const cw=W.map(w=>mk(w,false)).filter(Boolean).sort((a,b)=>(b.complete-a.complete)||(b.uke-a.uke)).slice(0,24);
    const ch=maxH?H.map(h=>mk(h,true)).filter(Boolean).sort((a,b)=>(b.complete-a.complete)||(b.uke-a.uke)).slice(0,8):[];
    const top=cw.concat(ch); let best=null; const chosen=[]; const cc=Object.assign({},c);
    function evalSet(){
      const ws=chosen.filter(x=>!x.isHead), hd=chosen.find(x=>x.isHead); const comp=ws.filter(x=>x.complete).length, miss=new Set(); let uke=0;
      chosen.forEach(x=>{ if(!x.complete&&!miss.has(x.mt)){ miss.add(x.mt); uke+=wall[x.mt]; } });
      const sc=ws.length*100000+comp*10000+(hd?(hd.complete?4000:2000):0)+Math.min(uke,999);
      if(!best||sc>best.sc) best={sc,sel:chosen.slice()};
    }
    (function dfs(s,nw,nh){ evalSet();
      for(let j=s;j<top.length;j++){ const x=top[j]; if(x.isHead?nh>=maxH:nw>=maxW) continue;
        let ok=true; const used=[]; for(const t of x.x.kinds){ if((cc[t]||0)<x.take[t]){ok=false;break;} used.push([t,x.take[t]]); }
        if(!ok) continue; used.forEach(([t,n])=>cc[t]-=n); chosen.push(x); dfs(j+1,nw+(x.isHead?0:1),nh+(x.isHead?1:0)); chosen.pop(); used.forEach(([t,n])=>cc[t]+=n); }
    })(0,0,0);
    const avail={}; handN.forEach((t,i)=>{ (avail[t]=avail[t]||[]).push(i); });
    const role=hand.map(()=>"rest"); let head=null;
    const blocks=[];
    (best?best.sel:[]).forEach(x=>{ const idxs=[]; for(const t of x.x.kinds) for(let k=0;k<x.take[t];k++){ const i=avail[t].shift(); idxs.push(i); role[i]=x.isHead?"head":(x.complete?"meld":"tatsu"); }
      const b={word:x.isHead?x.x.head:x.x.word,complete:x.complete,missing:x.mt,wallLeft:x.mt?wall[x.mt]:0,idxs};
      if(x.isHead) head=b; else blocks.push(b); });
    const pot=t=>{ let p=0; for(const w of W){ if(!(t in w.need)) continue; let o=0; for(const u of w.kinds){ if(u!==t) o+=Math.min(c[u]||0,w.need[u]); } if(o>=1) p++; } return p; };
    let rec=-1,bp=1e9,bw=1e9;
    role.forEach((r,i)=>{ if(r!=="rest") return; const t=handN[i], p=pot(t), wl=wall[t]||0; if(p<bp||(p===bp&&wl<bw)){ bp=p; bw=wl; rec=i; } });
    return {blocks,head,role,rec,sc:best?best.sc:0};
  }
  function analyze(hand,wall,opt){ wall=mergeWall(wall); let bestR=null; for(const arr of handVariants(hand)){ const r=analyzeOne(arr,wall,opt); if(!bestR||r.sc>bestR.sc) bestR=r; } return bestR; }
  return {allocTiles,matchWords,matchHeads,matchTatsu,labelOf,FLEX,W,H,idx,hidx,VAR,norm,rows,computeYaku,scoreFour,scorePartition,allPartitions,isWin14,partialYaku,partialRaw,gainBy,gainByNext,nearSwap,nearAdd,relatedYaku,MERGES,headObj,buildDeck,deckCounts,win14,tenpaiWaits,wordStatus2,headStatus,wordsUsingTile,headsUsingTile,displayNames,handVariants,idxsForWord,idxsForHead,idxsForTiles,analyze,pointsFor,sortHand,DISPLAY,shuffle};
}
root.HMcore={setup,pointsFor,DISPLAY,shuffle};
if(typeof module!=="undefined") module.exports=root.HMcore;
})(typeof window!=="undefined"?window:globalThis);
