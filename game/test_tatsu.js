// 搭子のリスト(ヒント一覧・2枚選んだときの待ち)と、判定(matchTatsu)の一致の確認(dan5 依頼 B「搭子リストの不一致」)
//  (a) 2枚の組ごとの matchTatsu の語は、手牌から見た「あと1枚の語(one)」か「そろっている語(done)」に入っている
//  (b) one の各語は、その語の持っている2牌の組の matchTatsu に、同じ待ち牌で入っている
//  (c) 待ち牌(missing)は、つ=っ・ぉ゛=お で重複して出ない(正規化済み)。山の残り枚数は、互換の牌を足した数
//  (d) 一覧は、山の残りが多い順
const fs=require("fs"); const HM=require("./core.js"); const G=HM.setup(JSON.parse(fs.readFileSync("data.json","utf8")));
let seed=777; const rng=()=>{ seed=(seed*1664525+1013904223)%4294967296; return seed/4294967296; };
let bad={a:0,b:0,c:0,d:0}, n=0;
const deckAll=G.buildDeck();
for(let k=0;k<1500;k++){
  const deck=HM.shuffle(deckAll.slice(),rng), hand=deck.splice(0,14), wc={}; deck.forEach(t=>wc[t]=(wc[t]||0)+1);
  const st=G.wordStatus2(hand,wc), oneW=new Set(st.one.map(o=>o.word)), doneW=new Set(st.done);
  for(let i=0;i<hand.length;i++) for(let j=i+1;j<hand.length;j++){
    const ts=G.matchTatsu([hand[i],hand[j]]); n++;
    const miss=ts.map(t=>t.missing+"@"+t.w); if(new Set(miss).size!==miss.length) bad.c++;
    for(const t of ts){ const w=G.W[t.w].word; if(!oneW.has(w)&&!doneW.has(w)) bad.a++; if(G.norm(t.missing)!==t.missing) bad.c++; }
  }
  for(const o of st.one){ const idxs=G.idxsForWord(o.word,hand); if(idxs.length!==2){ bad.b++; continue; }
    const ts=G.matchTatsu(idxs.map(i=>hand[i])); if(!ts.some(t=>G.W[t.w].word===o.word&&t.missing===o.need)) bad.b++; }
  const sorted=st.one.slice().sort((x,y)=>y.left-x.left); if(st.one.some((o,i)=>o.left!==sorted[i].left)) bad.d++;
}
console.log("手",1500,"・2枚の組",n,"/ 不一致 (a)",bad.a,"(b)",bad.b,"(c)",bad.c,"(d)",bad.d);
console.log(bad.a+bad.b+bad.c+bad.d===0?"すべてOK":"失敗");
