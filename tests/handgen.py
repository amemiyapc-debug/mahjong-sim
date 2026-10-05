"""テスト用の手の生成(役のパラメーターの語を多めに入れた、偏りのある14牌の勝ち手)。tests/test_yaku14.py と同じ作り方。"""
import random


def tokens_of(y):
    toks = []
    for g in y["params"].replace("/", ";").split(";"):
        for t in g.split("|"):
            t = t.split("=")[-1] if "=" in t else t
            if t:
                toks.append(t)
    return toks


def make_gen(S, rng, variants=True):
    W, H, Y = S.W, S.H, S.Y
    theme = []
    for y in Y:
        ws = set()
        for t in tokens_of(y):
            try:
                ws |= set(S._bits(S.token_mask(t)))
            except Exception:
                pass
        if ws:
            theme.append(sorted(ws))

    def hand_of(ws, h):
        t = []
        for w in ws:
            t += W[w]["tiles"].split("|")
        t += H[h]["tiles"].split("|")
        if variants:
            t = [("ぉ゛" if x == "お" and rng.random() < 0.3 else x) for x in t]
            t = [("っ" if x == "つ" and rng.random() < 0.3 else x) for x in t]
            t = [("ちゅ" if x in ("つ", "っ") and rng.random() < 0.2 else x) for x in t]
        rng.shuffle(t)
        return t

    def gen():
        k = rng.choice((0, 0, 2, 3, 4))
        ws = set()
        if k:
            pool = rng.choice(theme)
            ws |= set(rng.sample(pool, min(k, len(pool))))
        while len(ws) < 4:
            ws.add(rng.randrange(len(W)))
        return hand_of(list(ws)[:4], rng.randrange(len(H))), list(ws)[:4]
    return gen, theme
