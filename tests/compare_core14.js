// 手の一覧(JSON)を、game/core.js の win14 で判定し、結果(true/false)の配列をJSONで出力する
const fs = require("fs");
const [coreJs, dataJson, handsJson, outJson] = process.argv.slice(2);
const HM = require(require("path").resolve(coreJs));
const G = HM.setup(JSON.parse(fs.readFileSync(dataJson, "utf8")));
const hands = JSON.parse(fs.readFileSync(handsJson, "utf8"));
const t0 = Date.now();
const res = hands.map(h => !!G.win14(h));
fs.writeFileSync(outJson, JSON.stringify({ res, ms: Date.now() - t0 }));
