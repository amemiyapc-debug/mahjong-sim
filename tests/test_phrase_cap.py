"""1手に表示・記録する句の上限と選び方(20261008-2100)。 python3 tests/test_phrase_cap.py"""
import os, sys, random, itertools
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "ichishuu"))
import phrase_types as PT
ng = 0
def ok(m, c):
    global ng; print(("OK  " if c else "NG  ") + m); ng += (not c)
b = PT.PhraseBook(); names = sorted(b.by_name); cfg = PT.load_config(); freq = PT.load_type_frequency()
TIDS = tuple(b.type_pairs)
ok("上限は設定ファイル(data/phrase_config.csv)の PHRASE_CAP_PER_HAND=1。句の固定点 PHRASE_POINTS は未決(空欄)", cfg["PHRASE_CAP_PER_HAND"] == 1 and cfg["PHRASE_POINTS"] is None)
ok("型ごとの出現回数が設定ファイルにあり、9型すべて", set(freq) == set(TIDS))
rng0 = random.Random(1)
hands = [rng0.sample(names, 4) for _ in range(3000)]
cands = [{frozenset(c) for c in itertools.combinations(h, 2)} & b.phrases(True, TIDS) for h in hands]
sel1 = [PT.select_phrases(c, b, TIDS, random.Random(i)) for i, c in enumerate(cands)]
ok("1手に表示される句が2つ以上にならない(無作為の4語×3,000手。うち句が成立 %d手)" % sum(1 for c in cands if c), max(len(s) for s in sel1) <= 1 and sum(1 for c in cands if c) > 500)
ok("句が成立した手では、必ず1つ選ばれる(成立しない手は0)", all((len(s) == 1) == bool(c) for s, c in zip(sel1, cands)))
sbh = [(c, s) for c, s in zip(cands, sel1) if any(p in b.signboard for p in c)]
ok("看板が成立した手では、必ず看板が選ばれる(%d手)" % len(sbh), len(sbh) > 5 and all(s[0] in b.signboard for c, s in sbh))
nsb = [(c, s) for c, s in zip(cands, sel1) if c and not any(p in b.signboard for p in c)]
def tmin(c): return min(freq[t] for t in TIDS if any(p in b.type_pairs[t] for p in c))
ok("看板がないときは、成立した型のうち、出現回数が最も少ない型から選ぶ(%d手)" % len(nsb), all(freq[PT.classify(s[0], b, TIDS)] == tmin(c) for c, s in nsb))
ok("seedが同じなら、選ばれる句も同じ", [PT.select_phrases(c, b, TIDS, random.Random(i)) for i, c in enumerate(cands)] == sel1)
ok("seedが違うと、選ばれる句が変わりうる(同じ手でも)", any(PT.select_phrases(c, b, TIDS, random.Random(i + 99999)) != s for i, (c, s) in enumerate(zip(cands, sel1)) if len(c) > 2))
sel0 = [PT.select_phrases(c, b, TIDS, random.Random(i), cap=0) for i, c in enumerate(cands)]
sel2 = [PT.select_phrases(c, b, TIDS, random.Random(i), cap=2) for i, c in enumerate(cands)]
ok("上限の定数を変えると、結果が変わる(0なら表示なし、2なら最大2つ)", sum(len(s) for s in sel0) == 0 and max(len(s) for s in sel2) == 2 and sum(len(s) for s in sel2) > sum(len(s) for s in sel1))
ok("選ばれた句は、成立した句の中にある(成立していない句は選ばれない)", all(set(s) <= c for s, c in zip(sel1, cands)))
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
