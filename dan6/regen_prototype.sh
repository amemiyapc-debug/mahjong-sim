#!/bin/sh
# 試作HTMLを、パッチ前の元(b44927c)から作り直す。出力: prototype/hiragana_tap_prototype.html(一周版100語)・prototype/hiragana_tap_prototype_365.html(365語版)
cd "$(dirname "$0")/.." && git show b44927c:prototype/hiragana_tap_prototype.html > prototype/hiragana_tap_prototype.html && python3 dan6/make_prototype.py
