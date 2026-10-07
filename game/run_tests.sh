#!/bin/sh
# ゲーム(game/)の作り直し〜確認。出力HTMLは /mnt/user-data/outputs(HM_OUT_DIR で変えられる)。pip install playwright が必要(ブラウザの確認)。
set -e
cd "$(dirname "$0")"
echo "### v1.3m の辞書(../v13m)で、ゲームを作って確認"
HM_DATA_DIR=../v13m python3 make_data.py && python3 build.py
for t in test_batch test_cmd test_oho2 test_uo test_tri test_giongo test_mono test_tatsu; do echo "== $t: $(node $t.js | tail -1)"; done
python3 ../tests/test_core_v13m.py --n 6000 | tail -5
python3 ui_test_tap.py | tail -2; python3 ui_test6.py | tail -3
echo "### dan5 の辞書(../dan5)で、判定の照合"
python3 ../dan5/gen.py | tail -3; python3 ../tests/test_dan5_gen.py | tail -1
HM_DATA_DIR=../dan5 python3 make_data.py
for t in test_mono test_tatsu test_parity test_parity_sample; do echo "== $t: $(node $t.js | tail -1)"; done
node test_efficiency.js 400 | head -1
python3 ../tests/test_core_v13m.py --dir dan5 --n 6000 | tail -5
python3 ../dan5/test_prototype.py | tail -2
echo "### dan6 の辞書(../dan6)で、判定の照合"
python3 ../dan6/gen.py | tail -3; python3 ../tests/test_dan6_gen.py | tail -1; python3 ../tests/test_goro14.py | tail -1; python3 ../tests/test_skip.py | tail -1
HM_DATA_DIR=../dan6 HM_MODX=0.05 python3 make_data.py
for t in test_mono test_tatsu; do echo "== $t: $(node $t.js | tail -1)"; done
for t in test_parity test_parity_sample; do echo "== $t: $(HM_DIRNAME=dan6 HM_REGEN=1 node $t.js | tail -1)"; done
python3 ../tests/test_yaku14.py --dir dan6 --n 3000 | tail -3
python3 ../tests/test_core_v13m.py --dir dan6 --n 6000 | tail -5
python3 ../dan6/test_prototype.py | tail -4
echo "(参考)test_analyze.js / test_yakufreq.js は、自動プレイの統計"
