#!/bin/sh
# ゲーム(game/)の作り直し〜確認。入力CSVは ../v13m(HM_DATA_DIR で変えられる)。出力HTMLは /mnt/user-data/outputs(HM_OUT_DIR で変えられる)。
set -e
cd "$(dirname "$0")"
python3 make_data.py && python3 build.py
for t in test_batch test_cmd test_oho2 test_uo test_tri test_giongo; do echo "== $t"; node $t.js | tail -1; done
echo "== test_mono";  node test_mono.js 6000 | tail -2
echo "== core.js と Python(yaku14.py / sim14.py)の照合"; python3 ../tests/test_core_v13m.py --n 6000 | tail -6
echo "== ブラウザ(390px。pip install playwright が必要)"; python3 ui_test_tap.py | tail -3; python3 ui_test6.py | tail -4
echo "(参考)test_analyze.js / test_yakufreq.js は、自動プレイの統計。test_efficiency.js は、旧版から壊れている(isA)。test_parity*.js は、新しい語の全数CSVがないため、実行できない"
