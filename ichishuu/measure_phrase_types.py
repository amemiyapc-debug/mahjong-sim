"""句の型の出やすさの測定(20261008-2030)。強CPU(既存の hint)・1,000試合・シード 20261008+i・残りツモ12。測定のみ(上限や型の数の調整は、実装しない)。
3条件: (a) 看板30組のみ / (b) 看板+型1〜5 / (c) 看板+9型(除外条件つき)。同じ1,000試合の和了手を、3条件で数える(句の判定はプレイに使わない)。
  python3 ichishuu/measure_phrase_types.py"""
import json, os, sys, itertools, hashlib
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu"))
import sim_ichishuu as S
from phrase_types import PhraseBook, parse_filter, match
from judge14 import Judge14

GAMES, SEED, L = 1000, 20261008, 12
CONDS = {"a_看板のみ": (True, ()), "b_看板+型1〜5": (True, ("1", "2", "3", "4", "5")), "c_看板+9型": (True, ("1", "2", "3", "4", "5", "6", "7", "8", "10"))}


def main():
    W100, pairs, usage = S.load(); heads_all = S.rd(os.path.join(S.D6, "heads.csv"))
    v = S.verify(W100, pairs, usage, heads_all); heads = v["heads"]; copies = v["copies"]
    tmp = os.path.join(ROOT, "ichishuu", "_dict")
    games = S.play_all(W100, heads, copies, L, GAMES, SEED, 4, "hint", tmp)
    digest = hashlib.sha256(json.dumps([(g["result"], g["turn"], g.get("hand")) for g in games], ensure_ascii=False).encode()).hexdigest()[:16]
    J = Judge14(os.path.join(tmp, "words.csv"), os.path.join(tmp, "heads.csv"), os.path.join(S.D6, "tile_variants.csv"))
    names = [w["word"] for w in J.words]
    book = PhraseBook()
    wins = [g for g in games if g["result"] == "win"]
    # 和了手ごとの、分け方(4語の名前の集合)
    parts = [[frozenset(names[i] for i in p[0]) for p in J.partitions(g["hand"])] for g in wins]
    out = dict(games=GAMES, wins=len(wins), win_rate=100 * len(wins) / GAMES, digest=digest, same_games_as_ichishuu_run=(digest == "e4eadad994d27ee3"),
               type_counts={tid: len(book.type_pairs[tid]) for tid in book.type_pairs}, type_names=book.type_name,
               type_overlap_signboard={tid: len(book.type_pairs[tid] & book.signboard) for tid in book.type_pairs}, conds={})
    allw = set(book.by_name)
    for cname, (sb, tids) in CONDS.items():
        S_ = book.phrases(sb, tids)
        n_union, n_best, label_c, per_pair = [], [], Counter(), Counter()
        for ps in parts:
            sets = [{frozenset(c) for c in itertools.combinations(sorted(p), 2)} & S_ for p in ps]
            u = set().union(*sets) if sets else set()
            n_union.append(len(u)); n_best.append(max(len(s) for s in sets))
            for ph in u:
                per_pair[ph] += 1
                for lab in book.labels(ph, tids): label_c[lab] += 1
        nw = len(wins); tot_games = GAMES
        r = dict(n_phrases_defined=len(S_), win_with_ge1_union=100 * sum(1 for x in n_union if x >= 1) / nw, win_with_ge1_best=100 * sum(1 for x in n_best if x >= 1) / nw,
                 mean_per_win_union=sum(n_union) / nw, max_union=max(n_union), mean_per_game_union=sum(n_union) / tot_games, mean_per_win_best=sum(n_best) / nw, max_best=max(n_best),
                 mean_per_game_best=sum(n_best) / tot_games, per_9_games_union=9 * sum(n_union) / tot_games, per_9_games_best=9 * sum(n_best) / tot_games,
                 dist_union=dict(sorted(Counter(n_union).items())), labels={str(k): c for k, c in label_c.items()}, label_total=sum(label_c.values()),
                 distinct_phrases_seen=len(per_pair), per_type_distinct_seen={str(t): sum(1 for ph in per_pair if ph in book.type_pairs[t]) for t in tids},
                 signboard_seen=sum(1 for ph in per_pair if ph in book.signboard), signboard_zero=[sorted(p) for p in book.signboard if p not in per_pair])
        out["conds"][cname] = r
    # 除外条件なしの数(参考)
    book0 = PhraseBook(rules=[])
    out["type_counts_no_rules"] = {tid: len(book0.type_pairs[tid]) for tid in book0.type_pairs}
    json.dump(out, open(os.path.join(ROOT, "ichishuu", "results_phrase_types_20261008.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("games", "wins", "win_rate", "digest", "same_games_as_ichishuu_run", "type_counts", "type_counts_no_rules")}, ensure_ascii=False))
    for c, r in out["conds"].items():
        print(c, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in r.items() if k not in ("labels", "per_type_distinct_seen", "dist_union", "signboard_zero")})
        print("   labels", r["labels"], "type_distinct", r["per_type_distinct_seen"], "dist", r["dist_union"])


if __name__ == "__main__":
    main()
