"""playwright の起動の共通部分。環境にある chromium(PLAYWRIGHT_BROWSERS_PATH)を、そのまま使う。"""
import glob, os
from playwright.sync_api import sync_playwright

def launch(p):
    cands = sorted(glob.glob(os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"), "chromium-*", "chrome-linux*", "chrome")))
    try:
        return p.chromium.launch()
    except Exception:
        return p.chromium.launch(executable_path=cands[0])

HTML = os.environ.get("HM_HTML", "file:///mnt/user-data/outputs/hiragana-mahjong-test.html")
