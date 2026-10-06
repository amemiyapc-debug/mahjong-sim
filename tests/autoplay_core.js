// game/core.js(ゲーム本体の判定と牌効率のヒント analyze)だけで、強CPU(ヒントどおりに捨てる)を自動プレイして、アガリ率を測る。
// 山は core.js の buildDeck(旧ルール max(4,使う語の数) + ぉ゛4枚)。sim14.py の条件B(旧ルール)の独立した照合用。
const fs = require("fs");
const [coreJs, dataJson, nGames, L, seed] = process.argv.slice(2);
const HM = require(require("path").resolve(coreJs));
const G = HM.setup(JSON.parse(fs.readFileSync(dataJson, "utf8")));
let s = (+seed) >>> 0; const rng = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
let wins = 0, ten = 0, hanSum = 0; const n = +nGames, LL = +L;
for (let g = 0; g < n; g++) {
  const deck = G.shuffle(G.buildDeck(), rng); const wc = {}; deck.forEach(t => wc[t] = (wc[t] || 0) + 1);
  let hand = deck.splice(0, 13); hand.forEach(t => wc[t]--);
  let won = false;
  for (let k = 1; k <= LL; k++) {
    const t = deck.pop(); wc[t]--; hand.push(t);
    const r = G.win14(hand); if (r) { won = true; wins++; hanSum += r.han; break; }
    const a = G.analyze(hand, wc); hand.splice(a.rec, 1);
  }
  if (!won && G.tenpaiWaits(hand, wc).length) ten++;
}
console.log(JSON.stringify({ games: n, L: LL, win_rate: wins / n, tenpai_ryukyoku: ten / n, mean_han_no_merge: hanSum / wins, deck: G.buildDeck().length }));
