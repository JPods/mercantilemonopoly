#!/usr/bin/env python3
"""Disposable Energy, money, and economic momentum.

Disposable Energy (Bill James): how much energy people can buy with their
take-home pay. Measured here with gasoline, normalized so 1986 = 0:

    gallons(y) = income(y) / gasoline_price(y)
    DE(y)      = gallons(y) / gallons(1986) - 1

Three income variants are computed so reviewers can see what each choice does:

    original      aggregate disposable personal income (Bill's 2022 workbook method)
    per_capita    disposable personal income per person
    ex_transfers  per person, excluding personal current transfer receipts
                  (removes stimulus checks and other government transfers;
                  note it also removes Social Security and other pensions)

Then three tests:

    1. Gasoline price -> unemployment lag, monthly, 1976+ (tests the 18-month claim)
    2. Change in DE -> real GDP growth, annual, lags 0-5 years
    3. Flywheel: momentum as an exponentially weighted sum of DE changes,
       fit the time constant tau that best tracks real GDP growth

All data are pulled from public sources (FRED, EIA) and cached in data/raw/.
Run:  python3 disposable_energy.py [--refresh]
"""
import argparse
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
OUT = HERE / "output"

BASE_YEAR = 1986
START, END = 1960, 2025

FRED = {
    "dpi_agg": "A067RC1A027NBEA",   # Disposable personal income, $billions, annual
    "dpi_pc": "A229RC0A052NBEA",    # Disposable personal income per capita, $, annual
    "pop": "B230RC0A052NBEA",       # Population, thousands, annual
    "transfers": "PCTR",            # Personal current transfer receipts, $billions SAAR, monthly
    "gas_monthly": "APU000074714",  # Avg price, unleaded regular gasoline, $/gal, monthly (1976+)
    "unrate": "UNRATE",             # Unemployment rate, %, monthly
    "gdp_real": "GDPC1",            # Real GDP, chained $billions, quarterly
    "debt": "GFDEBTN",              # Federal debt, total public debt, $millions, quarterly
    "fed_assets": "WALCL",          # Federal Reserve total assets, $millions, weekly (2002+)
    "cpi": "CPIAUCSL",              # Consumer Price Index, all urban, monthly
}
EIA_GAS = "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T09.04"
EVENTS = {1973: "Oil Embargo", 1979: "Iranian Revolution", 1998: "DE peak",
          2008: "Great Recession", 2020: "COVID"}
PRINTING_BREAKS = (2008, 2020)


def fetch(name, url, refresh):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"{name}.csv"
    if refresh or not path.exists():
        print(f"[DE] fetch {name} <- {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "mercantilemonopoly-analysis"})
        with urllib.request.urlopen(req, timeout=60) as r:
            path.write_bytes(r.read())
    return path


def fred(series_id, refresh):
    path = fetch(series_id, f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}", refresh)
    df = pd.read_csv(path, parse_dates=["observation_date"], na_values=["."])
    return df.set_index("observation_date")[series_id].astype(float)


def annual(s, how="mean"):
    g = s.groupby(s.index.year)
    return g.mean() if how == "mean" else g.last()


def eia_gasoline(refresh):
    """Annual retail gasoline price: leaded regular through 1975, unleaded regular from 1976."""
    df = pd.read_csv(fetch("eia_T09.04", EIA_GAS, refresh), dtype=str)
    df = df[df["YYYYMM"].str.endswith("13")]
    df["year"] = df["YYYYMM"].str[:4].astype(int)
    df["v"] = pd.to_numeric(df["Value"], errors="coerce")
    leaded = df[df["MSN"] == "RLUCUUS"].set_index("year")["v"]
    unleaded = df[df["MSN"] == "RUUCUUS"].set_index("year")["v"]
    gas = pd.concat([leaded[leaded.index <= 1975], unleaded[unleaded.index >= 1976]])
    splice = {"1976_leaded": float(leaded.get(1976)), "1976_unleaded": float(unleaded.get(1976))}
    return gas.sort_index(), splice


def de_from(income, gas):
    gallons = income / gas
    return gallons / gallons.loc[BASE_YEAR] - 1


def lag_corr(x, y, max_lag):
    """Correlation of x(t) with y(t+lag): positive lag = x leads y."""
    rows = []
    for lag in range(max_lag + 1):
        pair = pd.concat([x, y.shift(-lag)], axis=1).dropna()
        rows.append({"lag": lag, "r": round(float(pair.iloc[:, 0].corr(pair.iloc[:, 1])), 3),
                     "n": len(pair)})
    best = max(rows, key=lambda d: abs(d["r"]))
    return rows, best


def flywheel(d_de, growth, taus):
    """Momentum M(t) = M(t-1)*(1 - 1/tau) + dDE(t). Find tau whose M best tracks GDP growth."""
    rows = []
    for tau in taus:
        m, acc = [], 0.0
        for v in d_de.fillna(0.0):
            acc = acc * (1 - 1 / tau) + v
            m.append(acc)
        mom = pd.Series(m, index=d_de.index)
        pair = pd.concat([mom, growth], axis=1).dropna()
        rows.append({"tau_years": tau, "r": round(float(pair.iloc[:, 0].corr(pair.iloc[:, 1])), 3)})
    return rows, max(rows, key=lambda d: d["r"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download all source data")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    s = {k: fred(v, args.refresh) for k, v in FRED.items()}
    gas, splice = eia_gasoline(args.refresh)

    yrs = pd.Index(range(START, END + 1), name="year")
    a = pd.DataFrame(index=yrs)
    a["gas_price"] = gas
    a["dpi_agg_bn"] = annual(s["dpi_agg"])
    a["dpi_pc"] = annual(s["dpi_pc"])
    a["pop_k"] = annual(s["pop"])
    a["transfers_bn"] = annual(s["transfers"])
    a["dpi_ex_transfers_pc"] = (a["dpi_agg_bn"] - a["transfers_bn"]) * 1e9 / (a["pop_k"] * 1e3)
    a["DE_original"] = de_from(a["dpi_agg_bn"], a["gas_price"])
    a["DE_per_capita"] = de_from(a["dpi_pc"], a["gas_price"])
    a["DE_ex_transfers"] = de_from(a["dpi_ex_transfers_pc"], a["gas_price"])
    a["real_gdp_growth_pct"] = annual(s["gdp_real"]).pct_change() * 100
    a["unemployment_pct"] = annual(s["unrate"])
    a["federal_debt_tn"] = annual(s["debt"], "last") / 1e6
    a["fed_assets_tn"] = annual(s["fed_assets"]) / 1e6
    a = a.loc[START:END]
    a.round(4).to_csv(OUT / "disposable_energy_annual.csv")

    # 1. Gasoline price -> unemployment, monthly
    gm = s["gas_monthly"].pct_change(12) * 100
    um = s["unrate"].diff(12)
    m = pd.concat([gm, um], axis=1, sort=True).dropna()
    m = m[m.index.year < 2020]  # COVID unemployment spike is not an energy event
    gas_unemp, gas_unemp_best = lag_corr(m.iloc[:, 0], m.iloc[:, 1], 36)
    real = (s["gas_monthly"] / s["cpi"]).pct_change(12) * 100  # inflation-adjusted gasoline price
    mr = pd.concat([real, um], axis=1, sort=True).dropna()
    mr = mr[mr.index.year < 2020]
    gas_unemp_real, gas_unemp_real_best = lag_corr(mr.iloc[:, 0], mr.iloc[:, 1], 36)

    # 2. dDE -> real GDP growth, annual; 3. flywheel tau
    tests = {}
    for v in ("DE_original", "DE_per_capita", "DE_ex_transfers"):
        tests[v] = {}
        for label, end in (("1961-2007", 2007), ("1961-2019", 2019), ("1961-2025", 2025)):
            sub = a.loc[1961:end]
            d_de = sub[v].diff()
            rows, best = lag_corr(d_de, sub["real_gdp_growth_pct"], 5)
            fw_rows, fw_best = flywheel(d_de, sub["real_gdp_growth_pct"], range(1, 16))
            tests[v][label] = {"lag_corr": rows, "best_lag": best,
                               "flywheel": fw_rows, "best_tau": fw_best}

    def pick(v, label):
        return {k: tests[v][label][k] for k in ("best_lag", "best_tau")}

    results = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "definition": "DE(y) = gallons(y)/gallons(1986) - 1; gallons = income / retail gasoline price",
        "base_year": BASE_YEAR,
        "sources": {**{k: f"FRED {v}" for k, v in FRED.items()}, "gas_price": "EIA MER Table 9.4"},
        "gasoline_splice": {"rule": "leaded regular <=1975, unleaded regular >=1976", **splice},
        "DE_selected_years": {
            str(y): {v: round(float(a.loc[y, v]), 3)
                     for v in ("DE_original", "DE_per_capita", "DE_ex_transfers")}
            for y in (1960, 1973, 1979, 1980, 1986, 1998, 2005, 2008, 2012, 2016, 2019, 2020, 2022, 2025)
            if y in a.index and pd.notna(a.loc[y, "DE_per_capita"])},
        "test_gas_price_leads_unemployment_monthly_1977_2019": {
            "x": "gasoline price, % change over 12 months", "y": "unemployment rate, change over 12 months",
            "best": gas_unemp_best, "by_lag_months": gas_unemp,
            "lags_with_r_at_least_0.30": [d["lag"] for d in gas_unemp if d["r"] >= 0.30],
            "real_price_variant": {"x": "gasoline price / CPI, % change over 12 months",
                                   "best": gas_unemp_real_best, "by_lag_months": gas_unemp_real}},
        "test_DE_change_leads_real_gdp_growth": {v: {lab: pick(v, lab) for lab in tests[v]} for v in tests},
        "detail": tests,
        "caveats": [
            "Correlation is not causation; trending series are differenced before correlating.",
            "Gasoline is one energy carrier; total energy (electricity, heating, diesel) is not included.",
            "ex_transfers removes Social Security and pensions along with stimulus; it is not 'earned income'.",
            "Annual data give ~60 points per test; significance is modest. Monthly/regional data would help.",
            "Federal debt vs oil imports after 2005 is NOT tested here; see README open questions.",
        ],
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2))

    # Charts
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for v, c, lw in (("DE_original", "#a8a29e", 1.5), ("DE_per_capita", "#9b1c1c", 2.2),
                     ("DE_ex_transfers", "#15803d", 2.2)):
        ax.plot(a.index, a[v], color=c, lw=lw, label=v.replace("DE_", "").replace("_", " "))
    ax.axhline(0, color="#57534e", lw=0.8)
    for y, lab in EVENTS.items():
        ax.axvline(y, color="#d6d3d1", lw=0.8, zorder=0)
        ax.text(y, ax.get_ylim()[1], lab, rotation=90, va="top", ha="right", fontsize=8, color="#57534e")
    ax.set_title("Disposable Energy: gallons of gasoline take-home pay buys, 1986 = 0")
    ax.set_ylabel("change from 1986")
    ax.legend(frameon=False, loc="lower right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "disposable_energy.png", dpi=150)

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax1.plot(a.index, a["federal_debt_tn"], color="#1e293b", lw=2.2, label="Federal debt ($T)")
    ax1.plot(a.index, a["fed_assets_tn"], color="#b45309", lw=2.2, label="Federal Reserve assets ($T)")
    ax1.set_ylabel("$ trillions")
    for y in PRINTING_BREAKS:
        ax1.axvspan(y, y + 1, color="#fde68a", alpha=0.6, zorder=0)
    ax2 = ax1.twinx()
    ax2.plot(a.index, a["DE_per_capita"], color="#9b1c1c", lw=1.6, ls="--", label="DE per capita (right)")
    ax2.set_ylabel("Disposable Energy, 1986 = 0")
    h = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    ax1.legend(h, [x.get_label() for x in h], frameon=False, loc="upper left")
    ax1.set_title("Money and energy: debt and Fed balance sheet vs Disposable Energy (2008 and 2020 shaded)")
    fig.tight_layout()
    fig.savefig(OUT / "money_vs_energy.png", dpi=150)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    lags = [d["lag"] for d in gas_unemp]
    ax.bar(lags, [d["r"] for d in gas_unemp], color="#475569")
    ax.bar([gas_unemp_best["lag"]], [gas_unemp_best["r"]], color="#9b1c1c")
    ax.set_xlabel("months gasoline price change leads unemployment change")
    ax.set_ylabel("correlation r")
    ax.set_title(f"Gasoline price -> unemployment, 1977-2019: strongest at {gas_unemp_best['lag']} months "
                 f"(r = {gas_unemp_best['r']})")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "gas_unemployment_lag.png", dpi=150)

    print(f"[DE] gas->unemployment best lag {gas_unemp_best}; real price {gas_unemp_real_best}")
    for v in tests:
        print(f"[DE] {v}: " + json.dumps({lab: pick(v, lab) for lab in tests[v]}))
    print(f"[DE] wrote {OUT}")


if __name__ == "__main__":
    main()
