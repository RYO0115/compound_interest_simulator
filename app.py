"""複利シミュレーター — Streamlit GUI版"""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulate import simulate

st.set_page_config(
    page_title="複利シミュレーター",
    page_icon="📈",
    layout="wide",
)

st.title("📈 複利シミュレーター")
st.caption("元本・年利・運用期間・複利頻度・毎月の追加投資額を設定してシミュレーションできます。")

DATA_DIR = "data"

# ── 実績データ読み込み ────────────────────────────────────────
@st.cache_data
def load_fund_data() -> dict:
    """ファンドのNAVデータを読み込みCAGRを算出して返す。"""
    files = {
        "sp500": ("emaxis_slim_sp500_nav.csv", "eMAXIS Slim 米国株式(S&P500)"),
        "allcountry": ("emaxis_slim_allcountry_nav.csv", "eMAXIS Slim 全世界株式(オール・カントリー)"),
    }
    result = {}
    for key, (filename, name) in files.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
        first_nav = df.iloc[0]["NAV"]
        last_nav = df.iloc[-1]["NAV"]
        total_years = (df.iloc[-1]["Date"] - df.iloc[0]["Date"]).days / 365.25
        cagr = (last_nav / first_nav) ** (1 / total_years) - 1
        result[key] = {
            "name": name,
            "df": df,
            "cagr": cagr,
            "total_return_pct": (last_nav / first_nav - 1) * 100,
            "start_date": df.iloc[0]["Date"].date(),
            "end_date": df.iloc[-1]["Date"].date(),
            "total_years": total_years,
        }
    return result


def calc_annual_returns(df: pd.DataFrame) -> pd.DataFrame:
    """年末基準価額から各暦年のリターン(%)を計算する。"""
    max_date = df["Date"].max()
    df = df.copy()
    df["Year"] = df["Date"].dt.year
    yearly_last = df.groupby("Year")["NAV"].last()
    years = sorted(yearly_last.index.tolist())

    records = []
    for i in range(1, len(years)):
        yr, prev_yr = years[i], years[i - 1]
        if yr - prev_yr != 1:
            continue
        if yr == max_date.year and max_date.month < 12:
            continue  # 当年は部分データのためスキップ
        ret = (yearly_last[yr] / yearly_last[prev_yr] - 1) * 100
        records.append({"year": yr, "return_pct": ret})
    return pd.DataFrame(records)


fund_data = load_fund_data()

# ── サイドバー: パラメータ入力 ───────────────────────────────
with st.sidebar:
    st.header("⚙️ シミュレーション設定")

    principal = st.number_input(
        "元本 (円)",
        min_value=0,
        max_value=100_000_000,
        value=1_000_000,
        step=100_000,
        format="%d",
    )

    # 年利設定モード
    st.subheader("年利の設定")
    rate_options = ["手動入力"]
    if "sp500" in fund_data:
        rate_options.append(f"S&P500 実績ベース ({fund_data['sp500']['cagr'] * 100:.2f}%)")
    if "allcountry" in fund_data:
        rate_options.append(f"オール・カントリー 実績ベース ({fund_data['allcountry']['cagr'] * 100:.2f}%)")

    rate_mode = st.radio("年利の設定方法", rate_options, index=0)

    if rate_mode == "手動入力":
        annual_rate_pct = st.slider(
            "年利 (%)",
            min_value=0.1,
            max_value=20.0,
            value=5.0,
            step=0.1,
            format="%.1f",
        )
        annual_rate = annual_rate_pct / 100
    elif "S&P500" in rate_mode and "sp500" in fund_data:
        fd = fund_data["sp500"]
        annual_rate = fd["cagr"]
        st.info(
            f"**{fd['name']}** の実績CAGR  \n"
            f"{fd['start_date']} 〜 {fd['end_date']}  \n"
            f"**{annual_rate * 100:.2f}% / 年**"
        )
    else:
        fd = fund_data["allcountry"]
        annual_rate = fd["cagr"]
        st.info(
            f"**{fd['name']}** の実績CAGR  \n"
            f"{fd['start_date']} 〜 {fd['end_date']}  \n"
            f"**{annual_rate * 100:.2f}% / 年**"
        )

    years = st.slider(
        "運用期間 (年)",
        min_value=1,
        max_value=50,
        value=20,
        step=1,
    )

    compound_freq = st.selectbox(
        "複利計算の頻度",
        options=[1, 4, 12, 365],
        index=2,
        format_func=lambda x: {
            1: "年複利 (1回/年)",
            4: "四半期複利 (4回/年)",
            12: "月複利 (12回/年)",
            365: "日複利 (365回/年)",
        }[x],
    )

    monthly_contribution = st.number_input(
        "毎月の追加投資額 (円)",
        min_value=0,
        max_value=1_000_000,
        value=30_000,
        step=5_000,
        format="%d",
    )

# ── タブ ──────────────────────────────────────────────────────
tab_sim, tab_history = st.tabs(["📊 シミュレーション", "📈 実績データ参照"])

# ════════════════════════════════════════════════════════
# タブ1: シミュレーション（既存機能そのまま）
# ════════════════════════════════════════════════════════
with tab_sim:
    results = simulate(
        principal=principal,
        annual_rate=annual_rate,
        years=years,
        compound_freq=compound_freq,
        monthly_contribution=monthly_contribution,
    )
    df_sim = pd.DataFrame(results)

    st.caption(f"使用年利: **{annual_rate * 100:.2f}%**")

    final = results[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最終残高", f"¥{final['balance']:,.0f}")
    col2.metric("累計投資額", f"¥{final['total_contributed']:,.0f}")
    col3.metric("総利益", f"¥{final['gain']:,.0f}")
    col4.metric("総利益率", f"{final['gain_rate']:.1f}%")

    st.divider()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_sim["year"], y=df_sim["total_contributed"],
        name="累計投資額", marker_color="#4C9BE8",
    ))
    fig.add_trace(go.Bar(
        x=df_sim["year"], y=df_sim["gain"],
        name="利益", marker_color="#F4A261",
    ))
    fig.add_trace(go.Scatter(
        x=df_sim["year"], y=df_sim["balance"],
        name="残高合計", mode="lines+markers",
        line=dict(color="#E63946", width=2), marker=dict(size=6),
    ))
    fig.update_layout(
        barmode="stack", title="資産推移",
        xaxis_title="年", yaxis_title="金額 (円)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", height=480,
    )
    fig.update_xaxes(tickmode="linear", dtick=max(1, years // 10))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 年次データ一覧"):
        display_df = df_sim.copy()
        display_df.columns = ["年", "残高 (円)", "累計投資額 (円)", "利益 (円)", "利益率 (%)"]
        for col in ["残高 (円)", "累計投資額 (円)", "利益 (円)"]:
            display_df[col] = display_df[col].map(lambda v: f"{v:,.0f}")
        display_df["利益率 (%)"] = display_df["利益率 (%)"].map(lambda v: f"{v:.1f}%")
        display_df["年"] = display_df["年"].map(lambda v: f"{v}年目")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════
# タブ2: 実績データ参照（新機能）
# ════════════════════════════════════════════════════════
with tab_history:
    if not fund_data:
        st.warning("データファイルが見つかりません。`uv run download_data.py` を実行してください。")
        st.stop()

    COLORS = {"sp500": "#E63946", "allcountry": "#4C9BE8"}
    LABELS = {
        "sp500": "eMAXIS Slim S&P500",
        "allcountry": "eMAXIS Slim オール・カントリー",
    }

    # ── サマリーカード ─────────────────────────────────────────
    cols = st.columns(len(fund_data))
    for col, (key, fd) in zip(cols, fund_data.items()):
        with col:
            st.subheader(LABELS[key])
            st.metric("CAGR（年平均リターン）", f"{fd['cagr'] * 100:.2f}%")
            st.metric("設定来累計リターン", f"{fd['total_return_pct']:.1f}%")
            st.caption(
                f"対象期間: {fd['start_date']} 〜 {fd['end_date']}  \n"
                f"（{fd['total_years']:.1f}年間）"
            )

    st.divider()

    # ── 基準価額推移チャート ───────────────────────────────────
    fig2 = go.Figure()
    for key, fd in fund_data.items():
        df_nav = fd["df"]
        fig2.add_trace(go.Scatter(
            x=df_nav["Date"], y=df_nav["NAV"],
            name=LABELS[key],
            line=dict(color=COLORS[key], width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>基準価額: %{y:,.0f}円<extra></extra>",
        ))
    fig2.update_layout(
        title="基準価額の推移（設定来）",
        xaxis_title="日付", yaxis_title="基準価額 (円)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", height=420,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── 年次リターン比較 ───────────────────────────────────────
    st.subheader("年次リターン比較")

    fig3 = go.Figure()
    has_bar = False
    for key, fd in fund_data.items():
        ar = calc_annual_returns(fd["df"])
        if ar.empty:
            continue
        has_bar = True
        avg_ret = ar["return_pct"].mean()
        fig3.add_trace(go.Bar(
            x=ar["year"], y=ar["return_pct"],
            name=f"{LABELS[key]}（平均: {avg_ret:.1f}%）",
            marker_color=COLORS[key],
        ))

    if has_bar:
        fig3.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig3.update_layout(
            barmode="group",
            title="暦年リターン（%）",
            xaxis_title="年", yaxis_title="リターン (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", height=380,
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.caption(
        "※ CAGR = 設定日から最終データ日までの年率換算リターン（複利ベース）。"
        "年次リターンは各暦年末の基準価額を用いた前年比。"
        "過去の実績であり将来のリターンを保証するものではありません。"
    )
