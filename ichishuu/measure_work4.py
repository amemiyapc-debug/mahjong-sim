"""20261010-1925 作業4 の測定: C 見本の仕込み(ちんぽ+まんこ)の有無 / E 見送りの期待値(研究♡1・2)。強CPU(hint)・一周版100語・残りツモ12・seed 20261008+i。
  python3 ichishuu/measure_work4.py c|e [N]
C: 最初の1ゲームだけの配牌。仕込みあり(ちんぽ・まんこの牌6枚を配牌に入れる)・なしで、「和了した手の分け方のどれかに ちんぽ と まんこ が両方入る」率と、和了率。
E: 研究♡1・2(見送り2回・3回。1ステージで共有)。ステージ1(句=2語つながる)・2(節=3語)の挑戦を、方針ごとに測る: 確定(見送らない)/ 点が低ければ見送る(しきい値=確定したときの点の25・50・75%点)/ 条件を満たさなければ見送る。"""
import json, os, sys, random, statistics, itertools
from multiprocessing import Pool
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "ichishuu")); sys.path.insert(0, os.path.join(ROOT, "dan6"))
import sim_ichishuu as S
import goro14 as G
from judge14 import Judge14
from yaku14 import Scorer
from sim14 import Game
SEED, L = 20261008, 12
_g = {}


def _init(tmp, copies, W100):
    J = Judge14(os.path.join(tmp, "words.csv"), os.path.join(tmp, "heads.csv"), os.path.join(S.D6, "tile_variants.csv"))
    Sc = Scorer(S.D6); rd = {}
    for w in Sc.W:
        for r in w["word"].split("・"): rd.setdefault(r, w["word"])
    _g.update(J=J, Sc=Sc, rd=rd, jn=[w["word"] for w in J.words], G=Game(None, copies, L, scorer=S.PartScorer(J), cpu="hint"), W100={w["word"]: w["tiles"].split("|") for w in W100})


def best(hand, lv):
    """14牌の、解読点が最大の分け方(研究♡ lv)。返り値 dict(points, size, theme_k, names)"""
    J, Sc, rd, jn = _g["J"], _g["Sc"], _g["rd"], _g["jn"]; out = None
    for ws, h, oho, chu in J.partitions(hand):
        nm = [rd[jn[j]] for j in ws]; hd = J.heads[h]["head"]
        r = Sc.score([Sc.widx[n] for n in nm], next(k for k, x in enumerate(Sc.H) if x["head"] == hd), oho)
        yin = G.yaku_in(Sc, r); sc = G.score(nm, hd, G.params(lv), yin); k = (sc["points"], yin)
        if out is None or k > out[0]: out = (k, dict(points=sc["points"], size=sc["size"], theme_k=sc["theme_k"], names=nm))
    return out[1] if out else None


def both(hand):   # 和了した手の分け方のどれかに、ちんぽ と まんこ が両方入るか
    J, jn = _g["J"], _g["jn"]
    return any({"ちんぽ", "まんこ"} <= {jn[j] for j in ws} for ws, h, oho, chu in J.partitions(hand))


def job_c(a):
    seed, seeded = a; g = _g["G"]; st = None
    if seeded:
        st = [t for n in ("ちんぽ", "まんこ") for t in _g["W100"][n]]
    r = g.play(random.Random(seed), seed_tiles=st)
    return dict(win=r["result"] == "win", both=(r["result"] == "win" and both(r["hand"])))


def sat(b, cond):
    return b["size"] >= 2 if cond == 1 else b["size"] >= 3 if cond == 2 else (b["size"] >= 3 and b["theme_k"] >= 3)


def job_e(a):
    """1回のステージ挑戦(3ゲーム。テンパイ流局は消費しない。見送りは1ステージで共有)。"""
    seed, lv, cond, policy, T = a; g = _g["G"]; rng = random.Random(seed)
    skips = G.SKIPS[lv]; used = 0; wins = 0; pts = 0; nowin = 0; skipped = 0; fails = 0; played = 0
    cleared = False
    while used < 3:
        ev = {"skips": skips}
        def skip(hand, turn, r):
            if ev["skips"] <= 0 or policy == "take": return False
            b = best(hand, lv)
            if policy == "low": take = b["points"] < T
            elif policy == "seek": take = not sat(b, cond)
            else: take = True
            if take: ev["skips"] -= 1; return True
            return False
        res = g.play(rng, skip if policy != "take" else None); played += 1
        skips = ev["skips"]
        if res["result"] == "tenpai": continue
        used += 1
        if res["result"] == "win":
            b = best(res["hand"], lv); wins += 1; pts += b["points"]
            if sat(b, cond): cleared = True; break
        else:
            nowin += 1
            if res.get("skipfail"): fails += 1
    return dict(cleared=cleared, used=used, wins=wins, pts=pts, nowin=nowin, skipfail=fails, played=played, skipped=G.SKIPS[lv] - skips)


def main():
    mode = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else (1000 if mode == "c" else 400)
    W100, pairs, usage = S.load(); v = S.verify(W100, pairs, usage, S.rd(os.path.join(S.D6, "heads.csv")))
    tmp = os.path.join(ROOT, "ichishuu", "_dict"); S.write_dict(tmp, W100, v["heads"])
    out = {}
    with Pool(4, initializer=_init, initargs=(tmp, v["copies"], W100)) as p:
        if mode == "c":
            for seeded in (False, True):
                rs = p.map(job_c, [(SEED + i, seeded) for i in range(N)], chunksize=10)
                out["仕込みあり" if seeded else "仕込みなし"] = dict(n=N, win_rate=100 * sum(r["win"] for r in rs) / N, both_rate=100 * sum(r["both"] for r in rs) / N)
                print(seeded, out["仕込みあり" if seeded else "仕込みなし"], flush=True)
        else:
            _init(tmp, v["copies"], W100)
            for lv in (1, 2):
                for cond in (1, 2):
                    # 確定したときの点の分布(しきい値の基準)
                    base = p.map(job_e, [(SEED + i, lv, cond, "take", 0) for i in range(N)], chunksize=5)
                    wp = sorted(b["pts"] for b in base if b["wins"])
                    q = lambda f: wp[int(len(wp) * f)] if wp else 0
                    pol = [("take", 0), ("low", q(.25)), ("low", q(.5)), ("low", q(.75)), ("seek", 0)]
                    for name, T in pol:
                        rs = base if name == "take" else p.map(job_e, [(SEED + i, lv, cond, name, T) for i in range(N)], chunksize=5)
                        used = sum(r["used"] for r in rs)
                        out[f"lv{lv}_cond{cond}_{name}_{int(T)}"] = dict(lv=lv, cond=cond, policy=name, T=T, n=N,
                            clear=100 * sum(r["cleared"] for r in rs) / N, E_pts_per_attempt=sum(r["pts"] for r in rs) / N, E_pts_per_consumed_game=sum(r["pts"] for r in rs) / max(1, used),
                            win_per_consumed=100 * sum(r["wins"] for r in rs) / max(1, used), nowin_per_consumed=100 * sum(r["nowin"] for r in rs) / max(1, used),
                            skipfail_per_attempt=sum(r["skipfail"] for r in rs) / N, skipped_per_attempt=sum(r["skipped"] for r in rs) / N, played_per_attempt=sum(r["played"] for r in rs) / N)
                        print(f"lv{lv} 条件{cond} {name:5} T={int(T):>9} → クリア {out[f'lv{lv}_cond{cond}_{name}_{int(T)}']['clear']:.1f}% 点/挑戦 {out[f'lv{lv}_cond{cond}_{name}_{int(T)}']['E_pts_per_attempt']:.0f} ノーテン/消費 {out[f'lv{lv}_cond{cond}_{name}_{int(T)}']['nowin_per_consumed']:.1f}%", flush=True)
    json.dump(out, open(os.path.join(ROOT, "ichishuu", f"results_work4_{mode}_20261010.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
