// 手の一覧(JSON)を、game/core.js で判定する。
// 各手: {hand:[牌14], parts:[{four:[語index×4], head:雀頭の名前}]}
// 出力: 手ごとに {win:{han,yaku,words,head}|null, parts:[{han,yaku}]}(役名は、group の絞り込み・同名1回の後)
const fs = require("fs");
const [coreJs, dataJson, casesJson, outJson] = process.argv.slice(2);
const HM = require(require("path").resolve(coreJs));
const G = HM.setup(JSON.parse(fs.readFileSync(dataJson, "utf8")));
const cases = JSON.parse(fs.readFileSync(casesJson, "utf8"));
const out = cases.map(c => {
  const w = G.win14(c.hand);
  const parts = c.parts.map(p => {
    const h = G.H[G.hidx[p.head]];
    const r = G.computeYaku(p.four, c.hand, { head: h.head, type: h.type, flavor: h.flavor, stem: h.stem });
    return { han: r.han, yaku: r.yaku.map(y => y.name) };
  });
  return { win: w ? { han: w.han, yaku: w.yaku.map(y => y.name), words: w.words, head: w.head } : null, parts };
});
fs.writeFileSync(outJson, JSON.stringify(out));
