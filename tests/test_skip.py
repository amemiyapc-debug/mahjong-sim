"""見送り(アガリを見送って、1枚捨てて続ける)の流れの確認(sim14.Game.play の skip)。手作りの山で、2通り:
 1. 見送り→再アガリ(捨てた牌をもう一度引く) 2. 見送り→残りのツモで完成せず→ノーテン扱い(skipfail)
 python3 tests/test_skip.py"""
import os, sys, random
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import sim14
from sim14 import Game, tile_copies
D = os.path.join(ROOT, "dan6")
ng = 0
def ok(m, c, extra=""):
    global ng; print(("OK  " if c else "NG  ") + m); ng += (not c)
class Fixed(random.Random):
    def shuffle(self, x): pass                      # 山を並べ替えない
cp = tile_copies(D, "new", 0.05, 13)
G = Game(D, cp, 12, cpu="hint")
base13 = ['ち', 'ん', 'ぽ', 'ぬれ', 'ま', 'ん', 'ぱ', 'こ', '×2', 'い', 'く', 'あ', 'ん']      # ちんぽ・ぬれまん・ぱこぱこ+雀頭あん+いく(う待ち)
def wall(seq): return list(reversed(seq))            # pop() は末尾から取る
rec = []
orig = G.choose
def choose(hand, wc):
    d = orig(hand, wc); rec.append(d[0]); return d
G.choose = choose
# --- 見送りなし: 最初のツモ(う)でアガる ---
G.wall0 = wall(base13 + ['う'] + ['ほ'] * 12)
r = G.play(Fixed(1))
ok("見送りなし: 1回目のツモ(う)でアガリ(skipped=0)", r["result"] == "win" and r["turn"] == 1 and r["skipped"] == 0, str(r["turn"]))
# --- 見送る方針で、見送ったあとに捨てた牌を引き直す ---
G.wall0 = wall(base13 + ['う'] + ['ほ'] * 12)
rec.clear(); calls = []
def skip1(hand, turn, rr):
    calls.append(turn); return len(calls) == 1
r = G.play(Fixed(1), skip1)
disc = rec[0]
ok(f"見送り: アガリ形で skip が呼ばれ、1枚捨てる(捨てた牌: {disc})。見送ったあとの残りは 'ほ' だけなので完成せず、ノーテン扱い", r["result"] == "noten" and r.get("skipfail") is True and r["skipped"] == 1 and calls == [1], str(r))
ok("  ノーテン扱い: テンパイが残っていても tenpai なし(連続テンパイはリセット)、ツモは L=12 まで進む", r["turn"] == 12 and r.get("tenpai") is None)
# --- 見送り→再アガリ: 捨てた牌を次のツモで引く ---
G.wall0 = wall(base13 + ['う', disc] + ['ほ'] * 12)
calls.clear(); rec.clear()
r = G.play(Fixed(1), skip1)
ok("見送り→再アガリ: 捨てた牌を次に引くと、2回目のアガリ(turn=2)。skipped=1。2回目は skip が呼ばれても見送らない方針なので、採用される", r["result"] == "win" and r["turn"] == 2 and r["skipped"] == 1 and len(calls) == 2, str(r["turn"]) + " " + str(calls))
# --- 見送れない: 最後のツモ(L)では skip が呼ばれない ---
G2 = Game(D, cp, 1, cpu="hint")
G2.wall0 = wall(base13 + ['う'] + ['ほ'] * 12)
calls.clear()
r = G2.play(Fixed(1), skip1)
ok("残りのツモが0(L=1の1回目)では、見送りは選べない(skip が呼ばれず、そのままアガリ)", r["result"] == "win" and calls == [], str(r))
# --- 見送る方針でない既存の CPU は、見送りなしと同じ ---
ok("skip=None の既存CPUは従来どおり(skipped=0)", G.play(Fixed(2)).get("skipped") == 0)
print("すべてOK" if not ng else f"失敗 {ng}"); sys.exit(1 if ng else 0)
