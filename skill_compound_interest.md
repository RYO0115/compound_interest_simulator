# Compound Interest Simulator — プロジェクト品質ガイド

機能追加・修正時に参照すること。

---

## プロジェクト構成

```
compound_interest_simulator/
├── simulate.py           # コアロジック（CLIスクリプト兼モジュール）
├── app.py                # Streamlit GUI アプリ
├── download_data.py      # 運用実績データダウンロードスクリプト
├── data/                 # ダウンロードしたCSVデータ
│   ├── sp500_index_20y.csv              # S&P500指数（20年分）
│   ├── acwi_etf_20y.csv                 # ACWI ETF（約18年分）
│   ├── emaxis_slim_sp500_nav.csv        # eMAXIS Slim S&P500 日次基準価額
│   └── emaxis_slim_allcountry_nav.csv   # eMAXIS Slim オルカン 日次基準価額
├── pyproject.toml        # uv プロジェクト設定
└── skill_compound_interest.md  # 本ファイル
```

## 実行方法

```bash
# CLI スクリプト
uv run simulate.py

# GUI アプリ（ブラウザで http://localhost:8501 を開く）
uv run streamlit run app.py
```

## コアロジック (`simulate.py`)

### シミュレーション関数

```python
simulate(principal, annual_rate, years, compound_freq, monthly_contribution) -> list[dict]
```

- `principal` (float): 元本 (円)
- `annual_rate` (float): 年利。例: `0.05` = 5%
- `years` (int): 運用期間 (年)
- `compound_freq` (int): 複利計算の頻度。`1`=年, `4`=四半期, `12`=月, `365`=日
- `monthly_contribution` (float): 毎月の追加投資額 (円)

戻り値は `list[dict]` で、各要素は年末時点の状態:

```python
{
    "year": int,               # 経過年数
    "balance": float,          # 残高
    "total_contributed": float, # 累計投資額（元本 + 積立合計）
    "gain": float,             # 利益 = balance - total_contributed
    "gain_rate": float,        # 利益率 (%)
}
```

### 計算の基本式

毎期の更新:
```
balance = (balance + contribution_per_period) * (1 + rate_per_period)
```

- `rate_per_period = annual_rate / compound_freq`
- `contribution_per_period = monthly_contribution * 12 / compound_freq`

積立は **期首に投入してから複利計算する** 方式。

## GUI アプリ (`app.py`)

- **フレームワーク**: Streamlit + Plotly
- サイドバーでパラメータを入力 → リアルタイムにグラフ・指標が更新される
- 表示要素:
  - サマリー指標 4 枚 (最終残高 / 累計投資額 / 総利益 / 総利益率)
  - 積み上げ棒グラフ + 折れ線グラフ (Plotly)
  - 年次データ一覧テーブル (expander 内)

## パラメータの制約・仕様

| パラメータ | 型 | 最小 | 最大 | デフォルト | 単位 |
|---|---|---|---|---|---|
| 元本 | int | 0 | 1億 | 100万 | 円 |
| 年利 | float | 0.1% | 20% | 5% | % |
| 運用期間 | int | 1 | 50 | 20 | 年 |
| 複利頻度 | int | 1 | 365 | 12 | 回/年 |
| 毎月追加投資 | int | 0 | 100万 | 3万 | 円 |

## 設計上の原則

1. **コアロジックの分離**: `simulate()` 関数は純粋関数として `simulate.py` に定義し、GUI・CLI の両方から `import` して使う。新機能追加時もこの関数を起点にする。
2. **単一責任**: `simulate.py` はロジックのみ。I/O・描画・UI は `app.py` に置く。
3. **後方互換性**: `simulate()` の引数シグネチャを変更する場合は既存の呼び出し箇所 (`app.py`, `simulate.py` の `__main__` ブロック) を必ず更新する。
4. **税金・インフレは現時点で非対応**: 将来追加する場合は `simulate()` に `tax_rate` / `inflation_rate` 引数を追加し、戻り値 dict に `after_tax_balance` / `real_balance` を加える。

## 運用実績データ (`download_data.py`)

```bash
uv run download_data.py
```

### データソースと仕様

| ファイル | データソース | 期間 | 更新頻度 |
|---|---|---|---|
| `sp500_index_20y.csv` | Yahoo Finance (`^GSPC`) | 2005〜現在 | 手動実行 |
| `acwi_etf_20y.csv` | Yahoo Finance (`ACWI` ETF) | 2008〜現在 | 手動実行 |
| `emaxis_slim_sp500_nav.csv` | 三菱UFJアセットマネジメント公式API | 2018-07-03〜現在 | 手動実行 |
| `emaxis_slim_allcountry_nav.csv` | 三菱UFJアセットマネジメント公式API | 2018-10-31〜現在 | 手動実行 |

### eMAXIS Slim ファンドデータのAPIエンドポイント

```
https://emaxis.am.mufg.jp/fund_file/chart/chart_data_{fund_id}.js
```

| ファンド | fund_id |
|---|---|
| eMAXIS Slim 米国株式(S&P500) | 253266 |
| eMAXIS Slim 全世界株式(オール・カントリー) | 253425 |

レスポンスはJSON形式。主要フィールド:
- `BASE_DATE`: 日付 (`YYYYMMDD`)
- `BASE_PRICE`: 基準価額 (円)
- `REINVEST_BASE_PRICE`: 分配金再投資基準価額
- `PROFIT_DISTRIBUTION`: 分配金 (無分配ファンドは null)
- `NET_ASSET_VALUE`: 純資産総額 (億円)

### 注意事項

- 両ファンドとも**2018年設定**のため過去20年分は存在しない。20年分が必要な場合は代替指数 (S&P500 / ACWI) を使用。
- eMAXIS APIは公式の公開APIではなく、公式サイト内のチャート向けエンドポイント。将来的にURLが変更される可能性がある。

## 依存ライブラリ

```
streamlit    # GUI フレームワーク
plotly       # インタラクティブグラフ
pandas       # テーブル表示
yfinance     # Yahoo Finance データ取得
requests     # HTTP クライアント
beautifulsoup4  # HTML パーサー（将来用）
```

追加時は `uv add <package>` を使用。`pip install` は使わない。
