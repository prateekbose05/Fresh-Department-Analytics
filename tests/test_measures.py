"""The dashboard's measures must reproduce every figure in the README and FINDINGS.

Those figures are printed by scripts/summarise.py from the raw facts. These
tests pin the dashboard to the same numbers by a separate route.
"""

import pandas as pd
import pytest

from dashboard import measures as m
from dashboard.model import CHANGED, apply_filters, load


@pytest.fixture(scope="module")
def model():
    return load()


@pytest.fixture(scope="module")
def week(model):
    return m.weekly(model)


def pct(x: float) -> float:
    return round(x * 100, 2)


def test_row_counts(model):
    assert len(model.sales) == 10192 and len(model.waste) == 39288
    assert len(model.labour) == 2912 and len(model.budget) == 3640
    assert model.date.WeekIndex.nunique() == 104


def test_department_headline(model):
    h = m.headline(model)
    assert round(h["Net Sales"]) == 8_022_126
    assert pct(h["Gross Margin %"]) == 33.29
    assert round(h["Waste Cost"]) == 184_178 and pct(h["Waste % of Sales"]) == 2.30
    assert round(h["Markdown Value"]) == 153_487 and pct(h["Markdown % of Sales"]) == 1.91
    assert pct(h["Trading Margin %"]) == 29.08
    assert round(h["Actual Labour Cost"]) == 919_750 and pct(h["Labour % of Sales"]) == 11.47
    assert round(h["Payroll Variance"]) == 3_831 and pct(h["Payroll Variance %"]) == 0.42
    assert round(h["Wage vs Budget"]) == -17_355 and pct(h["Wage vs Budget %"]) == -1.85
    assert pct(h["Sales vs Budget %"]) == -0.27


def test_weekly_budget_and_labour_ranges(week):
    assert len(week) == 104
    assert pct(week.SalesVsBudgetPct.min()) == -10.25
    assert pct(week.SalesVsBudgetPct.max()) == 22.37
    assert pct(week.LabourPct.min()) == 9.61 and pct(week.LabourPct.max()) == 12.65
    worst = m.worst_labour_weeks(week, 3)
    assert list(worst.WeekLabel) == ["W/E 11 Jan 2026", "W/E 18 Jan 2026", "W/E 27 Apr 2025"]
    assert (worst.SalesVsBudgetPct < -0.06).all()


def test_waste_by_sub_department(model):
    by = m.by_sub_department(model).set_index("SubDepartment")["Waste % of Sales"].map(pct)
    assert by.to_dict() == {"Bakery": 2.56, "Dairy & Chilled": 0.76, "Deli": 2.52,
                            "Fruit & Veg": 3.11, "Meat & Seafood": 2.59}


def test_waste_by_reason(model):
    by = m.waste_by_reason(model).set_index("ReasonCategory")
    assert by.index[0] == "Ordering & rotation"
    assert round(by.WasteCost["Ordering & rotation"]) == 100_973
    assert round(by.Share["Ordering & rotation"] * 100, 1) == 54.8


def test_ordering_change(model):
    changed = m.change_comparison(model, CHANGED)
    assert pct(changed["Waste % of Sales Before"]) == 3.62
    assert pct(changed["Waste % of Sales After"]) == 2.22
    assert pct(changed["Waste % of Sales Change"]) == -1.40
    assert pct(changed["Markdown % of Sales Change"]) == 0.60
    assert pct(changed["Trading Margin % Change"]) == 0.82
    assert round(changed["Value of Change"]) == 12_712
    assert round(changed["Net Sales After"]) == 1_553_871

    control = m.change_comparison(model, ["Deli", "Meat & Seafood", "Dairy & Chilled"])
    assert abs(control["Waste % of Sales Change"]) < 0.0002
    assert abs(control["Trading Margin % Change"]) < 0.0002


def test_rolling_ratio_is_ratio_of_sums(week):
    last = week.tail(4)
    expected = last.WasteCost.sum() / last.NetSales.sum()
    assert week.WastePct4wk.iloc[-1] == pytest.approx(expected)
    assert week.WastePct4wk.iloc[-1] != pytest.approx(last.WastePct.mean(), abs=1e-9)
    assert week.WastePct4wk.iloc[:3].isna().all()


def test_sub_department_filter_leaves_labour_alone(model):
    one = apply_filters(model, sub_departments=["Bakery"])
    assert set(one.sales.SubDepartment) == {"Bakery"}
    assert set(one.budget.SubDepartment) == {"Bakery"}
    assert len(one.labour) == len(model.labour)
    dept_sales = float(model.sales.NetSales.sum())
    h = m.headline(one, department_sales=dept_sales)
    assert pct(h["Labour % of Sales"]) == 11.47
    assert h["Net Sales"] < dept_sales


def test_date_filter(model):
    fy26 = apply_filters(model, "2025-07-01", "2026-06-30")
    assert fy26.sales.Date.min() >= pd.Timestamp("2025-07-01")
    assert fy26.labour.Date.max() <= pd.Timestamp("2026-06-30")
    assert 0 < m.headline(fy26)["Net Sales"] < m.headline(model)["Net Sales"]


def test_weeks_over_scenario_is_monotonic(week):
    counts = [m.weeks_over_scenario(week, p) for p in (0.10, 0.11, 0.1165, 0.12, 0.13)]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1] == 0
