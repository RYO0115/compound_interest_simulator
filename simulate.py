"""
複利シミュレーター - CLIスクリプト版

変更可能なパラメータ:
  PRINCIPAL          : 元本 (円)
  ANNUAL_RATE        : 年利 (例: 0.05 = 5%)
  YEARS              : 運用期間 (年)
  COMPOUND_FREQ      : 複利計算の頻度 (1=年複利, 12=月複利, 365=日複利)
  MONTHLY_CONTRIBUTION: 毎月の追加投資額 (円) ※ 0で積立なし
"""

# ============================================================
# パラメータ設定 — ここを変更してシミュレーション条件を調整
# ============================================================
PRINCIPAL            = 1_000_000   # 元本 (円)
ANNUAL_RATE          = 0.05        # 年利 (5%)
YEARS                = 20          # 運用期間 (年)
COMPOUND_FREQ        = 12          # 複利頻度 (12 = 月複利)
MONTHLY_CONTRIBUTION = 30_000      # 毎月の追加投資額 (円)
# ============================================================


def simulate(
    principal: float,
    annual_rate: float,
    years: int,
    compound_freq: int,
    monthly_contribution: float,
) -> list[dict]:
    """複利シミュレーションを実行し、各期末の状態を返す。"""
    rate_per_period = annual_rate / compound_freq
    total_periods = years * compound_freq
    # 月次追加投資額を 1 期あたりの金額へ変換
    contribution_per_period = monthly_contribution * 12 / compound_freq

    results = []
    balance = principal
    total_contributed = principal

    for period in range(1, total_periods + 1):
        balance = (balance + contribution_per_period) * (1 + rate_per_period)
        total_contributed += contribution_per_period

        if period % compound_freq == 0:  # 年末のみ記録
            year = period // compound_freq
            gain = balance - total_contributed
            results.append(
                {
                    "year": year,
                    "balance": balance,
                    "total_contributed": total_contributed,
                    "gain": gain,
                    "gain_rate": gain / total_contributed * 100,
                }
            )

    return results


def print_results(results: list[dict], params: dict) -> None:
    print("\n" + "=" * 62)
    print("  複利シミュレーション結果")
    print("=" * 62)
    print(f"  元本          : {params['principal']:>12,.0f} 円")
    print(f"  年利          : {params['annual_rate'] * 100:>11.2f} %")
    print(f"  運用期間      : {params['years']:>11} 年")
    print(f"  複利頻度      : {params['compound_freq']:>11} 回/年")
    print(f"  毎月追加投資  : {params['monthly_contribution']:>12,.0f} 円")
    print("-" * 62)
    print(f"  {'年':>4}  {'残高':>16}  {'累計投資額':>14}  {'利益':>14}  {'利益率':>7}")
    print("-" * 62)

    for r in results:
        print(
            f"  {r['year']:>4}年  "
            f"{r['balance']:>14,.0f}円  "
            f"{r['total_contributed']:>12,.0f}円  "
            f"{r['gain']:>12,.0f}円  "
            f"{r['gain_rate']:>6.1f}%"
        )

    final = results[-1]
    print("=" * 62)
    print(f"  最終残高      : {final['balance']:>12,.0f} 円")
    print(f"  累計投資額    : {final['total_contributed']:>12,.0f} 円")
    print(f"  総利益        : {final['gain']:>12,.0f} 円")
    print(f"  総利益率      : {final['gain_rate']:>11.1f} %")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    params = {
        "principal": PRINCIPAL,
        "annual_rate": ANNUAL_RATE,
        "years": YEARS,
        "compound_freq": COMPOUND_FREQ,
        "monthly_contribution": MONTHLY_CONTRIBUTION,
    }
    results = simulate(**params)
    print_results(results, params)
