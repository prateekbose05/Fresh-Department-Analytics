"""The measure library.

Every ratio is a ratio of sums over whatever rows are in scope, never an
average of weekly or daily percentages. Averaging ratios weights a quiet
January week the same as Christmas week and quietly moves the answer.
"""

from __future__ import annotations

import pandas as pd

from .model import CHANGED, DAY_ORDER, Model


def _div(a, b):
    """Safe division: NaN where the denominator is zero."""
    if isinstance(b, pd.Series):
        return a / b.where(b != 0)
    return a / b if b else float("nan")


# ---------------------------------------------------------------- headline

def trading(sales: pd.DataFrame, waste: pd.DataFrame) -> dict[str, float]:
    """Sales, margin, waste and markdown for the rows in scope."""
    net = float(sales.NetSales.sum())
    gross = net - float(sales.CostOfSales.sum())
    waste_cost = float(waste.WasteCost.sum())
    markdown = float(sales.MarkdownValue.sum())
    return {
        "Net Sales": net,
        "Gross Margin %": _div(gross, net),
        "Waste Cost": waste_cost,
        "Waste % of Sales": _div(waste_cost, net),
        "Markdown Value": markdown,
        "Markdown % of Sales": _div(markdown, net),
        "Trading Margin": gross - waste_cost - markdown,
        "Trading Margin %": _div(gross - waste_cost - markdown, net),
    }


def headline(model: Model, department_sales: float | None = None) -> dict[str, float]:
    """Every card on the dashboard.

    Labour has no sub-department, so labour ratios divide by department sales.
    Pass `department_sales` when `model` has a sub-department filter applied.
    """
    out = trading(model.sales, model.waste)
    dept_sales = out["Net Sales"] if department_sales is None else department_sales
    labour, budget = model.labour, model.budget
    actual, rostered = float(labour.ActualCost.sum()), float(labour.RosteredCost.sum())
    out.update({
        "Sales Budget": float(budget.SalesBudget.sum()),
        "Sales vs Budget %": _div(out["Net Sales"], float(budget.SalesBudget.sum())) - 1,
        "Waste vs Budget": out["Waste Cost"] - float(budget.WasteBudget.sum()),
        "Actual Labour Cost": actual,
        "Labour % of Sales": _div(actual, dept_sales),
        "Payroll Variance": actual - rostered,
        "Payroll Variance %": _div(actual, rostered) - 1,
        "Wage vs Budget": actual - float(budget.WageBudget.sum()),
        "Wage vs Budget %": _div(actual, float(budget.WageBudget.sum())) - 1,
        "Sales per Labour Hour": _div(dept_sales, float(labour.ActualHours.sum())),
    })
    return out


# ------------------------------------------------------------------ weekly

def weekly(model: Model, department_sales: pd.Series | None = None) -> pd.DataFrame:
    """One row per week with the dollars summed and the ratios recomputed.

    The four-week columns are ratios of two rolling sums.
    """
    keys = ["WeekIndex", "WeekEndDate", "WeekLabel"]
    out = model.sales.groupby(keys)[["NetSales", "CostOfSales", "MarkdownValue"]].sum()
    out = out.join(model.waste.groupby(keys).WasteCost.sum())
    out = out.join(model.budget.groupby(keys)[["SalesBudget", "WageBudget"]].sum())
    out = out.join(model.labour.groupby(keys)[["ActualCost", "RosteredCost", "ActualHours"]].sum())
    out = out.fillna(0.0).reset_index().sort_values("WeekIndex")

    dept = out.NetSales if department_sales is None else \
        out.WeekIndex.map(department_sales).fillna(0.0)
    out["DepartmentSales"] = dept
    gross = out.NetSales - out.CostOfSales
    out["GrossMarginPct"] = _div(gross, out.NetSales)
    out["TradingMarginPct"] = _div(gross - out.WasteCost - out.MarkdownValue, out.NetSales)
    out["WastePct"] = _div(out.WasteCost, out.NetSales)
    out["SalesVsBudgetPct"] = _div(out.NetSales, out.SalesBudget) - 1
    out["LabourPct"] = _div(out.ActualCost, dept)
    out["PayrollVariance"] = out.ActualCost - out.RosteredCost

    roll = lambda s: s.rolling(4, min_periods=4).sum()
    out["WastePct4wk"] = _div(roll(out.WasteCost), roll(out.NetSales))
    out["LabourPct4wk"] = _div(roll(out.ActualCost), roll(dept))
    return out


def department_sales_by_week(model: Model) -> pd.Series:
    """Weekly department sales, for labour ratios when a sub-department filter is on."""
    return model.sales.groupby("WeekIndex").NetSales.sum()


def weekly_waste_by_sub_department(model: Model) -> pd.DataFrame:
    """Four-week rolling waste % of sales, one line per sub-department."""
    keys = ["SubDepartment", "WeekIndex", "WeekEndDate"]
    df = (model.sales.groupby(keys).NetSales.sum().to_frame()
          .join(model.waste.groupby(keys).WasteCost.sum()).fillna(0.0).reset_index()
          .sort_values(["SubDepartment", "WeekIndex"]))
    grouped = df.groupby("SubDepartment")
    waste4 = grouped.WasteCost.transform(lambda s: s.rolling(4, min_periods=4).sum())
    sales4 = grouped.NetSales.transform(lambda s: s.rolling(4, min_periods=4).sum())
    df["WastePct4wk"] = _div(waste4, sales4)
    return df.dropna(subset=["WastePct4wk"])


# ------------------------------------------------------------- breakdowns

def by_sub_department(model: Model) -> pd.DataFrame:
    """The trading measures for each sub-department."""
    rows = []
    for sub in model.sub_departments:
        s = model.sales[model.sales.SubDepartment == sub]
        if s.empty:
            continue
        rows.append({"SubDepartment": sub,
                     **trading(s, model.waste[model.waste.SubDepartment == sub])})
    return pd.DataFrame(rows)


def waste_by_reason(model: Model) -> pd.DataFrame:
    out = (model.waste.groupby("ReasonCategory").WasteCost.sum()
           .sort_values(ascending=False).reset_index())
    out["Share"] = _div(out.WasteCost, float(out.WasteCost.sum()))
    return out


def waste_by_product_group(model: Model) -> pd.DataFrame:
    """Waste % against shelf life: the scatter that explains the ranking."""
    keys = ["ProductGroup", "SubDepartment", "ShelfLifeDays"]
    out = (model.sales.groupby(keys).NetSales.sum().to_frame()
           .join(model.waste.groupby(keys).WasteCost.sum()).fillna(0.0).reset_index())
    out["WastePct"] = _div(out.WasteCost, out.NetSales)
    return out


def waste_by_day(model: Model) -> pd.DataFrame:
    """Waste % of sales by sub-department and day of week."""
    keys = ["SubDepartment", "DayName"]
    out = (model.sales.groupby(keys).NetSales.sum().to_frame()
           .join(model.waste.groupby(keys).WasteCost.sum()).fillna(0.0).reset_index())
    out["WastePct"] = _div(out.WasteCost, out.NetSales)
    return out


def hours_by_day(model: Model) -> pd.DataFrame:
    out = model.labour.groupby("DayName")[["RosteredHours", "ActualHours"]].sum()
    return out.reindex(DAY_ORDER).dropna(how="all").reset_index()


def worst_labour_weeks(week: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    cols = ["WeekLabel", "DepartmentSales", "SalesVsBudgetPct", "ActualCost", "LabourPct",
            "PayrollVariance"]
    return week.nlargest(n, "LabourPct")[cols]


def weeks_over_scenario(week: pd.DataFrame, wage_budget_pct: float) -> int:
    """How many weeks labour cost would have exceeded a wage budget set as a % of sales."""
    return int((week.ActualCost > week.DepartmentSales * wage_budget_pct).sum())


# ------------------------------------------------------ the ordering change

def change_comparison(model: Model, sub_departments: list[str]) -> dict[str, float]:
    """Before and after 1 September 2025 for a group of sub-departments.

    Uses the whole date range the model holds, like a measure that removes the
    date filter: the comparison should not move when a slicer does.
    """
    out = {}
    for period in ("Before change", "After change"):
        s = model.sales[(model.sales.ChangePeriod == period)
                        & model.sales.SubDepartment.isin(sub_departments)]
        w = model.waste[(model.waste.ChangePeriod == period)
                        & model.waste.SubDepartment.isin(sub_departments)]
        t = trading(s, w)
        key = "Before" if period.startswith("Before") else "After"
        out[f"Net Sales {key}"] = t["Net Sales"]
        for name in ("Waste % of Sales", "Markdown % of Sales", "Trading Margin %"):
            out[f"{name} {key}"] = t[name]
    for name in ("Waste % of Sales", "Markdown % of Sales", "Trading Margin %"):
        out[f"{name} Change"] = out[f"{name} After"] - out[f"{name} Before"]
    out["Value of Change"] = out["Trading Margin % Change"] * out["Net Sales After"]
    return out


def change_table(model: Model) -> pd.DataFrame:
    """One row per sub-department, changed ones first, plus the two group rows."""
    control = [s for s in model.sub_departments if s not in CHANGED]
    rows = [{"Group": "Changed", "SubDepartment": s, **change_comparison(model, [s])}
            for s in CHANGED]
    rows += [{"Group": "Control", "SubDepartment": s, **change_comparison(model, [s])}
             for s in control]
    rows.append({"Group": "Changed", "SubDepartment": "Fruit & Veg + Bakery",
                 **change_comparison(model, CHANGED)})
    rows.append({"Group": "Control", "SubDepartment": "Control sub-departments",
                 **change_comparison(model, control)})
    return pd.DataFrame(rows)
