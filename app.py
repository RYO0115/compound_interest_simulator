"""複利シミュレーター — Streamlit GUI版（マルチポートフォリオ対応）"""

import os
import uuid

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
st.caption("複数のポートフォリオを同時にシミュレーション・比較できます。")

DATA_DIR = "data"

# ── ポートフォリオカラーパレット ──────────────────────────────
_COLORS = [
    "#4C9BE8",  # blue
    "#E63946",  # red
    "#2DC653",  # green
    "#F4A261",  # orange
    "#9B59B6",  # purple
    "#F72585",  # pink
    "#00B4D8",  # cyan
    "#FB8500",  # amber
    "#06D6A0",  # teal
    "#FFD166",  # yellow
]


def _lighten(hex_color: str, factor: float = 0.5) -> str:
    """Hex カラーを白方向に薄くする（投資額バー用）。"""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return "#{:02x}{:02x}{:02x}".format(
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def _port_color(idx: int) -> str:
    return _COLORS[idx % len(_COLORS)]


# ── ファンド実績データ ────────────────────────────────────────
@st.cache_data
def load_fund_data() -> dict:
    files = {
        "sp500":      ("emaxis_slim_sp500_nav.csv",       "eMAXIS Slim 米国株式(S&P500)"),
        "allcountry": ("emaxis_slim_allcountry_nav.csv",  "eMAXIS Slim 全世界株式(オール・カントリー)"),
    }
    result = {}
    for key, (fname, name) in files.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
        first, last = df.iloc[0]["NAV"], df.iloc[-1]["NAV"]
        yrs = (df.iloc[-1]["Date"] - df.iloc[0]["Date"]).days / 365.25
        result[key] = {
            "name": name,
            "df": df,
            "cagr": (last / first) ** (1 / yrs) - 1,
            "total_return_pct": (last / first - 1) * 100,
            "start_date": df.iloc[0]["Date"].date(),
            "end_date": df.iloc[-1]["Date"].date(),
            "total_years": yrs,
        }
    return result


def _calc_annual_returns(df: pd.DataFrame) -> pd.DataFrame:
    max_date = df["Date"].max()
    df = df.copy()
    df["Year"] = df["Date"].dt.year
    yl = df.groupby("Year")["NAV"].last()
    years = sorted(yl.index.tolist())
    rows = []
    for i in range(1, len(years)):
        yr, pyr = years[i], years[i - 1]
        if yr - pyr != 1:
            continue
        if yr == max_date.year and max_date.month < 12:
            continue
        rows.append({"year": yr, "return_pct": (yl[yr] / yl[pyr] - 1) * 100})
    return pd.DataFrame(rows)


fund_data = load_fund_data()

# ── セッションステート: ポートフォリオリスト ─────────────────
def _new_portfolio(label: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": label,
        # 以下はウィジェットの初期値として使用（以降は widget key が管理）
        "_init_principal":    1_000_000,
        "_init_rate_pct":     5.0,
        "_init_monthly":      30_000,
        "_init_years":        20,
        "_init_rate_mode":    0,   # radio index
    }


if "portfolios" not in st.session_state:
    st.session_state.portfolios = [_new_portfolio("ポートフォリオ 1")]
if "port_counter" not in st.session_state:
    st.session_state.port_counter = 2

# ── タブ ─────────────────────────────────────────────────────
tab_sim, tab_history = st.tabs(["📊 シミュレーション", "📈 実績データ参照"])

# ════════════════════════════════════════════════════════════
# タブ1: マルチポートフォリオ シミュレーション
# ════════════════════════════════════════════════════════════
with tab_sim:

    # ── 共通設定 ─────────────────────────────────────────────
    with st.expander("⚙️ 共通設定（複利計算の頻度）", expanded=False):
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

    # ── ポートフォリオ追加ボタン ──────────────────────────────
    if st.button("➕ ポートフォリオを追加", type="secondary"):
        label = f"ポートフォリオ {st.session_state.port_counter}"
        st.session_state.portfolios.append(_new_portfolio(label))
        st.session_state.port_counter += 1
        st.rerun()

    st.divider()

    # ── 年利オプション文字列（共有） ─────────────────────────
    rate_options = ["手動入力"]
    if "sp500" in fund_data:
        rate_options.append(f"S&P500 実績ベース ({fund_data['sp500']['cagr'] * 100:.2f}%)")
    if "allcountry" in fund_data:
        rate_options.append(f"オルカン 実績ベース ({fund_data['allcountry']['cagr'] * 100:.2f}%)")

    # ── ポートフォリオカード ──────────────────────────────────
    sim_configs: list[dict] = []   # 描画後に計算で使う設定
    to_delete: int | None = None

    for port_idx, portfolio in enumerate(st.session_state.portfolios):
        pid = portfolio["id"]
        color = _port_color(port_idx)

        # カード左帯
        st.markdown(
            f"<div style='border-left:5px solid {color};"
            f"padding:2px 0 2px 10px;margin-bottom:2px'>"
            f"<b style='color:{color}'>{portfolio['name']}</b></div>",
            unsafe_allow_html=True,
        )

        with st.container():
            # 1行目: 名前 + 削除
            r1a, r1b = st.columns([5, 1])
            with r1a:
                name_val = st.text_input(
                    "ポートフォリオ名",
                    value=portfolio["name"],
                    key=f"name_{pid}",
                    label_visibility="collapsed",
                )
                # 次のレンダー時のカード見出しに使うため保存
                st.session_state.portfolios[port_idx]["name"] = name_val
            with r1b:
                if len(st.session_state.portfolios) > 1:
                    if st.button("🗑️ 削除", key=f"del_{pid}", use_container_width=True):
                        to_delete = port_idx

            # 2行目: 元本 / 毎月追加 / 運用期間
            c1, c2, c3 = st.columns(3)
            with c1:
                principal = st.number_input(
                    "元本 (円)",
                    value=portfolio["_init_principal"],
                    min_value=0, max_value=100_000_000,
                    step=100_000, format="%d",
                    key=f"principal_{pid}",
                )
            with c2:
                monthly = st.number_input(
                    "毎月追加投資額 (円)",
                    value=portfolio["_init_monthly"],
                    min_value=0, max_value=1_000_000,
                    step=5_000, format="%d",
                    key=f"monthly_{pid}",
                )
            with c3:
                port_years = st.slider(
                    "運用期間 (年)",
                    min_value=1, max_value=50,
                    value=portfolio["_init_years"],
                    key=f"years_{pid}",
                )

            # 3行目: 年利設定モード
            rate_mode = st.radio(
                "年利の設定方法",
                rate_options,
                index=portfolio["_init_rate_mode"],
                horizontal=True,
                key=f"rate_mode_{pid}",
            )

            # 年利モードに応じた表示と annual_rate 計算
            if rate_mode == "手動入力":
                rate_pct = st.slider(
                    "年利 (%)",
                    min_value=0.1, max_value=20.0,
                    value=portfolio["_init_rate_pct"],
                    step=0.1, format="%.1f",
                    key=f"rate_pct_{pid}",
                )
                annual_rate = rate_pct / 100
                rate_label = f"{rate_pct:.2f}%（手動）"
            elif "S&P500" in rate_mode and "sp500" in fund_data:
                fd = fund_data["sp500"]
                annual_rate = fd["cagr"]
                rate_label = f"{annual_rate * 100:.2f}%（S&P500 実績 {fd['start_date']}〜{fd['end_date']}）"
                st.caption(f"📊 使用年利: **{annual_rate * 100:.2f}%** — {fd['name']} 設定来CAGR")
            else:
                fd = fund_data["allcountry"]
                annual_rate = fd["cagr"]
                rate_label = f"{annual_rate * 100:.2f}%（オルカン実績 {fd['start_date']}〜{fd['end_date']}）"
                st.caption(f"📊 使用年利: **{annual_rate * 100:.2f}%** — {fd['name']} 設定来CAGR")

            sim_configs.append({
                "name":       name_val,
                "principal":  principal,
                "annual_rate": annual_rate,
                "monthly":    monthly,
                "years":      port_years,
                "color":      color,
                "rate_label": rate_label,
            })

        st.divider()

    # 削除処理（ループ外で実行）
    if to_delete is not None:
        st.session_state.portfolios.pop(to_delete)
        st.rerun()

    # ── シミュレーション実行 ──────────────────────────────────
    all_results: list[dict] = []
    for cfg in sim_configs:
        rows = simulate(
            principal=cfg["principal"],
            annual_rate=cfg["annual_rate"],
            years=cfg["years"],
            compound_freq=compound_freq,
            monthly_contribution=cfg["monthly"],
        )
        all_results.append({"cfg": cfg, "rows": rows, "df": pd.DataFrame(rows)})

    # ── グループ積み上げ棒グラフ ─────────────────────────────
    fig = go.Figure()
    for port_idx, res in enumerate(all_results):
        cfg = res["cfg"]
        df = res["df"]
        color = cfg["color"]
        light = _lighten(color)
        name = cfg["name"]

        # 投資額バー（淡色）
        fig.add_trace(go.Bar(
            name="投資額",
            x=df["year"],
            y=df["total_contributed"],
            marker_color=light,
            offsetgroup=port_idx,
            legendgroup=name,
            legendgrouptitle_text=name,
            hovertemplate=(
                f"<b>{name}</b><br>"
                "%{x}年目<br>"
                "累計投資額: ¥%{y:,.0f}<extra></extra>"
            ),
        ))
        # 利益バー（濃色、積み上げ）
        fig.add_trace(go.Bar(
            name="利益",
            x=df["year"],
            y=df["gain"],
            base=df["total_contributed"],
            marker_color=color,
            offsetgroup=port_idx,
            legendgroup=name,
            hovertemplate=(
                f"<b>{name}</b><br>"
                "%{x}年目<br>"
                "利益: ¥%{customdata:,.0f}<br>"
                "残高: ¥%{base:,.0f}+¥%{y:,.0f}<extra></extra>"
            ),
            customdata=df["gain"],
        ))

    max_years = max(res["cfg"]["years"] for res in all_results)
    fig.update_layout(
        barmode="group",
        title="ポートフォリオ別 資産推移比較",
        xaxis_title="年",
        yaxis_title="金額 (円)",
        legend=dict(
            groupclick="toggleitem",
            orientation="h",
            yanchor="bottom", y=1.01,
            xanchor="right", x=1,
        ),
        hovermode="x unified",
        height=520,
        bargap=0.15,
        bargroupgap=0.05,
    )
    fig.update_xaxes(tickmode="linear", dtick=max(1, max_years // 10))
    st.plotly_chart(fig, use_container_width=True)

    # ── 最終結果サマリー ─────────────────────────────────────
    st.subheader("最終結果サマリー")
    sum_cols = st.columns(len(all_results))
    for col, res in zip(sum_cols, all_results):
        cfg = res["cfg"]
        final = res["rows"][-1]
        color = cfg["color"]
        with col:
            st.markdown(
                f"<span style='color:{color};font-size:1.1em'>■</span> "
                f"**{cfg['name']}**",
                unsafe_allow_html=True,
            )
            st.metric("最終残高",   f"¥{final['balance']:,.0f}")
            st.metric("累計投資額", f"¥{final['total_contributed']:,.0f}")
            st.metric("総利益",     f"¥{final['gain']:,.0f}")
            st.metric("総利益率",   f"{final['gain_rate']:.1f}%")
            st.caption(f"年利: {cfg['rate_label']}  |  期間: {cfg['years']}年")

    # ── 年次データ詳細（折り畳み） ───────────────────────────
    with st.expander("📋 ポートフォリオ別 年次データ一覧"):
        detail_tabs = st.tabs([res["cfg"]["name"] for res in all_results])
        for tab, res in zip(detail_tabs, all_results):
            with tab:
                disp = res["df"].copy()
                disp.columns = ["年", "残高 (円)", "累計投資額 (円)", "利益 (円)", "利益率 (%)"]
                for c in ["残高 (円)", "累計投資額 (円)", "利益 (円)"]:
                    disp[c] = disp[c].map(lambda v: f"{v:,.0f}")
                disp["利益率 (%)"] = disp["利益率 (%)"].map(lambda v: f"{v:.1f}%")
                disp["年"] = disp["年"].map(lambda v: f"{v}年目")
                st.dataframe(disp, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════
# タブ2: 実績データ参照（変更なし）
# ════════════════════════════════════════════════════════════
with tab_history:
    if not fund_data:
        st.warning("データファイルが見つかりません。`uv run download_data.py` を実行してください。")
        st.stop()

    H_COLORS = {"sp500": "#E63946", "allcountry": "#4C9BE8"}
    H_LABELS = {"sp500": "eMAXIS Slim S&P500", "allcountry": "eMAXIS Slim オール・カントリー"}

    cols = st.columns(len(fund_data))
    for col, (key, fd) in zip(cols, fund_data.items()):
        with col:
            st.subheader(H_LABELS[key])
            st.metric("CAGR（年平均リターン）", f"{fd['cagr'] * 100:.2f}%")
            st.metric("設定来累計リターン", f"{fd['total_return_pct']:.1f}%")
            st.caption(
                f"対象期間: {fd['start_date']} 〜 {fd['end_date']}  \n"
                f"（{fd['total_years']:.1f}年間）"
            )

    st.divider()

    fig2 = go.Figure()
    for key, fd in fund_data.items():
        fig2.add_trace(go.Scatter(
            x=fd["df"]["Date"], y=fd["df"]["NAV"],
            name=H_LABELS[key],
            line=dict(color=H_COLORS[key], width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>基準価額: %{y:,.0f}円<extra></extra>",
        ))
    fig2.update_layout(
        title="基準価額の推移（設定来）",
        xaxis_title="日付", yaxis_title="基準価額 (円)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", height=420,
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("年次リターン比較")
    fig3 = go.Figure()
    has_bar = False
    for key, fd in fund_data.items():
        ar = _calc_annual_returns(fd["df"])
        if ar.empty:
            continue
        has_bar = True
        avg = ar["return_pct"].mean()
        fig3.add_trace(go.Bar(
            x=ar["year"], y=ar["return_pct"],
            name=f"{H_LABELS[key]}（平均: {avg:.1f}%）",
            marker_color=H_COLORS[key],
        ))
    if has_bar:
        fig3.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig3.update_layout(
            barmode="group", title="暦年リターン（%）",
            xaxis_title="年", yaxis_title="リターン (%)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified", height=380,
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.caption(
        "※ CAGR = 設定日から最終データ日までの年率換算リターン（複利ベース）。"
        "過去の実績であり将来のリターンを保証するものではありません。"
    )
