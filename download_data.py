"""
運用実績データダウンロードスクリプト

取得データ:
  [実ファンド] eMAXIS Slim 米国株式(S&P500)   基準価額 2018-07-03〜現在
  [実ファンド] eMAXIS Slim 全世界株式(AC)      基準価額 2018-10-31〜現在
  [代替指数]   S&P500 指数 (^GSPC)             過去20年分
  [代替指数]   ACWI ETF                        過去20年分（2008年以降）

データソース:
  実ファンド : 三菱UFJアセットマネジメント公式サイト内部API
  代替指数   : Yahoo Finance (yfinance)
"""

import json
import os
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

TODAY = datetime.today().strftime("%Y-%m-%d")
START_20Y = "2005-01-01"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

EMAXIS_CHART_BASE = "https://emaxis.am.mufg.jp/fund_file/chart"

FUNDS = [
    {
        "fund_id": "253266",
        "name": "eMAXIS Slim 米国株式(S&P500)",
        "filename": "emaxis_slim_sp500_nav.csv",
        "label": "[3/4]",
    },
    {
        "fund_id": "253425",
        "name": "eMAXIS Slim 全世界株式(オール・カントリー)",
        "filename": "emaxis_slim_allcountry_nav.csv",
        "label": "[4/4]",
    },
]


def download_index_data() -> None:
    """S&P500 と ACWI の指数データを yfinance で取得（20年分）"""
    indices = [
        ("^GSPC", "S&P500 指数", "sp500_index_20y.csv", "[1/4]"),
        ("ACWI",  "ACWI ETF",    "acwi_etf_20y.csv",    "[2/4]"),
    ]
    for ticker, name, filename, label in indices:
        print(f"{label} {name} 取得中 ({START_20Y}〜{TODAY})...")
        df: pd.DataFrame = yf.download(
            ticker, start=START_20Y, end=TODAY, progress=False, auto_adjust=True
        )
        if df.empty:
            print(f"  警告: データが空です ({ticker})")
            continue

        df.index.name = "Date"
        out = os.path.join(DATA_DIR, filename)
        df.to_csv(out)
        print(f"  保存: {out}  ({len(df):,} 行)")


def download_fund_nav(fund: dict) -> None:
    """三菱UFJアセットマネジメント公式APIからファンドの日次基準価額を取得"""
    label = fund["label"]
    name = fund["name"]
    fund_id = fund["fund_id"]
    filename = fund["filename"]

    url = f"{EMAXIS_CHART_BASE}/chart_data_{fund_id}.js"
    print(f"{label} {name} 取得中...")

    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    payload = resp.json()
    rows = payload.get("ROWS", [])

    records = []
    for row in rows:
        try:
            date = datetime.strptime(row["BASE_DATE"], "%Y%m%d").date()
            nav = row["BASE_PRICE"]
            reinvest_nav = row["REINVEST_BASE_PRICE"]
            dist = row.get("PROFIT_DISTRIBUTION")
            net_asset = row.get("NET_ASSET_VALUE")
            records.append(
                {
                    "Date": date,
                    "NAV": nav,
                    "Reinvest_NAV": reinvest_nav,
                    "Distribution": dist,
                    "Net_Asset_Billion_JPY": net_asset,
                }
            )
        except (KeyError, ValueError):
            continue

    df = pd.DataFrame(records).sort_values("Date").reset_index(drop=True)
    out = os.path.join(DATA_DIR, filename)
    df.to_csv(out, index=False)
    print(f"  保存: {out}  ({len(df):,} 行, {df['Date'].min()} 〜 {df['Date'].max()})")


def main() -> None:
    print(f"データダウンロード開始 — {TODAY}")
    print("=" * 55)

    download_index_data()
    for fund in FUNDS:
        download_fund_nav(fund)

    print("=" * 55)
    print("完了。data/ ディレクトリを確認してください。\n")

    # 取得結果サマリー
    print("【保存ファイル一覧】")
    for f in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f:<45} {size/1024:>7.1f} KB")


if __name__ == "__main__":
    main()
