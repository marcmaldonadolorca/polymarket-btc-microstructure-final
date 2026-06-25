"""Recompute the final public tables from the anonymised action ledger.

This script is intentionally independent from the private corpus and from the
fitted models.  It uses only:

* ``results/final_candidate_actions_anonymized.csv``;
* optionally, ``results/final_candidate_summary.csv`` for a consistency check.

It is the public audit path for the final report: anyone can verify the clean
OOS result, the post-hoc volatility diagnostic, the daily support and the
bootstrap intervals from the published ledger.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BOOTSTRAP_SEED = 42
N_BOOTSTRAP = 5_000
COST_COLUMNS = {
    "cost_0p25": "net_cost_0p25",
    "cost_0p5": "net_cost_0p5",
    "cost_1p0": "net_cost_1p0",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("results/final_candidate_actions_anonymized.csv"),
        help="Published anonymised action ledger.",
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=Path("results/final_candidate_summary.csv"),
        help="Published summary to compare against when --check is used.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path where the recomputed summary will be written.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the recomputed summary differs materially from --expected.",
    )
    return parser.parse_args()


def iid_bootstrap(values: np.ndarray) -> tuple[float, float, float]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = np.asarray(
        [rng.choice(values, size=len(values), replace=True).mean() for _ in range(N_BOOTSTRAP)]
    )
    low, high = np.quantile(means, [0.05, 0.95])
    return float(low), float(high), float((means > 0).mean())


def cluster_bootstrap(rows: pd.DataFrame) -> tuple[float, float, float]:
    grouped = rows.groupby("market_hash", sort=False)[COST_COLUMNS["cost_0p5"]]
    sums = grouped.sum().to_numpy(dtype=float)
    counts = grouped.size().to_numpy(dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    means = np.empty(N_BOOTSTRAP, dtype=float)
    for index in range(N_BOOTSTRAP):
        sampled = rng.integers(0, len(sums), size=len(sums))
        means[index] = sums[sampled].sum() / counts[sampled].sum()
    low, high = np.quantile(means, [0.05, 0.95])
    return float(low), float(high), float((means > 0).mean())


def drawdown(values: np.ndarray) -> float:
    cumulative = np.cumsum(values)
    running_peak = np.maximum.accumulate(np.r_[0.0, cumulative])[1:]
    dd = cumulative - running_peak
    return float(-dd.min())


def add_metric(rows: list[dict[str, object]], scope: str, metric: str, value: float, unit: str) -> None:
    rows.append({"scope": scope, "metric": metric, "value": float(value), "unit": unit})


def build_summary(ledger: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    scopes = {
        "base_oos": ledger,
        "low_vol_posthoc": ledger[ledger["volatility_regime"] == "low"],
        "high_vol_posthoc": ledger[ledger["volatility_regime"] == "high"],
        "missing_volatility": ledger[ledger["volatility_regime"] == "missing"],
    }

    for scope, frame in scopes.items():
        add_metric(rows, scope, "n_actions", len(frame), "actions")
        for suffix, column in COST_COLUMNS.items():
            add_metric(rows, scope, f"mean_net_{suffix}", frame[column].mean(), "ticks/action")

    daily_base = ledger.groupby("session_day")[COST_COLUMNS["cost_0p5"]].mean()
    add_metric(rows, "base_oos", "positive_days_cost_0p5", (daily_base > 0).sum(), "days")
    add_metric(rows, "base_oos", "n_days", daily_base.size, "days")

    low = scopes["low_vol_posthoc"]
    daily_low = low.groupby("session_day")[COST_COLUMNS["cost_0p5"]].mean()
    add_metric(rows, "low_vol_posthoc", "positive_days_cost_0p5", (daily_low > 0).sum(), "days")
    add_metric(rows, "low_vol_posthoc", "n_days", daily_low.size, "days")

    iid_low, iid_high, iid_p = iid_bootstrap(low[COST_COLUMNS["cost_0p5"]].to_numpy(dtype=float))
    add_metric(rows, "low_vol_posthoc", "iid_bootstrap_ci90_low", iid_low, "ticks/action")
    add_metric(rows, "low_vol_posthoc", "iid_bootstrap_ci90_high", iid_high, "ticks/action")
    add_metric(rows, "low_vol_posthoc", "iid_bootstrap_p_positive", iid_p, "probability")

    cluster_low, cluster_high, cluster_p = cluster_bootstrap(low)
    add_metric(rows, "low_vol_posthoc", "market_cluster_ci90_low", cluster_low, "ticks/action")
    add_metric(rows, "low_vol_posthoc", "market_cluster_ci90_high", cluster_high, "ticks/action")
    add_metric(rows, "low_vol_posthoc", "market_cluster_p_positive", cluster_p, "probability")
    add_metric(
        rows,
        "low_vol_posthoc",
        "diagnostic_max_drawdown",
        drawdown(low[COST_COLUMNS["cost_0p5"]].to_numpy(dtype=float)),
        "ticks",
    )
    add_metric(rows, "low_vol_posthoc", "unique_markets", low["market_hash"].nunique(), "markets")
    add_metric(
        rows,
        "low_vol_posthoc",
        "max_actions_per_market",
        low.groupby("market_hash").size().max(),
        "actions/market",
    )
    return pd.DataFrame(rows, columns=["scope", "metric", "value", "unit"])


def check_summary(recomputed: pd.DataFrame, expected_path: Path) -> None:
    expected = pd.read_csv(expected_path)
    merged = recomputed.merge(
        expected,
        on=["scope", "metric", "unit"],
        how="outer",
        suffixes=("_recomputed", "_expected"),
        indicator=True,
    )
    if not (merged["_merge"] == "both").all():
        missing = merged[merged["_merge"] != "both"]
        raise SystemExit(f"Summary rows differ:\n{missing}")

    # The ledger is rounded to six decimals, while the original summary was
    # generated before rounding.  A small tolerance is therefore expected.
    diff = (merged["value_recomputed"] - merged["value_expected"]).abs()
    bad = merged[diff > 2e-4].copy()
    if not bad.empty:
        bad["abs_diff"] = diff[diff > 2e-4]
        raise SystemExit(f"Summary values differ materially:\n{bad}")


def main() -> None:
    args = parse_args()
    ledger = pd.read_csv(args.ledger)
    summary = build_summary(ledger)
    if args.out is not None:
        summary.to_csv(args.out, index=False)
    if args.check:
        check_summary(summary, args.expected)

    key = summary.set_index(["scope", "metric"])["value"]
    print(f"Base OOS @0.5: n={int(key[('base_oos', 'n_actions')])}, "
          f"mean={key[('base_oos', 'mean_net_cost_0p5')]:+.3f}")
    print(f"Low-vol post-hoc @0.5: n={int(key[('low_vol_posthoc', 'n_actions')])}, "
          f"mean={key[('low_vol_posthoc', 'mean_net_cost_0p5')]:+.3f}")
    print(f"Market-cluster IC90: "
          f"[{key[('low_vol_posthoc', 'market_cluster_ci90_low')]:+.3f}, "
          f"{key[('low_vol_posthoc', 'market_cluster_ci90_high')]:+.3f}]")
    if args.check:
        print("Public ledger check: OK")


if __name__ == "__main__":
    main()
