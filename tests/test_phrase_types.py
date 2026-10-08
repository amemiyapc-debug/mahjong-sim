"""句の型(20261008-2030)の確認。 python3 tests/test_phrase_types.py"""
import os, sys, csv
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "ichishuu"))
from phrase_types import PhraseBook
ng = 0
def ok(m, c):
    global ng; print(("OK  " if c else "NG  ") + m); ng += (not c)
W = list(csv.DictReader(open(os.path.join(ROOT, "data", "words_ichishuu100.csv"), encoding="utf-8-sig")))
b = PhraseBook()
cnt = {t: len(p) for t, p in b.type_pairs.items()}
ok("型の数が、設定ファイル(phrase_types.csv)どおり9つ(欠番: 9・11)", sorted(cnt, key=int) == ["1", "2", "3", "4", "5", "6", "7", "8", "10"])
ok("手計算の見込みと一致: ①28 ②337 ③357 ④352 ⑤34 ⑥84 ⑩28", [cnt[t] for t in ("1", "2", "3", "4", "5", "6", "10")] == [28, 337, 357, 352, 34, 84, 28])
# 独立した数え直し(設定ファイルを使わず、語のリストから直接)
by = lambda **k: [w["word"] for w in W if all(w[a] == v for a, v in k.items())]
parts = [w for w in W if w["slot"] == "部位" and w["word"] != "つがい"]
ok("独立計算 ⑤: 男性器・つがいを外した部位17 × (なめろ・せめろ)2 = 34", len([w for w in parts if w["sub"] != "男性器"]) * 2 == 34)
ok("独立計算 ③: 部位21 ×(反応20 − しゃせい・がんしゃ・まんしゃ)17 = 357", len(parts) * 17 == 357)
ok("独立計算 ⑩: キス・吸い8語の組 C(8,2) = 28", len(by(sub="キス・吸い")) * (len(by(sub="キス・吸い")) - 1) // 2 == 28)
ok("つがいは、型の句に1つも使われない(全型)", not any("つがい" in p for s in b.type_pairs.values() for p in s))
ok("②: 行為の語に部位名が入るものは、合う部位とだけ組む(まん舐めは女性器の語とだけ)", all(b.by_name[(set(p) - {"まん舐め"}).pop()]["sub"] == "女性器" for p in b.type_pairs["2"] if "まん舐め" in p))
ok("④: しゃせい・がんしゃ・まんしゃ は、ちん舐め・ちんコキ・ぱいコキ・こうび のときだけ", all((set(p) - {x for x in p if x in ("しゃせい", "がんしゃ", "まんしゃ")}).pop() in ("ちん舐め", "ちんコキ", "ぱいコキ", "こうび") for p in b.type_pairs["4"] if any(x in p for x in ("しゃせい", "がんしゃ", "まんしゃ"))))
ok("⑥: 胸はぱちんとだけ、男性器はぱんぱん・ぱこぱことだけ", all(set(p) - {a for a in p if b.by_name[a]["slot"] == "部位"} == {"ぱちん"} for p in b.type_pairs["6"] if any(b.by_name[a]["sub"] == "胸" for a in p)) and all(next(x for x in p if b.by_name[x]["slot"] == "音") in ("ぱんぱん", "ぱこぱこ") for p in b.type_pairs["6"] if any(b.by_name[a]["sub"] == "男性器" for a in p)))
ok("⑧: Bに命令(なめろ・せめろ・いけっ・おちろ・さけべ)が入らない", not any(x in p for p in b.type_pairs["8"] for x in ("なめろ", "せめろ", "いけっ", "おちろ", "さけべ")))
# 設定ファイル駆動: 除外条件を空にすると、数が変わる(コードに直書きしていない)
b0 = PhraseBook(rules=[])
ok("除外条件を外すと数が変わる(設定ファイルから読んでいる): ②440 ③440 ④400 ⑤110 ⑥176 ⑧112", [len(b0.type_pairs[t]) for t in ("2", "3", "4", "5", "6", "8")] == [440, 440, 400, 110, 176, 112])
sg = {tuple(sorted((r["word_a"], r["word_b"]))) for r in csv.DictReader(open(os.path.join(ROOT, "data", "phrase_pairs_draft.csv"), encoding="utf-8-sig"))}
ok("看板30組が、従来どおり成立する(型の設定に関係なく、全部入っている)。型と重なる組は1つの句として数える", len(b.signboard) == 30 and {tuple(sorted(p)) for p in b.signboard} == sg and len(b.phrases(True, tuple(b.type_pairs))) == len(set().union(*b.type_pairs.values()) | b.signboard))
ok("型の句と看板の句で、重みが同じ(点数に差をつけない)", {t["weight"] for t in b.types} == {"1"})
ok("③の説明文が、2040の訂正(Aが原因でBになること)になっている", "Aが原因でBになること" in next(t for t in b.types if t["type_id"] == "3")["description"])
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
