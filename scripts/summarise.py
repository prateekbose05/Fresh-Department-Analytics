"""
Roll the daily facts up to a weekly summary and print every headline figure
quoted in the README and on LinkedIn.

Two jobs, on purpose. The weekly file is a fallback for a cut-down Power BI
licence that cannot add measures to a model, and running it is how the numbers
in the write-up get checked instead of remembered.

Note the ratios in the weekly file are computed per week and cannot be averaged
to get a period figure. Sum the dollars and divide. The Power BI measures do
this correctly; the flat file is a convenience, not a model.

Usage: python3 scripts/summarise.py
"""

from __future__ import annotations

import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CHANGE_DATE = "2025-09-01"
CHANGED = ["Fruit & Veg", "Bakery"]


def load() -> dict[str, pd.DataFrame]:
    f = lambda n: pd.read_csv(os.path.join(DATA, n))
    d = f("dim_date.csv"); d["Date"] = pd.to_datetime(d["Date"])
    pg = f("dim_product_group.csv")
    s = f("fact_sales.csv"); s["Date"] = pd.to_datetime(s["Date"])
    w = f("fact_waste.csv"); w["Date"] = pd.to_datetime(w["Date"])
    l = f("fact_labour.csv"); l["Date"] = pd.to_datetime(l["Date"])
    b = f("fact_budget.csv"); b["Date"] = pd.to_datetime(b["Date"])
    return {"date": d, "pg": pg, "sales": s.merge(pg, on="ProductGroupKey"),
            "waste": w.merge(pg, on="ProductGroupKey"), "labour": l, "budget": b}


def weekly(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    wk = t["date"][["Date", "WeekIndex", "WeekEndDate", "WeekLabel", "FinancialYear", "MonthYear"]]
    g = lambda df, cols: df.merge(wk[["Date", "WeekIndex"]], on="Date").groupby("WeekIndex")[cols].sum()

    out = wk.groupby("WeekIndex").agg(
        WeekEnding=("WeekEndDate", "max"), WeekLabel=("WeekLabel", "max"),
        FinancialYear=("FinancialYear", "max"), MonthYear=("MonthYear", "max")).reset_index()

    out = out.join(g(t["sales"], ["NetSales", "CostOfSales", "MarkdownValue", "UnitsSold"]), on="WeekIndex")
    out = out.join(g(t["waste"], ["WasteCost"]), on="WeekIndex")
    out = out.join(g(t["labour"], ["RosteredHours", "ActualHours", "RosteredCost", "ActualCost"]), on="WeekIndex")
    out = out.join(g(t["budget"], ["SalesBudget", "WageBudget", "WasteBudget"]), on="WeekIndex")

    out["GrossProfit"] = out.NetSales - out.CostOfSales
    out["GrossMarginPct"] = out.GrossProfit / out.NetSales
    out["TradingMargin"] = out.GrossProfit - out.WasteCost - out.MarkdownValue
    out["TradingMarginPct"] = out.TradingMargin / out.NetSales
    out["WastePctOfSales"] = out.WasteCost / out.NetSales
    out["MarkdownPctOfSales"] = out.MarkdownValue / out.NetSales
    out["LabourPctOfSales"] = out.ActualCost / out.NetSales
    out["SalesPerLabourHour"] = out.NetSales / out.ActualHours
    out["PayrollVariance"] = out.ActualCost - out.RosteredCost
    out["WageVsBudget"] = out.ActualCost - out.WageBudget
    out["SalesVsBudgetPct"] = out.NetSales / out.SalesBudget - 1
    out["ChangePeriod"] = ["After change" if pd.Timestamp(x) >= pd.Timestamp(CHANGE_DATE)
                           else "Before change" for x in out.WeekEnding]
    return out.round(4)


def split(t: dict[str, pd.DataFrame], subdepts: list[str], after: bool) -> tuple[float, ...]:
    m = (lambda df: df.Date >= CHANGE_DATE) if after else (lambda df: df.Date < CHANGE_DATE)
    s = t["sales"][m(t["sales"]) & t["sales"].SubDepartment.isin(subdepts)]
    w = t["waste"][m(t["waste"]) & t["waste"].SubDepartment.isin(subdepts)]
    ns = s.NetSales.sum()
    return (ns, w.WasteCost.sum() / ns, s.MarkdownValue.sum() / ns,
            (ns - s.CostOfSales.sum() - w.WasteCost.sum() - s.MarkdownValue.sum()) / ns)


def main() -> None:
    t = load()
    wk = weekly(t)
    path = os.path.join(DATA, "agg_weekly.csv")
    wk.to_csv(path, index=False)

    s, w, l, b = t["sales"], t["waste"], t["labour"], t["budget"]
    ns = s.NetSales.sum()
    pct = lambda x: f"{x * 100:.2f}%"

    print(f"\nFRESH DEPARTMENT, 104 weeks to {wk.WeekEnding.max()}\n" + "-" * 58)
    print(f"Net sales                 ${ns:>12,.0f}   ${ns / 104:>9,.0f} / week")
    print(f"Gross margin              {pct(1 - s.CostOfSales.sum() / ns):>13}")
    print(f"Waste                     ${w.WasteCost.sum():>12,.0f}   {pct(w.WasteCost.sum() / ns):>9} of sales")
    print(f"Markdown                  ${s.MarkdownValue.sum():>12,.0f}   {pct(s.MarkdownValue.sum() / ns):>9} of sales")
    print(f"Trading margin            {pct((ns - s.CostOfSales.sum() - w.WasteCost.sum() - s.MarkdownValue.sum()) / ns):>13}")
    print(f"Labour cost               ${l.ActualCost.sum():>12,.0f}   {pct(l.ActualCost.sum() / ns):>9} of sales")
    print(f"Actual vs rostered        ${l.ActualCost.sum() - l.RosteredCost.sum():>12,.0f}   {pct(l.ActualCost.sum() / l.RosteredCost.sum() - 1):>9}")
    print(f"Actual vs wage budget     ${l.ActualCost.sum() - b.WageBudget.sum():>12,.0f}   {pct(l.ActualCost.sum() / b.WageBudget.sum() - 1):>9}")
    print(f"Sales vs budget           {pct(ns / b.SalesBudget.sum() - 1):>13}")

    print(f"\nLABOUR STICKINESS\n" + "-" * 58)
    lo, hi = wk.LabourPctOfSales.min(), wk.LabourPctOfSales.max()
    print(f"Weekly labour % of sales ranges {pct(lo)} to {pct(hi)}")
    worst = wk.nlargest(3, "LabourPctOfSales")
    for _, r in worst.iterrows():
        print(f"  {r.WeekLabel:<20} {pct(r.LabourPctOfSales):>7}  sales ${r.NetSales:>8,.0f}  vs budget {pct(r.SalesVsBudgetPct):>8}")

    print(f"\nORDERING CHANGE, {CHANGE_DATE} onward\n" + "-" * 58)
    print(f"{'':<34}{'waste':>9}{'markdown':>11}{'margin':>17}")
    rows = {}
    for label, groups in [("Fruit & Veg + Bakery", CHANGED),
                          ("Control sub-depts", ["Deli", "Meat & Seafood", "Dairy & Chilled"])]:
        for period, after in [("before", False), ("after", True)]:
            sales, wp, mp, tm = split(t, groups, after)
            rows[(label, period)] = (sales, wp, mp, tm)
            print(f"  {label + ', ' + period:<32}{pct(wp):>9}{pct(mp):>11}{pct(tm):>17}")
    for label in ("Fruit & Veg + Bakery", "Control sub-depts"):
        bef, aft = rows[(label, "before")], rows[(label, "after")]
        d = lambda i: (aft[i] - bef[i]) * 100
        print(f"  {'DELTA ' + label:<32}{d(1):>+8.2f}pt{d(2):>+10.2f}pt{d(3):>+16.2f}pt")
    bef, aft = rows[("Fruit & Veg + Bakery", "before")], rows[("Fruit & Veg + Bakery", "after")]
    print(f"\n  Value of the change: ${(aft[3] - bef[3]) * aft[0]:,.0f} of trading margin "
          f"on ${aft[0]:,.0f} of sales in the 52 weeks after.")

    print(f"\nWASTE BY REASON CATEGORY\n" + "-" * 58)
    meta = pd.read_csv(os.path.join(DATA, "dim_waste_reason.csv"))
    by = w.merge(meta, on="WasteReason").groupby("ReasonCategory").WasteCost.sum().sort_values(ascending=False)
    for k, v in by.items():
        print(f"  {k:<24} ${v:>10,.0f}   {pct(v / w.WasteCost.sum()):>7} of waste")

    print(f"\nWrote {os.path.relpath(path, ROOT)}  ({len(wk)} weeks)\n")


if __name__ == "__main__":
    main()
