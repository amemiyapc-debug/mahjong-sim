"""一周版100語・山156枚の測定(20261008 依頼。測定のみ。ルール・語・点数は変えない)。
  python3 ichishuu/sim_ichishuu.py [--games 1000] [--seed 20261008] [--procs 4]
入力: data/words_ichishuu100.csv(100語)・data/tile_usage_100.csv・data/phrase_pairs_draft.csv(句30組)。雀頭の辞書は dan6/heads.csv から選ぶ(仮定。報告に記載)。
CPU: sim14.Game の cpu="hint"(牌効率のヒント。これまで「強CPU」としてきたもの)。1ゲームのツモ回数 L=12(感度: 10・14)。"""
import argparse, csv, json, math, os, random, sys, hashlib, time
from collections import Counter
from multiprocessing import Pool
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from judge14 import Judge14
from sim14 import Game

rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
DATA = os.path.join(ROOT, "data"); D6 = os.path.join(ROOT, "dan6")
NORM = {"っ": "つ", "ぉ゛": "お"}


def load():
    W100 = rd(os.path.join(DATA, "words_ichishuu100.csv"))
    pairs = rd(os.path.join(DATA, "phrase_pairs_draft.csv"))
    usage = rd(os.path.join(DATA, "tile_usage_100.csv"))
    return W100, pairs, usage


def verify(W100, pairs, usage, heads_all):
    """入力の検証(受け入れ条件)。返り値: dict"""
    out = {}
    d6 = {w["word"]: w for w in rd(os.path.join(D6, "words.csv"))}
    d6_read = {}
    for w in d6.values():                                   # 「・」併記の語は、読みごとに引けるようにする
        for r in w["word"].split("・"): d6_read.setdefault(r, w)
    miss, diff = [], []
    for w in W100:
        x = d6_read.get(w["word"])
        if x is None: miss.append(w["word"]); continue
        if sorted(x["tiles"].split("|")) != sorted(w["tiles"].split("|")) or x["slot"] != w["slot"] or x["sub"] != w["sub"]:
            diff.append((w["word"], x["tiles"], w["tiles"], x["slot"], w["slot"], x["sub"], w["sub"]))
    out["words_n"] = len(W100); out["words_unique"] = len({w["word"] for w in W100})
    out["words_not_in_words_csv"] = miss; out["words_differ"] = diff
    out["tiles3"] = all(len(w["tiles"].split("|")) == 3 for w in W100)
    used = Counter()
    for w in W100: used.update(set(w["tiles"].split("|")))
    out["used"] = dict(used); out["tile_types"] = len(used)
    copies = {t: min(10, max(2, math.ceil(u / 2))) for t, u in used.items()}
    out["copies"] = copies; out["wall"] = sum(copies.values()); out["x2_copies"] = copies.get("×2")
    file_used = {r["tile"]: int(r["used_in_words"]) for r in usage}; file_old = {r["tile"]: int(r["copies_old_rule"]) for r in usage}
    out["used_diff"] = {t: (used.get(t), file_used.get(t)) for t in set(used) | set(file_used) if used.get(t) != file_used.get(t)}
    out["copies_diff"] = {t: (copies.get(t), file_old.get(t)) for t in set(copies) | set(file_old) if copies.get(t) != file_old.get(t)}
    out["file_wall"] = sum(file_old.values())
    out["single_use_tiles"] = [t for t, u in used.items() if u == 1]
    out["two_use_tiles"] = sorted(t for t, u in used.items() if u == 2)
    names = {w["word"] for w in W100}
    out["pairs_n"] = len(pairs); out["pairs_missing"] = [(i + 2, p["word_a"], p["word_b"]) for i, p in enumerate(pairs) if p["word_a"] not in names or p["word_b"] not in names]
    out["pairs_dup"] = len(pairs) - len({frozenset((p["word_a"], p["word_b"])) for p in pairs})
    # 雀頭の辞書(仮定): dan6/heads.csv のうち、2牌とも、100語の山にある牌(つ=っ)で作れるもの
    wall_types = {NORM.get(t, t) for t in copies}
    out["heads_all"] = len(heads_all)
    out["heads"] = [h for h in heads_all if all(NORM.get(t, t) in wall_types for t in h["tiles"].split("|"))]
    out["heads_excluded"] = [h["head"] for h in heads_all if h not in out["heads"]]
    return out


class PartScorer:
    """役・点を数えず、14枚が「別々の4語+雀頭」に分けられるか(アガリ)だけを見る。"""
    def __init__(self, judge): self.judge = judge
    def best(self, hand):
        parts = self.judge.partitions(hand)
        if not parts: return None
        ws, h, oho, chu = parts[0]
        return dict(han=0, han_no_merge=0, yaku=[], merges=[], raw=[], words=ws, head=h, parts=len(parts))


_G = None


def _init(W100, heads, copies, L, cpu, tmpdir):
    global _G
    J = Judge14(os.path.join(tmpdir, "words.csv"), os.path.join(tmpdir, "heads.csv"), os.path.join(D6, "tile_variants.csv"))
    _G = Game(None, copies, L, scorer=PartScorer(J), cpu=cpu)


def _run(args):
    seed, n = args
    return [_G.play(random.Random(seed + k)) for k in range(n)]


def write_dict(tmpdir, W100, heads):
    os.makedirs(tmpdir, exist_ok=True)
    with open(os.path.join(tmpdir, "words.csv"), "w", encoding="utf-8-sig", newline="") as f:
        c = csv.writer(f); c.writerow(["word", "tiles"]); [c.writerow([w["word"], w["tiles"]]) for w in W100]
    with open(os.path.join(tmpdir, "heads.csv"), "w", encoding="utf-8-sig", newline="") as f:
        c = csv.writer(f); c.writerow(["head", "tiles"]); [c.writerow([h["head"], h["tiles"]]) for h in heads]


def play_all(W100, heads, copies, L, n, seed, procs, cpu, tmpdir):
    write_dict(tmpdir, W100, heads)
    chunk = 25
    jobs = [(seed + i, min(chunk, n - i)) for i in range(0, n, chunk)]
    with Pool(procs, initializer=_init, initargs=(W100, heads, copies, L, cpu, tmpdir)) as p:
        res = []
        for part in p.imap(_run, jobs): res += part
    return res


def analyse(games, W100, pairs, heads, tmpdir):
    J = Judge14(os.path.join(tmpdir, "words.csv"), os.path.join(tmpdir, "heads.csv"), os.path.join(D6, "tile_variants.csv"))
    idx = {w["word"]: i for i, w in enumerate(J.words)}
    wins = [g for g in games if g["result"] == "win"]
    n = len(games)
    r = dict(games=n, wins=len(wins), win_rate=100 * len(wins) / n, tenpai=sum(g["result"] == "tenpai" for g in games), noten=sum(g["result"] == "noten" for g in games))
    r["mean_turn_win"] = sum(g["turn"] for g in wins) / len(wins) if wins else None
    r["turn_dist_win"] = dict(sorted(Counter(g["turn"] for g in wins).items()))
    pc = Counter(); anyp = Counter(); per_hand = []; nparts = []; uniq = 0; uniq_pc = Counter()
    for g in wins:
        parts = J.partitions(g["hand"]); nparts.append(len(parts)); sets = [frozenset(p[0]) for p in parts]
        got = set()
        for i, p in enumerate(pairs):
            a, b = idx[p["word_a"]], idx[p["word_b"]]
            if any(a in s and b in s for s in sets): got.add(i)
        for i in got: pc[i] += 1
        per_hand.append(len(got))
        if len(parts) == 1:
            uniq += 1
            for i in got: uniq_pc[i] += 1
    nw = len(wins)
    r["pair_rate"] = {i: 100 * pc[i] / nw for i in range(len(pairs))}
    r["pair_rate_unique"] = {i: (100 * uniq_pc[i] / uniq if uniq else None) for i in range(len(pairs))}
    r["mean_pairs_per_win"] = sum(per_hand) / nw; r["win_with_ge1_pair"] = 100 * sum(1 for x in per_hand if x >= 1) / nw
    r["overall_pair_share"] = 100 * sum(per_hand) / (nw * len(pairs)); r["mean_partitions"] = sum(nparts) / nw; r["unique_partition_hands"] = uniq
    r["pairs_zero"] = [i for i in range(len(pairs)) if pc[i] == 0]
    r["digest"] = hashlib.sha256(json.dumps([(g["result"], g["turn"], g.get("hand")) for g in games], ensure_ascii=False).encode()).hexdigest()[:16]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1000); ap.add_argument("--seed", type=int, default=20261008)
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--out", default=os.path.join(ROOT, "ichishuu", "results_20261008.json"))
    ap.add_argument("--tmp", default=os.path.join(ROOT, "ichishuu", "_dict"))
    a = ap.parse_args()
    W100, pairs, usage = load()
    heads_all = rd(os.path.join(D6, "heads.csv"))
    v = verify(W100, pairs, usage, heads_all)
    heads = v["heads"]; copies = v["copies"]
    print("検証:", {k: v[k] for k in v if k not in ("heads", "used", "copies")})
    out = dict(verify={k: (v[k] if k != "heads" else [h["head"] for h in heads]) for k in v}, runs={})
    cfgs = [("L12_main", 12, heads, "hint"), ("L10", 10, heads, "hint"), ("L14", 14, heads, "hint"),
            ("L12_head_aegigoe_only", 12, [h for h in heads if h["type"] == "喘ぎ声"], "hint")]
    for name, L, hs, cpu in cfgs:
        t0 = time.time()
        g = play_all(W100, hs, copies, L, a.games, a.seed, a.procs, cpu, a.tmp)
        r = analyse(g, W100, pairs, hs, a.tmp); r["L"] = L; r["heads_n"] = len(hs); r["cpu"] = cpu
        out["runs"][name] = r; print(f"{name}: アガリ率 {r['win_rate']:.1f}% 平均ツモ {r['mean_turn_win']:.2f} ({time.time()-t0:.0f}秒) digest {r['digest']}", flush=True)
    # 同じシードで、もう一度(L=12)。結果が一致するか
    g2 = play_all(W100, heads, copies, 12, a.games, a.seed, a.procs, "hint", a.tmp)
    r2 = analyse(g2, W100, pairs, heads, a.tmp)
    out["rerun"] = dict(digest=r2["digest"], same=(r2["digest"] == out["runs"]["L12_main"]["digest"]), win_rate=r2["win_rate"], mean_turn_win=r2["mean_turn_win"])
    print("再実行: digest", r2["digest"], "一致:", out["rerun"]["same"])
    out["pairs"] = [(p["word_a"], p["word_b"]) for p in pairs]
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("→", a.out)


if __name__ == "__main__":
    main()
