"""one_from_each でグループが重なる役(童貞目線: stem:X x3 + part:P)が、
「各グループに別々の語を割り当てる」判定になっていることを確かめる。"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import simulator as sim
d = sim.data()
ix = {w['word']: i for i, w in enumerate(d.words)}
rows = [i for i, y in enumerate(d.yaku) if y['name'] == '童貞目線']
ten = next(i for i in rows if d.yaku[i]['params'].startswith('stem:ちん;'))
assert d.yaku[ten]['params'] == 'stem:ちん;stem:ちん;stem:ちん;part:男性器', d.yaku[ten]['params']
fn = d.fns[ten]
mask = lambda ws: sum(1 << ix[w] for w in ws)
# ちん語幹は 見せちん/デカちん/エロちん/ちん穴/ちん媚/ちん♡/ちん舐/ちんコキ (部位=男性器)
assert fn(mask(['見せちん', 'デカちん', 'エロちん', 'ちんぽ']))          # ちん語幹3 + 男性器の別の語(ちんぽ) → 成立
assert fn(mask(['見せちん', 'デカちん', 'エロちん', 'ちん穴']))          # ちん語幹4語(4つ目はstem:ちんかつ男性器)→ 成立
assert not fn(mask(['見せちん', 'デカちん', 'ちんぽ', 'ちんこ']))        # ちん語幹は2語 → 3つのstem:ちんグループに届かない
assert not fn(mask(['見せちん', 'デカちん', 'エロちん', 'まんこ']))      # 4語目が男性器でない → 不成立
assert not fn(mask(['見せちん', 'ちんぽ', 'ちんこ', 'ちんコキ']))        # 同じ語を2つのグループに使い回せない(別々の語が必要)
# 全6語幹の童貞目線(stem:X x3 + part:P)を、独立実装(順列総当たり)と数え上げで照合
import itertools
bad = 0
for i in rows:
    y = d.yaku[i]
    groups = [g.split('|') for g in y['params'].split(';')]
    def match(tok, w):
        return (w['modifier'] == tok[4:] if tok.startswith('mod:') else w['stem'] == tok[5:] if tok.startswith('stem:')
                else w['part'] == tok[5:] if tok.startswith('part:') else w['word'] == tok)
    for combo in itertools.combinations(range(d.nw), 4):
        ws = [d.words[j] for j in combo]
        slow = any(all(any(match(t, w) for t in groups[k]) for k, w in enumerate(perm)) for perm in itertools.permutations(ws))
        if bool(d.fns[i](mask([w['word'] for w in ws]))) != slow:
            bad += 1
print("童貞目線", len(rows), "行を全595,665組で照合: 不一致", bad)
assert bad == 0
print("OK")
