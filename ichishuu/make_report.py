"""ichishuu/results_20261008.json → docs/ichishuu_sim_20261008.md(数字は結果のまま。解釈は最後の節に分ける)"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "ichishuu", "results_20261008.json"), encoding="utf-8")); v = d["verify"]; R = d["runs"]; P = d["pairs"]; m = R["L12_main"]
def row(k):
    r = R[k]; return f"| {k} | {r['L']} | {r['heads_n']} | {r['wins']}/{r['games']} | {r['win_rate']:.1f}% | {r['mean_turn_win']:.2f} | {r['tenpai']} | {r['noten']} |"
md = ["# 一周版100語の測定(2026-10-08・測定のみ)\n", "ルール・語・点数は変えていない。数字は、実行結果そのまま。解釈・提案は、最後の節に分けて書いた。\n", "## 1. 実行\n"]
md += ["- コマンド: `python3 ichishuu/sim_ichishuu.py`(既定値: 1,000ゲーム・シード 20261008・4プロセス)。結果の生データ: `ichishuu/results_20261008.json`。この文書は `python3 ichishuu/make_report.py` で作る。",
       "- シード: ゲームiのシードは `20261008 + i`(i=0〜999)。すべての設定(L=10/12/14・雀頭の感度)で同じシードを使う。",
       "- 入力: `data/words_ichishuu100.csv`(100語)・`data/tile_usage_100.csv`・`data/phrase_pairs_draft.csv`(句30組)。",
       "- 使った既存の実装: `sim14.py` の `Game`(CPU=`hint`。牌効率のヒントで捨て牌を選ぶ、これまで「強CPU」と呼んできたもの。テンパイ判定は全数探索)、`judge14.py`(14牌の分割)、`dan6/tile_variants.csv`(つ=っ・お=ぉ゛)。役・点は数えない(`PartScorer` は、14枚が分けられるかだけを見る)。", "",
       "## 2. 使ったルールの仮定(勝手に新しいルールは作っていない。決まっていない点は、既存の実装に合わせた)\n"]
md += ["- " + s for s in [
    "手牌13枚。ツモで14枚にして、別々の4語(12牌)+雀頭(2牌の語)に過不足なく分けられればアガリ。分けられなければ1枚捨てる。これを最大L回(CLAUDE.md §3)。同じ語を1つの手牌に2回使えない。",
    "**雀頭の辞書**(依頼に指定がない): `dan6/heads.csv` の28種のうち、2牌とも、100語の山にある牌で作れるもの27種を使った(除外: まぞ。「ぞ」が山にない)。感度として、喘ぎ声の雀頭12種だけの場合も出した(§4)。",
    "**山**: 依頼の式 `min(10, max(2, ceil(その牌を使う語の数 ÷ 2)))` だけ。修飾牌への+10%(CLAUDE.md §3)は足さない。ぉ゛は入れない。雀頭だけに使う牌は山に入れない(山は100語に使う牌だけ)。",
    "牌の互換: つ=っ・お=ぉ゛(`dan6/tile_variants.csv`)。ちゅ→つ の代用はなし(dan6 の決定)。山では「っ」「つ」を別の牌として数える(「っ」10枚・「つ」3枚)。",
    "CPU: 既存の `hint`(上記)。「見送り」「牌入れ替え」は使わない。",
    "アガリ率 = ツモ回数L以内に14枚が完成した割合。平均ツモ回数 = 完成したゲームで、完成した時点のツモの回数(1〜L)の平均。",
    "句の「成立」= アガリの14枚の分け方のうち、**どれか1つ以上**に、語Aと語Bが両方含まれる。分け方が1通りに決まる手に限った割合も出した(`results_20261008.json` の `pair_rate_unique`)。"]]
md += ["", "## 3. 山の枚数の検証(b)\n",
       f"- 語 {v['words_n']}・重複なし {v['words_unique']}・すべて3牌: {v['tiles3']}。牌の種類 {v['tile_types']}種。",
       f"- 式で計算した枚数と、`tile_usage_100.csv` の `copies_old_rule` の不一致: {len(v['copies_diff'])}件。語の使用数の不一致: {len(v['used_diff'])}件。",
       f"- **山の合計 {v['wall']}枚**(ファイル側の合計 {v['file_wall']}枚)。**×2牌 {v['x2_copies']}枚**(×2を使う語は18語)。見込みと一致した。",
       f"- 専用牌(1語だけで使う牌): {v['single_use_tiles'] or 'なし'}。2語だけで使う牌: {'・'.join(v['two_use_tiles'])}。",
       f"- 100語と `dan6/words.csv`(365語)の照合: 語の表記が見つからない語 {len(v['words_not_in_words_csv'])}件。牌・slotが違う語 0件。`sub` 列だけ違う語が1件: ちんちん(`words.csv` は「部位(×2)」、`words_ichishuu100.csv` は「男性器」)。",
       f"- 句30組: 行数 {v['pairs_n']}。語が100語にない行 {len(v['pairs_missing'])}件。重複 {v['pairs_dup']}件。", "",
       "## 4. 結果(c・d・e)\n", "| 設定 | L | 雀頭の数 | アガリ | アガリ率 | 平均ツモ回数(アガリのみ) | テンパイ流局 | ノーテン |", "|---|---|---|---|---|---|---|---|"]
md += [row(k) for k in ("L12_main", "L10", "L14", "L12_head_aegigoe_only")]
md += ["", "L12_main が主(依頼のc・d)。L10・L14 が感度(e)。最後の行は、雀頭の辞書の感度(参考)。", "", "### 句30組の成立(d)\n", "| | L=10 | L=12(主) | L=14 |", "|---|---|---|---|"]
a, b = R["L10"], R["L14"]
md += ["| アガリ手のうち、1組以上成立した手 | %.1f%% | %.1f%% | %.1f%% |" % (a["win_with_ge1_pair"], m["win_with_ge1_pair"], b["win_with_ge1_pair"]),
       "| アガリ手あたりの成立組数の平均 | %.3f | %.3f | %.3f |" % (a["mean_pairs_per_win"], m["mean_pairs_per_win"], b["mean_pairs_per_win"]),
       "| 全体(30組のうち成立した組の割合の平均) | %.2f%% | %.2f%% | %.2f%% |" % (a["overall_pair_share"], m["overall_pair_share"], b["overall_pair_share"]),
       "| 1度も成立しなかった組の数 | %d | %d | %d |" % (len(a["pairs_zero"]), len(m["pairs_zero"]), len(b["pairs_zero"])),
       "| アガリ手の分け方の数の平均 | %.2f | %.2f | %.2f |" % (a["mean_partitions"], m["mean_partitions"], b["mean_partitions"]),
       "", "### 組ごとの成立率(アガリ手に対する%%。分母 L=10: %d・L=12: %d・L=14: %d)\n" % (a["wins"], m["wins"], b["wins"]), "| no | 語A | 語B | L=10 | L=12(主) | L=14 |", "|---|---|---|---|---|---|"]
for i, (x, y) in enumerate(P):
    md.append("| %d | %s | %s | %.1f%% | %.1f%% | %.1f%% |" % (i + 1, x, y, a["pair_rate"][str(i)], m["pair_rate"][str(i)], b["pair_rate"][str(i)]))
md += ["", "### アガリまでのツモ回数の分布(L=12・アガリ%d件)\n" % m["wins"], "| ツモ回数 | " + " | ".join(m["turn_dist_win"]) + " |", "|" + "---|" * (len(m["turn_dist_win"]) + 1), "| 件数 | " + " | ".join(str(x) for x in m["turn_dist_win"].values()) + " |", "",
       "## 5. 再現性(f)\n",
       f"- 同じシードで、L=12 をもう一度実行した。結果(各ゲームの結果・ツモ回数・14枚の手牌)のハッシュ: 1回目 `{m['digest']}`、2回目 `{d['rerun']['digest']}`。**一致: {d['rerun']['same']}**。アガリ率 {d['rerun']['win_rate']:.1f}%・平均ツモ回数 {d['rerun']['mean_turn_win']:.2f}(1回目と同じ)。", "",
       "## 6. 確認できなかったこと・判断に迷ったこと\n"]
e = R["L12_head_aegigoe_only"]
md += ["- " + s for s in [
    "雀頭の辞書は、依頼に指定がなく、上記の仮定で置いた(27種)。喘ぎ声だけ(12種)にすると、アガリ率は %.1f%%・平均ツモ %.2f になった。" % (e["win_rate"], e["mean_turn_win"]),
    "「句の成立」の定義(分け方のどれか1つ以上)は、私が置いた。分け方が1通りの手(L=12で %d 件)に限った組ごとの割合は、JSON にある。" % m["unique_partition_hands"],
    "1,000ゲームでは、成立率が1%%未満の組(L=12で30組中 %d 組が0件)の差は、誤差の範囲で、順位づけには使えない。" % len(m["pairs_zero"]),
    "役・点・句の倍率は数えていない(依頼のとおり)。CPU は `hint` の1種類だけ。弱CPUや、句を狙うCPUは試していない。"]]
md += ["", "## 7. 解釈(数字とは分けた私の見立て。判断は企画側)\n",
       "- アガリ率は、L=12で約%d%%と高い。dan6 の365語・361枚の測定(約79%%。CPU・ツモ回数は同じ。役・点の判定は別)より、約10ポイント低い。語を100に絞っても、アガリやすさが大きくは落ちていない。" % round(m["win_rate"]),
       "- 句30組は、無作為に4語を引いた場合の期待(1組あたり約0.12%%)とほぼ同じ頻度でしか成立していない(L=12で全体 %.2f%%)。このCPUは牌効率だけで手を作り、句を狙わないため、句を成立させるには、プレイヤーが句を狙って語を選ぶ必要がある。CPUの数字は、プレイヤーが句を狙わない場合の下限に近い。" % m["overall_pair_share"],
       "- 句の成立を、ゲームの「売りの肝」(CLAUDE.md §1-2)として機能させたい場合は、句の組数(30組)・手牌に残せる枚数・句を狙う操作のどれかに手を入れる必要がありそうだが、この測定だけでは、どれが効くかは分からない。"]
open(os.path.join(ROOT, "docs", "ichishuu_sim_20261008.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("OK")
