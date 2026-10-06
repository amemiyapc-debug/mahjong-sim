"""ひらがな麻雀(仮) v1.3m シミュレーター(14牌形・固定の山・強CPUの自動プレイ)。仕様は CLAUDE.md(v1.3m)。

  python3 sim14.py --dir v13m --games 3000 --L 12 --out results_v1.3m      # 条件A(新ルール)とB(旧ルール)を測る
  python3 sim14.py --dir v13m --check-tiles                                 # 牌の枚数ルールの確認だけ

構成:
  1. 牌の枚数ルール(tile_copies): 'new' = min(10,max(2,ceil(使う語・雀頭の数/2)))+修飾牌の加算 / 'old' = max(4,使う語・雀頭の数)。ぉ゛は4枚固定。
  2. 1ゲーム: 手牌13枚、ツモ(14枚)→アガリ判定→1枚捨て、を最大L回。アガリ判定と役・合体・翻の選択は yaku14.Scorer(judge14 の分割ごと)。
     L回目の捨ての後、13枚がテンパイ(待ち牌が山に残っている)ならテンパイ流局、そうでなければノーテン。
  3. 強CPU: (a) 捨てた後にテンパイになる捨て牌があれば、待ち牌の山の残り枚数が最大のものを選ぶ(全4語+雀頭の全数探索。厳密)。
     (b) なければ、牌効率のヒント(game/core.js の analyze と同じ。完成した語・あと1枚の語・雀頭のまとまりを最大にし、余りの牌から、
         その牌を含む語の数が最小のものを捨てる)。山の残りは、見えている(手牌・捨て牌以外)ものとして数える。
     牌の変種: ぉ゛=お、っ=つ(置き換え)、ちゅ→つ(一方向。ちゅを何枚つとして使うかを試す)。捨てるときは、ぉ゛・ちゅを残す。
  4. 出力: 各条件のアガリ率・累積テンパイ率・翻・点・役・合体・語・牌のCSV。
"""
import argparse
import csv
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

from yaku14 import Scorer, read_rows

MOD_TILES = ("見せ", "デカ", "エロ", "ぬれ", "穴", "媚び", "♡", "舐め", "コキ")
HAND = 13


def points(han):
    """満貫制(CLAUDE.md §6-1)。"""
    if han <= 4:
        return han * 1000
    return 8000 if han == 5 else 12000 if han <= 7 else 16000 if han <= 10 else 24000 if han <= 12 else 32000


# ---------------------------------------------------------------- 牌の枚数ルール
def tile_usage(d):
    """牌ごとの、使う語・雀頭の数(修飾3型の語は数えない)と、修飾3型の需要(修飾3型の語で使う牌の枚数)。"""
    W = read_rows(os.path.join(d, "words.csv"))
    H = read_rows(os.path.join(d, "heads.csv"))
    used, demand = Counter(), Counter()
    for w in W:
        ts = w["tiles"].split("|")
        if w["type"] == "修飾3型":
            demand.update(ts)
        else:
            used.update(set(ts))
    for h in H:
        used.update(set(h["tiles"].split("|")))
    return used, demand


def tile_copies(d, rule="new", modx=0.1, x2=13):
    """牌 -> 枚数(ぉ゛を含む)。rule: 'new'(v1.3m)/ 'old'(v1.3〜v1.3l)。
    modx: 修飾牌に足す、前置き(修飾3型)の需要の割合(既定0.1)。x2: 新しい牌 ×2 の枚数(dan5。辞書に ×2 があるときだけ。既定13)。"""
    used, demand = tile_usage(d)
    V = read_rows(os.path.join(d, "tile_variants.csv"))
    copies = {}
    for t, u in used.items():
        if rule == "new":
            c = min(10, max(2, math.ceil(u / 2)))
            if t in MOD_TILES:
                c += int(demand[t] * modx + 0.5)      # 四捨五入(0.5は切り上げ)
        elif rule == "old":
            c = max(4, u)
        else:
            raise ValueError(rule)
        copies[t] = c
        if t == "×2": copies[t] = x2                # ×2 は、枚数を固定(dan5)
    for v in V:
        if int(v["copies"]) > 0:
            copies[v["tile"]] = int(v["copies"])        # ぉ゛ 4枚(固定)
    return copies


def check_tiles(d):
    """新ルールの枚数が、tile_copies_adopted.csv と一致するか。山の枚数・牌の種類も出す。"""
    new = tile_copies(d, "new")
    ad = {r["tile"]: int(r["copies"]) for r in read_rows(os.path.join(d, "tile_copies_adopted.csv"))}
    diff = {t: (new.get(t), ad.get(t)) for t in set(new) | set(ad) if t != "ぉ゛" and new.get(t) != ad.get(t)}
    old = tile_copies(d, "old")
    used, _ = tile_usage(d)
    ad_used = {r["tile"]: int(r["used_in_words"]) for r in read_rows(os.path.join(d, "tile_copies_adopted.csv"))}
    used_diff = {t: (used.get(t), ad_used.get(t)) for t in set(used) | set(ad_used) if used.get(t) != ad_used.get(t)}
    return dict(new_total=sum(new.values()), new_types=len([t for t in new if t != "ぉ゛"]), old_total=sum(old.values()),
                diff=diff, used_diff=used_diff, oho=new.get("ぉ゛"))


# ---------------------------------------------------------------- CPU・ゲーム
class Game:
    def __init__(self, d, copies, L=12, scorer=None, cpu="hint"):
        self.cpu = cpu
        self.S = scorer or Scorer(d)
        J = self.S.judge
        self.J, self.L = J, L
        self.norm = J.replace                                        # ぉ゛→お, っ→つ
        self.flex = J.flex[0] if J.flex else None                    # (ちゅ, つ)
        self.wall0 = [t for t, n in sorted(copies.items()) for _ in range(n)]
        self.Wn = [(tuple(c), dict(c)) for c in J.word_tiles]
        self.Hn = [(tuple(c), dict(c)) for c in J.head_tiles]
        self.Wt = J.words_by_tile
        self.Ht = J.heads_by_tile
        # 牌(正規化後) -> 供給できる山の牌
        self.supply_of = defaultdict(list)
        for t in copies:
            self.supply_of[self.norm.get(t, t)].append(t)
        if self.flex:
            self.supply_of[self.flex[1]].append(self.flex[0])        # つ は ちゅ でも補える
        self.supply_of = {k: sorted(set(v)) for k, v in self.supply_of.items()}

    # --- 山の残り(実牌) -> 正規化した牌ごとの補給枚数 ---
    def supply(self, wc):
        return {k: sum(wc.get(t, 0) for t in v) for k, v in self.supply_of.items()}

    def blocks(self, c, sup, tbl, by_tile):
        """牌の集まり c に対して、完成した語(0)・あと1枚(1。その牌は山にある)の一覧 [(index, miss, 足りない牌)]。"""
        seen, out = set(), []
        for t in c:
            if c[t] <= 0:
                continue
            for i in by_tile.get(t, ()):
                if i in seen:
                    continue
                seen.add(i)
                kinds, need = tbl[i]
                miss, mt = 0, None
                for k in kinds:
                    m = need[k] - c.get(k, 0)
                    if m > 0:
                        miss += m
                        mt = k
                if miss == 0:
                    out.append((i, 0, None))
                elif miss == 1 and sup.get(mt, 0) > 0:
                    out.append((i, 1, mt))
        return out

    # --- (a) テンパイになる捨て牌の全数探索 ---
    def tenpai_options(self, c, sup):
        """14牌 c(正規化後)から1枚捨てて、テンパイ(あと1枚で4語+雀頭。待ち牌は山にある)になる捨て牌。
        戻り値 {捨てる牌: {待ち牌...}}。13牌 c のときは、テンパイなら {None: {待ち牌...}}(捨てる牌はない)。"""
        n13 = sum(c.values()) == HAND
        ws = self.blocks(c, sup, self.Wn, self.Wt)
        hs = self.blocks(c, sup, self.Hn, self.Ht)
        if not hs or len(ws) < 3:
            return {}
        r = dict(c)
        opts = {}
        Wn, Hn = self.Wn, self.Hn

        def take(kinds, need):
            m, mt, taken = 0, None, []
            for k in kinds:
                have = r.get(k, 0)
                x = need[k] - have
                if x > 0:
                    m += x
                    mt = k
                    n = have
                else:
                    n = need[k]
                if n:
                    taken.append((k, n))
            return m, mt, taken

        def dfs(start, k, miss, mt):
            if k == 4:
                for hi, _, _ in hs:
                    kinds, need = Hn[hi]
                    hm, hmt, taken = take(kinds, need)
                    if miss + hm != 1:
                        continue
                    for t_, n in taken:
                        r[t_] -= n
                    left = [t_ for t_, n in r.items() if n > 0]
                    if n13:
                        if not left:
                            opts.setdefault(None, set()).add(hmt if hm else mt)
                    elif len(left) == 1 and r[left[0]] == 1:
                        opts.setdefault(left[0], set()).add(hmt if hm else mt)
                    for t_, n in taken:
                        r[t_] += n
                return
            for j in range(start, len(ws)):
                kinds, need = Wn[ws[j][0]]
                m, mtt, taken = take(kinds, need)
                if miss + m > 1:
                    continue
                for t_, n in taken:
                    r[t_] -= n
                dfs(j + 1, k + 1, miss + m, mtt if m else mt)
                for t_, n in taken:
                    r[t_] += n

        dfs(0, 0, 0, None)
        return opts

    # --- (b) 牌効率のヒント(core.js の analyzeOne と同じ) ---
    def hint(self, c, sup):
        cw = sorted(((i, m, mt) for i, m, mt in self.blocks(c, sup, self.Wn, self.Wt)),
                    key=lambda x: (x[1], -(sup.get(x[2], 0) if x[2] else 0)))[:24]
        ch = sorted(((i, m, mt) for i, m, mt in self.blocks(c, sup, self.Hn, self.Ht)),
                    key=lambda x: (x[1], -(sup.get(x[2], 0) if x[2] else 0)))[:8]

        def mk(tbl, items, is_head):
            out = []
            for i, m, mt in items:
                kinds, need = tbl[i]
                out.append((is_head, m == 0, m, mt, {k: min(c[k], need[k]) for k in kinds if c.get(k, 0) > 0}))
            return out
        top = mk(self.Wn, cw, False) + mk(self.Hn, ch, True)
        best = [None, []]
        chosen = []
        cc = dict(c)

        def score():
            ws = [x for x in chosen if not x[0]]
            hd = [x for x in chosen if x[0]]
            comp = sum(1 for x in ws if x[1])
            miss, uke = set(), 0
            for x in chosen:
                if not x[1] and x[3] not in miss:
                    miss.add(x[3])
                    uke += sup.get(x[3], 0)
            sc = len(ws) * 100000 + comp * 10000 + (4000 if hd and hd[0][1] else 2000 if hd else 0) + min(uke, 999)
            if best[0] is None or sc > best[0]:
                best[0], best[1] = sc, chosen[:]

        def dfs(s, nw, nh):
            score()
            for j in range(s, len(top)):
                x = top[j]
                if (nh >= 1) if x[0] else (nw >= 4):
                    continue
                if any(cc.get(k, 0) < n for k, n in x[4].items()):
                    continue
                for k, n in x[4].items():
                    cc[k] -= n
                chosen.append(x)
                dfs(j + 1, nw + (0 if x[0] else 1), nh + (1 if x[0] else 0))
                chosen.pop()
                for k, n in x[4].items():
                    cc[k] += n
        dfs(0, 0, 0)
        rest = dict(c)
        for x in best[1]:
            for k, n in x[4].items():
                rest[k] -= n
        rest_tiles = [t for t, n in rest.items() if n > 0]
        if not rest_tiles:
            rest_tiles = [t for t, n in c.items() if n > 0]

        def pot(t):
            p = 0
            for i in self.Wt.get(t, ()):
                kinds, need = self.Wn[i]
                o = sum(min(c.get(u, 0), need[u]) for u in kinds if u != t)
                if o >= 1:
                    p += 1
            return p
        return best[0] or 0, min(rest_tiles, key=lambda t: (pot(t), sup.get(t, 0), t))

    def interpretations(self, hand):
        """正規化した牌の数え方。ちゅを、つとして使う枚数 b ごと。"""
        base = Counter(self.norm.get(t, t) for t in hand)
        out = [base]
        if self.flex:
            ft, fb = self.flex
            n = base.get(ft, 0)
            for b in (range(1, n + 1)):
                c1 = Counter(base)
                c1[ft] -= b
                c1[fb] += b
                out.append(c1)
        return out

    def actual_discard(self, hand, key):
        """正規化した牌 key に当たる、実際の牌。ぉ゛・ちゅは残す。"""
        pref = {"お": ["お", "ぉ゛"], "つ": ["つ", "っ", "ちゅ"]}.get(key, [key])
        for t in pref:
            if t in hand:
                return t
        return key

    def is_tenpai(self, hand13, sup):
        """13牌の手が、テンパイ(待ち牌が山にある)か。テンパイには、完成した語が3つ以上いるので、足りなければ探索しない。"""
        for ci in self.interpretations(hand13):
            if sum(1 for _, m, _ in self.blocks(ci, sup, self.Wn, self.Wt) if m == 0) >= 3 and self.tenpai_options(ci, sup):
                return True
        return False

    def choose(self, hand, wc):
        """14牌の手から、捨てる牌(実際の牌)と、捨てた後にテンパイかを返す。cpu='hint': 牌効率のヒントだけ(core.js と同じ)。
        cpu='exact': テンパイになる捨て牌があれば、待ち牌が最も多いものを選ぶ(強め)。"""
        sup = self.supply(wc)
        interps = self.interpretations(hand)
        if self.cpu == "hint":
            cand = [interps[0]] if len(interps) == 1 else [interps[0], interps[-1]]
            res = max((self.hint(ci, sup) for ci in cand), key=lambda x: x[0])
            disc = self.actual_discard(hand, res[1])
            rest = list(hand)
            rest.remove(disc)
            return disc, self.is_tenpai(rest, sup)
        best = None
        for ci in interps:
            for disc, waits in self.tenpai_options(ci, sup).items():
                u = sum(sup.get(w, 0) for w in waits)
                if best is None or u > best[0]:
                    best = (u, disc)
        if best:
            return self.actual_discard(hand, best[1]), True
        cand = [interps[0]] if len(interps) == 1 else [interps[0], interps[-1]]
        res = max((self.hint(ci, sup) for ci in cand), key=lambda x: x[0])
        return self.actual_discard(hand, res[1]), False

    def play(self, rng):
        wall = self.wall0[:]
        rng.shuffle(wall)
        wc = Counter(wall)
        hand = [wall.pop() for _ in range(HAND)]
        for t in hand:
            wc[t] -= 1
        first_tenpai = None
        tenpai = False
        for turn in range(1, self.L + 1):
            t = wall.pop()
            wc[t] -= 1
            hand.append(t)
            r = self.S.best(hand)
            if r:
                if first_tenpai is None or first_tenpai >= turn:
                    first_tenpai = turn - 1
                return dict(result="win", turn=turn, han=r["han"], han_no_merge=r["han_no_merge"], yaku=r["yaku"],
                            merges=r["merges"], raw=r["raw"], words=r["words"], head=r["head"], tenpai=first_tenpai)
            disc, tenpai = self.choose(hand, wc)
            hand.remove(disc)
            if tenpai and first_tenpai is None:
                first_tenpai = turn
        return dict(result="tenpai" if tenpai else "noten", turn=self.L, tenpai=first_tenpai)


_G = None


def _init(d, rule, L, cpu):
    global _G
    _G = Game(d, tile_copies(d, rule), L, cpu=cpu)


def _run(args):
    seed0, n = args
    out = []
    for k in range(n):
        out.append(_G.play(random.Random(seed0 + k)))
    return out


def run_games(d, rule, L, n, seed, procs, cpu):
    chunk = max(1, min(25, n // (procs * 4) or 1))
    jobs = [(seed + i, min(chunk, n - i)) for i in range(0, n, chunk)]
    with Pool(procs, initializer=_init, initargs=(d, rule, L, cpu)) as p:
        res = []
        for part in p.imap(_run, jobs):
            res += part
            if len(res) % 500 < chunk:
                print(f"    {rule}: {len(res)}/{n} ゲーム", flush=True)
    return res


# ---------------------------------------------------------------- 集計
def gini(xs):
    xs = sorted(xs)
    n, s = len(xs), sum(xs)
    return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(xs)) / (n * s) if s else 0.0


def ci95(k, n):
    p = k / n
    return 1.96 * math.sqrt(p * (1 - p) / n) * 100


def summarize(games, L):
    n = len(games)
    wins = [g for g in games if g["result"] == "win"]
    nw = len(wins)
    c3, c6 = round(0.3 * L), round(0.6 * L)
    cum = lambda t: sum(1 for g in games if g.get("tenpai") is not None and g["tenpai"] <= t)
    hans = [g["han"] for g in wins]
    return dict(games=n, wins=nw, win_rate=100 * nw / n, win_ci=ci95(nw, n),
                tenpai_ryukyoku=100 * sum(g["result"] == "tenpai" for g in games) / n,
                noten=100 * sum(g["result"] == "noten" for g in games) / n,
                cum_tenpai_t3=100 * cum(c3) / n, cum_tenpai_t6=100 * cum(c6) / n, t3=c3, t6=c6,
                mean_han=sum(hans) / nw if nw else 0, ge5=100 * sum(h >= 5 for h in hans) / nw if nw else 0,
                ge8=100 * sum(h >= 8 for h in hans) / nw if nw else 0,
                noyaku=100 * sum(h == 1 for h in hans) / nw if nw else 0,
                mean_points=sum(points(h) for h in hans) / nw if nw else 0,
                mean_turn=sum(g["turn"] for g in wins) / nw if nw else 0,
                merge_any=100 * sum(1 for g in wins if g["merges"]) / nw if nw else 0,
                merge_two=100 * sum(1 for g in wins if len(g["merges"]) == 2) / nw if nw else 0)


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_condition_csvs(out, tag, G, games, copies, d):
    S = G.S
    wins = [g for g in games if g["result"] == "win"]
    nw = len(wins)
    # 役(アガリ手での出現率。分母=アガリ手)
    raw, final = Counter(), Counter()
    for g in wins:
        for n in set(g["raw"]):
            raw[n] += 1
        for n in set(g["yaku"]):
            final[n] += 1
    seen = {}
    for ri, y in enumerate(S.Y):
        seen.setdefault(y["name"], (y["han_provisional"], y["group"], y["pattern"]))
    write_csv(os.path.join(out, f"yaku_{tag}.csv"), ["name", "han", "group", "pattern", "raw_wins", "raw_rate_pct", "final_wins", "final_rate_pct"],
              [[n, h, gr, pt, raw[n], f"{100*raw[n]/nw:.3f}", final[n], f"{100*final[n]/nw:.3f}"] for n, (h, gr, pt) in seen.items()])
    # 合体
    elig, app = Counter(), Counter()
    for g in wins:
        rs = set(g["raw"])
        for m, src in zip(S.M, S.msrc):
            if all(s in rs for s in src):
                elig[m["name"]] += 1
        for m in g["merges"]:
            app[m] += 1
    write_csv(os.path.join(out, f"merge_{tag}.csv"),
              ["name", "source_yaku", "han", "level", "eligible_wins", "eligible_rate_pct", "applied_wins", "applied_rate_pct"],
              [[m["name"], m["source_yaku"], m["han_provisional"], m["level"], elig[m["name"]], f"{100*elig[m['name']]/nw:.3f}",
                app[m["name"]], f"{100*app[m['name']]/nw:.3f}"] for m in S.M])
    # 語(アガリ手の4語に入った割合)
    wc = Counter(w for g in wins for w in g["words"])
    hc = Counter(g["head"] for g in wins)
    write_csv(os.path.join(out, f"words_{tag}.csv"), ["kind", "word", "type", "tiles", "wins", "rate_pct"],
              [["語", w["word"], w["type"], w["tiles"], wc[i], f"{100*wc[i]/nw:.3f}"] for i, w in enumerate(S.W)] +
              [["雀頭", h["head"], h["type"], h["tiles"], hc[i], f"{100*hc[i]/nw:.3f}"] for i, h in enumerate(S.H)])
    # 牌(枚数と、その牌を使う語・雀頭が、アガリ手に入った割合)
    uses = defaultdict(set)
    for i, w in enumerate(S.W):
        for t in w["tiles"].split("|"):
            uses[t].add(i)
    used, _ = tile_usage(d)
    rows = []
    for t in sorted(copies, key=lambda t: (-copies[t], t)):
        ws = uses.get(t, set())
        k = sum(1 for g in wins if ws & set(g["words"]))
        rows.append([t, copies[t], used.get(t, 0), len(ws), k, f"{100*k/nw:.2f}"])
    write_csv(os.path.join(out, f"tiles_{tag}.csv"),
              ["tile", "copies", "used_in_words", "words_using_tile(修飾3型を含む)", "wins_with_such_word", "rate_pct"], rows)
    # 語の偏り
    rates = [wc[i] / nw for i in range(len(S.W))]
    pos = [r for r in rates if r > 0]
    return dict(word_max=max(rates) * 100, word_min_pos=min(pos) * 100 if pos else 0, ratio=max(rates) / min(pos) if pos else float("inf"),
                zero_words=sum(1 for r in rates if r == 0), gini=gini(rates), n_words=len(rates))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "v13m"))
    ap.add_argument("--games", type=int, default=3000)
    ap.add_argument("--L", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default="results_v1.3m")
    ap.add_argument("--rules", default="new,old")
    ap.add_argument("--cpu", default="hint", choices=["hint", "exact"], help="hint=牌効率のヒント(強CPU・既定) / exact=テンパイ全数探索つき(より強い)")
    ap.add_argument("--check-tiles", action="store_true")
    a = ap.parse_args()
    if a.check_tiles:
        r = check_tiles(a.dir)
        print(r)
        return
    os.makedirs(a.out, exist_ok=True)
    summ = {}
    for rule in a.rules.split(","):
        t0 = time.time()
        copies = tile_copies(a.dir, rule)
        print(f"条件 {rule}: 山 {sum(copies.values())}枚 / 牌 {len(copies)-1}種+ぉ゛ L={a.L} {a.games}ゲーム", flush=True)
        games = run_games(a.dir, rule, a.L, a.games, a.seed, a.procs, a.cpu)
        G = Game(a.dir, copies, a.L, cpu=a.cpu)
        tag = f"{rule}_L{a.L}" + ("" if a.cpu == "hint" else "_exact")
        s = summarize(games, a.L)
        s.update(write_condition_csvs(a.out, tag, G, games, copies, a.dir))
        s["wall"] = sum(copies.values())
        summ[rule] = s
        print(f"  完了 {time.time()-t0:.0f}秒: アガリ率 {s['win_rate']:.1f}%(±{s['win_ci']:.1f}) 平均翻 {s['mean_han']:.2f}", flush=True)
    keys = ["wall", "games", "wins", "win_rate", "win_ci", "tenpai_ryukyoku", "noten", "t3", "cum_tenpai_t3", "t6", "cum_tenpai_t6",
            "mean_han", "ge5", "ge8", "noyaku", "mean_points", "mean_turn", "merge_any", "merge_two",
            "word_max", "word_min_pos", "ratio", "zero_words", "gini"]
    write_csv(os.path.join(a.out, f"summary_L{a.L}" + ("" if a.cpu == "hint" else "_exact") + ".csv"), ["metric"] + list(summ),
              [[k] + [f"{summ[r][k]:.4g}" if isinstance(summ[r][k], float) else summ[r][k] for r in summ] for k in keys])
    print("→", os.path.join(a.out, f"summary_L{a.L}" + ("" if a.cpu == "hint" else "_exact") + ".csv"))


if __name__ == "__main__":
    main()
