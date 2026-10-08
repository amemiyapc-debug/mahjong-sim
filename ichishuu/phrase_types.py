"""句の「型」(20261008-2030): 型の定義と除外条件を、設定ファイルから読んで、成立する組を列挙する。コードに直書きしない。
  data/phrase_types.csv      型の定義(type_id, name, a_filter, b_filter, weight, description)
  data/phrase_type_rules.csv 除外条件(rule_id, type_id(ALL=全型), kind, side, filter, partner_filter, note)
  data/phrase_pairs_draft.csv 看板30組(従来どおり)
フィルタの書式: `キー=値1|値2;キー=値` (キーは slot / sub / word。キー間は AND、値は OR)。
除外条件の種類: exclude = その側の語のうち、フィルタに合うものは、使わない(side は A / B / any)。
               allow_only = その側の語がフィルタに合うとき、相手の語は partner_filter に合うものだけと組む。
組は、順序のない2語の集合として数える(⑦⑧⑩のように、AとBの分類が重なる型は、どちらの向きでも当てはまれば1組)。"""
import csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
rd = lambda n: list(csv.DictReader(open(os.path.join(DATA, n), encoding="utf-8-sig")))


def parse_filter(s):
    f = {}
    for part in (s or "").split(";"):
        if part.strip():
            k, v = part.split("=", 1); f[k.strip()] = set(v.split("|"))
    return f


def match(w, f):
    """w: 語の行(word・slot・sub)。f: parse_filter の結果。空のフィルタは、すべてに合う。"""
    return all(w[k] in vs for k, vs in f.items())


class PhraseBook:
    def __init__(self, words=None, types=None, rules=None, pairs=None):
        self.words = words if words is not None else rd("words_ichishuu100.csv")
        self.types = types if types is not None else rd("phrase_types.csv")
        self.rules = rules if rules is not None else rd("phrase_type_rules.csv")
        pr = pairs if pairs is not None else rd("phrase_pairs_draft.csv")
        self.signboard = {frozenset((p["word_a"], p["word_b"])) for p in pr}
        names = {w["word"] for w in self.words}
        assert all(x in names for p in self.signboard for x in p), "看板の語が、語リストにない"
        self.by_name = {w["word"]: w for w in self.words}
        self.type_name = {t["type_id"]: t["name"] for t in self.types}
        self.type_pairs = {t["type_id"]: self._enumerate(t) for t in self.types}

    def _rules_for(self, tid):
        return [r for r in self.rules if r["type_id"] in (tid, "ALL")]

    def _ok(self, rules, a, b):
        """向き(A側=a, B側=b)で、除外条件に反しないか"""
        for r in rules:
            f = parse_filter(r["filter"]); side = r["side"]
            if r["kind"] == "exclude":
                if (side in ("A", "any") and match(a, f)) or (side in ("B", "any") and match(b, f)): return False
            elif r["kind"] == "allow_only":
                pf = parse_filter(r["partner_filter"])
                if side == "A" and match(a, f) and not match(b, pf): return False
                if side == "B" and match(b, f) and not match(a, pf): return False
                if side == "any":
                    if match(a, f) and not match(b, pf): return False
                    if match(b, f) and not match(a, pf): return False
            else:
                raise ValueError("未知の kind: " + r["kind"])
        return True

    def _enumerate(self, t):
        fa, fb = parse_filter(t["a_filter"]), parse_filter(t["b_filter"]); rules = self._rules_for(t["type_id"]); out = set()
        for a in self.words:
            if not match(a, fa): continue
            for b in self.words:
                if a is b or not match(b, fb): continue
                if self._ok(rules, a, b): out.add(frozenset((a["word"], b["word"])))
        return out

    def phrases(self, signboard=True, type_ids=()):
        """成立する組(順序なしの2語)の集合。看板と型の両方に当てはまる組は、1つ。"""
        s = set(self.signboard) if signboard else set()
        for tid in type_ids: s |= self.type_pairs[tid]
        return s

    def labels(self, pair, type_ids):
        """その組の分類: 看板に当てはまれば「看板」、型に当てはまれば型のID(重なれば、すべて)"""
        out = (["看板"] if pair in self.signboard else []) + [tid for tid in type_ids if pair in self.type_pairs[tid]]
        return out
