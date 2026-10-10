"""dan6 語呂度エンジン(goro/goro.py・goro2.py・goro3.py の移植。点 = 500 × 句ボーナス(1+Σつながり+Σ名前つき役の淫) × 連鎖 × テーマ)。語のタグは data/word_tags_v1.csv。
アガリ手(4語+雀頭)を score() に渡すと、つながり・連鎖・テーマ・点を返す。
パラメータ P(語呂度の変種): thresh(しきい値、既定3)、thresh_add({(スロット,スロット): 加算}。そのスロット対だけしきい値を上げる)。"""
import csv, os, itertools, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = {(0, 1): 1, (0, 2): 3, (0, 3): 1, (1, 2): 2, (1, 3): 2, (1, 5): 1, (1, 6): 1, (2, 3): 3, (2, 4): 2, (2, 5): 2, (2, 6): 1,
        (3, 4): 2, (3, 5): 3, (3, 6): 1, (4, 5): 2, (4, 6): 1, (5, 6): 3}
SAME_SUB = {('高まり', '絶頂・結末'): 2, ('感情・状況', '命令・誘い'): 1, ('行為', 'キス・吸い'): 1}
MODS = ['見せ', 'デカ', 'エロ', 'ぬれ', '媚び', '舐め', 'コキ', '穴', '♡', '×2']
ALIAS = {'まめ': 'くり', 'おまめ': 'くり', 'すじ': 'くり'}
COMP = [('くりでイく', 'くり', '絶頂'), ('まんでイく', '部位:女性器', '絶頂'), ('ちんでイく', '部位:男性器', '絶頂'),
        ('胸でイく', '部位:胸', '絶頂'), ('お尻でイく', '部位:後ろ', '絶頂'), ('口でイく', '部位:口', '絶頂'),
        ('ラブキス', 'キス', 'ラブ'), ('調教', 'SM', '態度'), ('命令調教', 'SM', '命令'), ('濡れ濡れ', 'ぬれ', '水音'), ('見せつけ', '見せ', '絶頂')]
CL = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8}
FLOOR = 500
SLOT_NAMES = ['前置き', '感情・誘い', '部位', '行為', '音', '反応', '喘ぎ声']
STAGE_NAMES = {1: '語', 2: '句', 3: '節', 4: '文', 5: '碑文'}
LV_NAMES = ['無知', '恥ずかしい', 'すけべ']      # 研究♡の呼び名(内部の数値は 0/1/2)
KEN = {0: 4, 1: 3, 2: 2}                       # 研究♡ -> 語を結ぶしきい値(data/score_config.csv の KEN_MODE=table のとき使う。20261010-1210 で table に決定。研究♡0は点に影響しない)
SKIPS = {0: 1, 1: 2, 2: 3}                     # 研究♡ -> 見送り回数(仮。1ステージの全ゲームで共有)
DEFAULT_THRESH = 3                             # KEN_CONST が空のときの値(KEN_MODE=const で使う)


def _read_csv(name):
    with open(os.path.join(ROOT, 'data', name), encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def load_unlock(path_name='score_unlock.csv'):
    """点の解禁表(data/score_unlock.csv)-> {項目キー: {研究♡: 0/1}}。キー: base/en/yaku/phrase/chain/theme"""
    return {r['key']: {lv: int(r['lv%d' % lv]) for lv in (0, 1, 2)} for r in _read_csv(path_name)}


def load_lap(path_name='lap_config.csv'):
    """周回数 -> 研究♡(data/lap_config.csv。lap 列の最大値の行は「その周回以降」)"""
    return sorted((int(r['lap']), int(r['ken'])) for r in _read_csv(path_name))


def load_score_config(path_name='score_config.csv'):
    c = {r['key']: r['value'].strip() for r in _read_csv(path_name)}
    return dict(KEN_MODE=c.get('KEN_MODE', 'table') or 'table', KEN_CONST=int(c.get('KEN_CONST') or DEFAULT_THRESH))


def load_stage_wins(path_name='stage_wins_lap1.csv'):
    """1周目(研究♡0)のステージ条件: ステージ番号 -> 3ゲームのうち必要な和了の回数(data/stage_wins_lap1.csv)"""
    return sorted((int(r['stage']), int(r['wins_needed'])) for r in _read_csv(path_name))


UNLOCK = load_unlock()
STAGE_WINS = load_stage_wins()
LAP_KEN = load_lap()
CONFIG = load_score_config()


def ken_lap(lap):
    """周回数 -> 研究♡(1周目=0 無知、2周目=1 恥ずかしい、3周目以降=2 すけべ。data/lap_config.csv)。ステージ番号では変わらない"""
    lv = LAP_KEN[0][1]
    for l, k in LAP_KEN:
        if lap >= l:
            lv = k
    return lv


def wins_needed(stage):
    """1周目のステージ条件(和了の回数)。表にないステージは、最後の行の値"""
    n = STAGE_WINS[0][1]
    for st, w in STAGE_WINS:
        if stage >= st:
            n = w
    return n


def thresh_of(lv, mode=None):
    """研究♡ -> 語を結ぶしきい値。KEN_MODE=table(既定。20261010-1210): KEN[lv](研究♡1=3、研究♡2=2)。KEN_MODE=const: 一定(KEN_CONST)"""
    mode = mode or CONFIG['KEN_MODE']
    return KEN[lv] if mode == 'table' else CONFIG['KEN_CONST']


def params(lv, mode=None, **kw):
    """score()/best_hand() に渡す P。lv を入れると、解禁表のとおりの項目だけが点になる"""
    return dict(thresh=thresh_of(lv, mode), lv=lv, **kw)


def _stem(r):
    n = r['word'].replace('【雀頭】', '').split('・')[0]
    for m in MODS:
        n = n.replace(m, '')
    n = n.replace('っ', 'つ')
    n = ALIAS.get(n, n)
    return n[:2] if len(n) >= 2 else n


def _theme(r):
    if r['part'] and '|' not in r['part']:
        return r['part']
    if r['slot_no_eff'] in (5, 6):
        return '感じる'
    if r['tone'] in ('SM', 'ラブ'):
        return r['tone']
    return ''


def _tags(r):
    t = set()
    n = r['word'].replace('【雀頭】', '')
    if r['part'] and '|' not in r['part']:
        t.add('部位:' + r['part'])
    if r['sub'] in ('絶頂・結末', '雀頭・快感'):
        t.add('絶頂')
    if r['stem'] == 'くり':
        t.add('くり')
    if r['sub'] == 'キス・吸い':
        t.add('キス')
    if r['tone'] == 'ラブ':
        t.add('ラブ')
    if r['tone'] == 'SM':
        t.add('SM')
    if r['sub'] == '命令・誘い':
        t.add('命令')
    if r['sub'] == '態度':
        t.add('態度')
    if r['slot'] == '音':
        t.add('水音')
    if 'ぬれ' in n:
        t.add('ぬれ')
    if '見せ' in n:
        t.add('見せ')
    return t


def load(path=None):
    path = path or os.path.join(ROOT, 'data', 'word_tags_v1.csv')
    rows = {}
    for x in csv.DictReader(open(path, encoding='utf-8-sig')):
        r = dict(word=x['word'], kind=x['種別'], slot_no=int(x['slot_no']), slot=x['slot'], sub=x['sub'], reading=x['読み'],
                 part=x['部位'], tone=x['トーン'], target=x['命令の係り先'])
        # 略称の雀頭は一行の最後(スロット6)に置く(goro.py と同じ)
        r['slot_no_eff'] = 6 if (r['kind'] == '雀頭' and '略称' in r['sub']) else r['slot_no']
        r['stem'] = _stem(r)
        r['theme'] = _theme(r)
        r['tags'] = _tags(r)
        rows[r['word']] = r
    return rows


ROWS = load()


def node(name, head=False):
    return ROWS[('【雀頭】' + name) if head else name]


def _parts(p):
    return set(p.split('|')) if p else set()


def pscore(a, b):
    A, B = _parts(a), _parts(b)
    if not A or not B:
        return 0
    if A & B:
        return 2
    bodies = {'女性器', '後ろ', '口'}
    if ('穴' in A and B & bodies) or ('穴' in B and A & bodies):
        return 1
    return None


def link(a, b, P=None):
    """つながりの強さ(0=つながらない、しきい値以上の整数)"""
    P = P or {}
    thresh = P.get('thresh', 3)
    sa, sb = a['slot_no_eff'], b['slot_no_eff']
    if sa > sb:
        a, b = b, a
        sa, sb = sb, sa
    if sa == sb:
        sub = lambda r: r['sub'].replace('雀頭・', '')
        base = SAME_SUB.get((sub(a), sub(b))) or SAME_SUB.get((sub(b), sub(a))) or 1       # 語の順に依存しないよう、両方向を引く(参照実装 goro.py は片方向のみ)
    else:
        base = BASE.get((sa, sb), 0)
    for x, y in ((a, b), (b, a)):
        if x['target'] and x['slot_no_eff'] < y['slot_no_eff'] and x['target'] == y['slot']:
            base = max(base, 3)
    if base == 0:
        return 0
    p = pscore(a['part'], b['part'])
    if p is None:
        return 0
    ta, tb = a['tone'], b['tone']
    t = 0
    if ta and tb:
        if ta == tb:
            t = 1
        elif {ta, tb} == {'ラブ', 'SM'}:
            return 0
    ra, rb = a['reading'], b['reading']
    ph = 1 if (ra[-1:] == rb[:1] or rb[-1:] == ra[:1] or ra[:1] == rb[:1] or ra[-1:] == rb[-1:]) else 0
    sc = base + p + t + ph
    if sa == sb and p == 0 and base < 2:
        return 0
    return sc if sc >= thresh + P.get('thresh_add', {}).get((sa, sb), 0) else 0


def link2(a, b, P=None):
    """goro2.link: 同語幹・同テーマの加点(同スロット: 同語幹4・同テーマ3、別スロット: 同語幹+2)"""
    s = link(a, b, P)
    same = a['slot_no_eff'] == b['slot_no_eff']
    if a['tone'] and b['tone'] and {a['tone'], b['tone']} == {'ラブ', 'SM'}:
        return 0
    if same:
        if a['stem'] == b['stem'] and a['stem']:
            s = max(s, 4)
        elif a['theme'] and a['theme'] == b['theme']:
            s = max(s, 3)
    else:
        if a['stem'] == b['stem'] and a['stem']:
            s = s + 2 if s else 3
    return s


def collapse(nodes, L):
    names = [n['word'] for n in nodes]
    slot = {n['word']: n['slot_no_eff'] for n in nodes}
    par = {n: n for n in names}

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    inner = [(a, b, s) for a, b, s in L if slot[a] == slot[b]]
    for a, b, s in inner:
        par[f(a)] = f(b)
    seen = {}
    for a, b, s in L:
        if slot[a] == slot[b]:
            continue
        k = tuple(sorted((f(a), f(b))))
        seen[k] = max(seen.get(k, 0), s)
    return list(inner) + [(k[0], k[1], s) for k, s in seen.items()]


def _chain_count(nodes, C):
    names = [n['word'] for n in nodes]
    par = {n: n for n in names}

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for a, b, s in C:
        par[f(a)] = f(b)
    comp = collections.defaultdict(lambda: [0, 0])
    for n in names:
        comp[f(n)][0] += 1
    for a, b, s in C:
        comp[f(a)][1] += 1
    return sum(max(0, e - 1) for n, e in comp.values()), comp


def mult(m):
    x = 1.0
    for k in range(1, m + 1):
        x *= 1 + 0.5 * k
    return x


def best_theme(nodes):
    best = (1, 'なし', 0)
    c1 = collections.Counter(n['stem'] for n in nodes if n['stem'])
    c2 = collections.Counter(n['theme'] for n in nodes if n['theme'])
    for nm, cnt in list(c1.items()) + list(c2.items()):
        if CL.get(cnt, 1) > best[0]:
            best = (CL.get(cnt, 1), '単:' + nm, cnt)
    for nm, A, B in COMP:
        a = [n for n in nodes if A in n['tags']]
        b = [n for n in nodes if B in n['tags']]
        if a and b:
            k = len({n['word'] for n in a} | {n['word'] for n in b})
            if CL.get(k, 1) > best[0]:
                best = (CL.get(k, 1), '複合:' + nm, k)
    return best


def theme_counts(nodes):
    """単独テーマ(同語幹・同テーマ)の最大語数、複合テーマが成立しているか"""
    c1 = collections.Counter(n['stem'] for n in nodes if n['stem'])
    c2 = collections.Counter(n['theme'] for n in nodes if n['theme'])
    k = max([0] + list(c1.values()) + list(c2.values()))
    comp = []
    for nm, A, B in COMP:
        a = [n for n in nodes if A in n['tags']]
        b = [n for n in nodes if B in n['tags']]
        if a and b:
            comp.append((nm, len({n['word'] for n in a} | {n['word'] for n in b})))
    return k, comp


def _kazari():
    p = os.path.join(ROOT, 'dan6', 'yaku_class.csv')
    return {r['name'] for r in csv.DictReader(open(p, encoding='utf-8-sig')) if r['class'].startswith('飾り')}


KAZARI = _kazari()                              # 飾り(12個)は 0淫。演出と図鑑にだけ使う


def yaku_in(S, r):
    """名前つき役の淫の合計。r = Scorer.score() の結果。同じ group は tier 最大の1つだけ(Scorer が処理済み)、
    合体は成立した合体1つの淫(元の役の淫の合計+1/+2)で、元の役は二重に数えない。飾りは0淫。
    形の1翻(旧)は、淫には含めない。"""
    mh = {m['name']: int(m['han_provisional']) for m in S.M}
    return sum(h for n, h in r['added'].items() if n in r['yaku'] and n not in KAZARI) + sum(mh[n] for n in r['merges'])


def score(words, head, P=None, yin=0, phrase_mult=1.0):
    """words: 語名の4つ、head: 雀頭名(【雀頭】なし)、yin: 名前つき役の淫の合計。返り値: dict"""
    nodes = [node(w) for w in words] + [node(head, True)]
    L = []
    for a, b in itertools.combinations(nodes, 2):
        s = link2(a, b, P)
        if s:
            L.append((a['word'], b['word'], s))
    C = collapse(nodes, L)
    m, comp = _chain_count(nodes, C)
    ch = mult(m)
    en = sum(min(3, s - 2) for a, b, s in C)                   # 縁(旧名: つながり)
    bonus_full = 1 + en + yin                                  # 句ボーナス = 1 + Σ縁 + Σ名前つき役の淫
    tm, tn, k = best_theme(nodes)
    size = max([c[0] for c in comp.values()] + [1])            # つながった語の数の最大(語1・句2・節3・文4・碑文5)
    kk, compo = theme_counts(nodes)
    # 句(語A+語B。看板・型)の得点(PHRASE_POINTS。data/phrase_config.csv)は、ここ(points を出したあと)に、表示した句の数×PHRASE_POINTS を足す案。未決のため、まだ入れない(20261008-2110)
    # 解禁表(data/score_unlock.csv): P['lv'] があれば、その研究♡で解禁された項目だけを点に入れる。成立の判定(縁・連鎖・テーマ・句)は常に行う
    lv = (P or {}).get('lv')
    u = (lambda k: 1) if lv is None else (lambda k: UNLOCK[k][lv])
    bonus = 1 + en * u('en') + yin * u('yaku')
    ch_a = ch if u('chain') else 1
    tm_a = tm if u('theme') else 1
    pm_a = phrase_mult if u('phrase') else 1
    pts = FLOOR * bonus * ch_a * tm_a * pm_a if u('base') else 0
    return dict(links=len(C), raw_links=len(L), merges=m, chain=ch, bonus=bonus, bonus_full=bonus_full, en=en, yin=yin, lv=lv,
                points_full=FLOOR * bonus_full * ch * tm * phrase_mult, theme=tm, theme_name=tn, theme_k=kk,
                composite=compo, size=size, stage_name=STAGE_NAMES[size],
                points=pts, pairs=C)


JA_UNITS = [(10 ** 16, '京'), (10 ** 12, '兆'), (10 ** 8, '億'), (10 ** 4, '万')]


def fmt_points(p):
    """大きな点を 万・億・兆・京 で表す(320px 向けに最大でも約10文字)"""
    p = int(p)
    for u, nm in JA_UNITS:
        if p >= u:
            v = p / u
            s = ('%.1f' % (int(v * 10) / 10)) if v < 100 else ('%d' % int(v))
            if s.endswith('.0'):
                s = s[:-2]
            return s + nm
    return str(p)


def best_hand(S, hand, P=None):
    """14牌の手の、点が最大の分割。アガリでなければ None。S = yaku14.Scorer。
    返り値: score() の dict + words/head(名前)・yaku(名前つき役の名前)・kazari(飾り)・yaku_merges(成立した名前つき合体)・yin・points_noyaku(名前つき役を外した同じ分割の点)"""
    best = None
    for ws, h, oho, chu in S.judge.partitions(hand):
        r = S.score(ws, h, oho)
        names = [S.W[i]['word'] for i in ws]
        head = S.H[h]['head']
        yin = yaku_in(S, r)
        sc = score(names, head, P, yin)
        k = (sc['points'], yin)
        if best is None or k > best[0]:
            sc0 = score(names, head, P, 0)
            best = (k, dict(sc, words=names, head=head, yaku=[n for n in r['yaku'] if n not in KAZARI], kazari=[n for n in r['yaku'] if n in KAZARI],
                            yaku_merges=r['merges'], points_noyaku=sc0['points']))
    return best[1] if best else None
