"""一周版のデータの確認(20261008-0910・1320・1630の受け入れ条件)。 python3 tests/test_ichishuu_data.py"""
import csv, math, os, sys
from collections import Counter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rd = lambda n: list(csv.DictReader(open(os.path.join(ROOT, "data", n), encoding="utf-8-sig")))
W, P, U, N, M = rd("words_ichishuu100.csv"), rd("phrase_pairs_draft.csv"), rd("tile_usage_100.csv"), rd("phrase_names.csv"), rd("lina_memos_100.csv")
ng = 0
def ok(m, c):
    global ng; print(("OK  " if c else "NG  ") + m); ng += (not c)
names = [w["word"] for w in W]
ok("100語・重複なし・すべて3牌", len(W) == 100 and len(set(names)) == 100 and all(len(w["tiles"].split("|")) == 3 for w in W))
used = Counter(); [used.update(set(w["tiles"].split("|"))) for w in W]
cp = {t: min(10, max(2, math.ceil(u / 2))) for t, u in used.items()}
ok("牌 40種・専用牌なし(2語だけ: ど・な・コキ・媚び)", len(used) == 40 and min(used.values()) == 2 and sorted(t for t, u in used.items() if u == 2) == sorted(["ど", "な", "コキ", "媚び"]))
ok("枚数の式が tile_usage_100.csv と一致。山156枚・×2は9枚", all(cp[r["tile"]] == int(r["copies_old_rule"]) and used[r["tile"]] == int(r["used_in_words"]) for r in U) and sum(cp.values()) == 156 and cp["×2"] == 9)
ok("句の候補30組の語が、すべて100語の中にある(重複なし)", len(P) == 30 and all(p["word_a"] in names and p["word_b"] in names for p in P) and len({frozenset((p["word_a"], p["word_b"])) for p in P}) == 30)
ok("phrase_names.csv: 30行・列は5つ。語A・語Bが100語に一致し、phrase_pairs_draft.csv と同じ組・同じ順", len(N) == 30 and list(N[0].keys()) == ["no", "語A", "語B", "名前", "1周目の誤読名"] and all(n["語A"] == p["word_a"] and n["語B"] == p["word_b"] for n, p in zip(N, P)) and all(n["1周目の誤読名"] for n in N))
ok("lina_memos_100.csv: 100行・word列が一周版100語と同じ順序・同じ語・列は7つ", len(M) == 100 and [m["word"] for m in M] == names and len(M[0]) == 7)
rep = "ちんちん,こすこす,べろべろ,ちゅぱちゅぱ,びくびく,どきどき,びんびん,じんじん,ぱんぱん,ぱこぱこ,くちゅくちゅ,こびこび,めろめろ,いけいけ,つんつん,しめしめ,すきすき".split(",")
ah = "あんっ,ああっ,ああん,おおっ,んおっ,んおお,んんっ,うおお,あんあん,うんっ".split(",")
mem = {m["word"]: m for m in M}
ok("反復17語の1周目メモに、すべて「神」または「王」が入っている", len(rep) == 17 and all(("神" in mem[w]["1周目の研究メモ"] or "王" in mem[w]["1周目の研究メモ"]) for w in rep))
ok("喘ぎ声10語の1周目メモに、すべて「聖句」が入っている", len(ah) == 10 and all("聖句" in mem[w]["1周目の研究メモ"] for w in ah))
bad = [(m["no"], k, b) for m in M for k, v in m.items() for b in ("古代", "古語", "古名", "古形", "昔", "遺跡", "時代", "太古") if b in v]
ok("「古代」「古語」「古名」「古形」「昔」「遺跡」「時代」「太古」が、どの列にも出てこない", not bad)
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
