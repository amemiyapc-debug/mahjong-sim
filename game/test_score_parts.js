// 手の一覧(JSON)の、全分割と採点(合体を含む)を、game/core.js で出力する。tests/test_core_v13m.py から使う。
// 使い方: node test_score_parts.js data.json hands.json out.json
const fs = require("fs"); const HM = require("./core.js");
const G = HM.setup(JSON.parse(fs.readFileSync(process.argv[2], "utf8")));
const hands = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const out = hands.map(h => {
  const ps = G.allPartitions(h);
  const parts = ps.map(p => { const r = G.scorePartition(h, p); return { four: p.four.slice().sort((a, b) => a - b), head: G.H[p.head].tiles.map(t=>G.norm(t)).sort().join("|"), han: r.han, hanNoMerge: r.hanNoMerge, yaku: r.yaku.map(y => y.name).sort(), merges: r.merges.map(m => m.name).sort() }; });
  const w = G.win14(h);
  return { parts, win: w ? { han: w.han, words: w.words.slice().sort((a, b) => a - b), head: G.H[w.headIdx].tiles.map(t=>G.norm(t)).sort().join("|") } : null };
});
fs.writeFileSync(process.argv[4], JSON.stringify(out));
