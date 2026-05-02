"""
アプリのスクリーンショットを取得して docs/images/ に保存するスクリプト。
Streamlit が起動済みの状態で実行すること。
"""

import io
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

BASE_URL     = "http://localhost:8501"
OUT_DIR      = Path("docs/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)
W, H         = 1400, 900   # ブラウザウィンドウサイズ
SCROLL_JS  = "document.querySelector('.stMain').scrollTop = {y}"
SCROLL_GET = "document.querySelector('.stMain').scrollTop"


def wait_charts(page, min_count: int = 1, timeout: int = 20_000) -> None:
    page.wait_for_function(
        f"document.querySelectorAll('.js-plotly-plot').length >= {min_count}",
        timeout=timeout,
    )
    time.sleep(2.5)


def scroll_to(page, y: int) -> None:
    page.evaluate(SCROLL_JS.format(y=y))
    time.sleep(0.6)


def viewport_shot(page, path: str) -> None:
    """現在のビューポートをそのまま撮影する。"""
    img_bytes = page.screenshot(full_page=False)
    img = Image.open(io.BytesIO(img_bytes))
    img.save(path)
    print(f"  保存: {path}  ({img.width}×{img.height}px)")


def centered_shot(page, element_y: int, path: str, capture_h: int = H) -> None:
    """要素の y 座標を中心に表示してビューポート撮影する。"""
    scroll_y = max(0, element_y - (H - capture_h) // 2 - 40)
    scroll_to(page, scroll_y)
    viewport_shot(page, path)


def run() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
        )
        page = ctx.new_page()

        # ── ページ読み込み ──────────────────────────────────────
        print("ページ読み込み中...")
        page.goto(BASE_URL, wait_until="networkidle")
        wait_charts(page, min_count=2)

        # 各グラフの座標を取得
        charts = page.locator(".js-plotly-plot").all()
        boxes  = [c.bounding_box() for c in charts]
        print(f"  グラフ数: {len(charts)}")
        for i, b in enumerate(boxes):
            if b:
                print(f"  chart[{i}]: y={b['y']:.0f}px  h={b['height']:.0f}px")

        bar_y = boxes[0]["y"] if boxes[0] else 900
        pie_y = boxes[1]["y"] if len(boxes) > 1 and boxes[1] else 2000

        # ── 1. ポートフォリオ入力カード（最上部）──────────────
        print("\n[1/5] ポートフォリオ入力カード")
        scroll_to(page, 0)
        viewport_shot(page, str(OUT_DIR / "01_portfolio_input.png"))

        # ── 2. 棒グラフ ─────────────────────────────────────────
        print("[2/5] 棒グラフ")
        # グラフを画面中央付近に来るようスクロール
        scroll_to(page, max(0, int(bar_y) - 200))
        viewport_shot(page, str(OUT_DIR / "02_bar_chart.png"))

        # ── 3. 最終結果サマリー ──────────────────────────────────
        print("[3/5] 最終結果サマリー")
        # 棒グラフの下にサマリーがあるので、棒グラフ下端へスクロール
        scroll_to(page, int(bar_y) + int(boxes[0]["height"]) - 100 if boxes[0] else 1400)
        viewport_shot(page, str(OUT_DIR / "03_summary.png"))

        # ── 4. 円グラフ ─────────────────────────────────────────
        print("[4/5] 円グラフ")
        # 円グラフ見出しが上部に入るようスクロール
        scroll_to(page, max(0, int(pie_y) - 120))
        viewport_shot(page, str(OUT_DIR / "04_pie_chart.png"))

        # ── 5. 実績データ参照タブ ─────────────────────────────
        print("[5/5] 実績データ参照タブ")
        page.click("text=📈 実績データ参照")
        wait_charts(page, min_count=3)
        scroll_to(page, 0)
        viewport_shot(page, str(OUT_DIR / "05_history_tab.png"))

        browser.close()

    saved = sorted(OUT_DIR.glob("*.png"))
    print(f"\n完了 — {len(saved)} 枚保存:")
    for p in saved:
        print(f"  {p}")


if __name__ == "__main__":
    run()
