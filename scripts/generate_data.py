"""
Generate the synthetic dataset behind the Fresh Department Performance dashboard.

Everything here is invented. No Woolworths data, systems or records were used.
The store is a fictional metro supermarket sized to look like a real one so the
Power BI model has to solve real problems: a weekly wage budget that has to be
phased to days, waste that moves against markdown, and a labour line that does
not fall as fast as sales.

Deterministic: same seed, same numbers, every run.

Usage:  python3 scripts/generate_data.py
Output: data/*.csv
"""

from __future__ import annotations

import csv
import os
from datetime import date, timedelta

import numpy as np

SEED = 2026
RNG = np.random.default_rng(SEED)

START = date(2024, 9, 2)      # a Monday
END = date(2026, 8, 30)       # a Sunday, 104 complete weeks
INTERVENTION_START = date(2025, 9, 1)   # start of week 53

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Target scale for the fictional store, chosen once and held.
STORE_WEEKLY_SALES = 200_000.0
FRESH_SHARE = 0.37
DEPT_WEEKLY_SALES = STORE_WEEKLY_SALES * FRESH_SHARE   # ~74,000
ANNUAL_GROWTH = 0.035

# Share of the week's trade by day. Supermarket shape: quiet start, Friday peak.
DOW_PROFILE = {0: 0.125, 1: 0.120, 2: 0.130, 3: 0.145, 4: 0.175, 5: 0.175, 6: 0.130}


# ----------------------------------------------------------------------------
# Calendar
# ----------------------------------------------------------------------------

def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm. Computed, never hardcoded."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """nth occurrence of a weekday in a month. Monday = 0."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def victorian_holidays(year: int) -> dict[date, str]:
    """
    Victorian public holidays with fixed or computable dates.

    The Friday before the AFL Grand Final is a Victorian public holiday but its
    date is set each year and is not computable, so it is deliberately excluded
    rather than guessed. Substitute days for holidays falling on a weekend are
    applied to New Year's Day, Australia Day, Christmas Day and Boxing Day.
    """
    hol: dict[date, str] = {}
    easter = easter_sunday(year)

    fixed = [
        (date(year, 1, 1), "New Year's Day", True),
        (date(year, 1, 26), "Australia Day", True),
        (nth_weekday(year, 3, 0, 2), "Labour Day", False),
        (easter - timedelta(days=2), "Good Friday", False),
        (easter - timedelta(days=1), "Easter Saturday", False),
        (easter + timedelta(days=1), "Easter Monday", False),
        (date(year, 4, 25), "ANZAC Day", False),
        (nth_weekday(year, 6, 0, 2), "King's Birthday", False),
        (nth_weekday(year, 11, 1, 1), "Melbourne Cup Day", False),
        (date(year, 12, 25), "Christmas Day", True),
        (date(year, 12, 26), "Boxing Day", True),
    ]

    for d, name, substitute in fixed:
        hol[d] = name
        if substitute and d.weekday() >= 5:
            shift = 2 if d.weekday() == 5 else 1
            sub = d + timedelta(days=shift)
            while sub in hol:
                sub += timedelta(days=1)
            hol[sub] = f"{name} (substitute)"
    return hol


def build_calendar() -> tuple[list[date], dict[date, str]]:
    days = []
    d = START
    while d <= END:
        days.append(d)
        d += timedelta(days=1)
    hol: dict[date, str] = {}
    for y in range(START.year, END.year + 1):
        hol.update(victorian_holidays(y))
    hol = {d: n for d, n in hol.items() if START <= d <= END}
    return days, hol


# ----------------------------------------------------------------------------
# Dimensions
# ----------------------------------------------------------------------------

# key, sub_department, product_group, share of department sales,
# baseline GP%, shelf life in days, baseline waste rate on cost
PRODUCT_GROUPS = [
    ("PG01", "Fruit & Veg",     "Bananas & Tropical",   0.070, 0.315,  4, 0.052),
    ("PG02", "Fruit & Veg",     "Salads & Herbs",       0.062, 0.360,  3, 0.068),
    ("PG03", "Fruit & Veg",     "Root Vegetables",      0.058, 0.335, 12, 0.024),
    ("PG04", "Fruit & Veg",     "Berries & Stone Fruit",0.050, 0.300,  3, 0.075),
    ("PG05", "Bakery",          "Bread & Rolls",        0.088, 0.510,  2, 0.061),
    ("PG06", "Bakery",          "Pastries & Cakes",     0.052, 0.545,  2, 0.072),
    ("PG07", "Deli",            "Sliced Meats",         0.064, 0.385,  5, 0.031),
    ("PG08", "Deli",            "Cheese",               0.058, 0.365, 14, 0.017),
    ("PG09", "Deli",            "Hot Food & Salads",    0.046, 0.430,  1, 0.089),
    ("PG10", "Meat & Seafood",  "Beef & Lamb",          0.104, 0.268,  4, 0.028),
    ("PG11", "Meat & Seafood",  "Poultry",              0.086, 0.285,  3, 0.034),
    ("PG12", "Meat & Seafood",  "Seafood",              0.042, 0.310,  2, 0.055),
    ("PG13", "Dairy & Chilled", "Milk & Cream",         0.126, 0.212, 10, 0.009),
    ("PG14", "Dairy & Chilled", "Yoghurt & Desserts",   0.094, 0.246, 18, 0.011),
]

# key, role, base hourly rate (synthetic), share of department hours
ROLES = [
    ("R1", "Department Team Member", 27.80, 0.44),
    ("R2", "Casual Team Member",     33.10, 0.26),
    ("R3", "Early Fill & Nightfill", 29.40, 0.19),
    ("R4", "Duty Manager",           36.20, 0.11),
]

PENALTY = {5: 1.25, 6: 1.50}          # Saturday, Sunday
PUBLIC_HOLIDAY_PENALTY = 2.25

WASTE_REASONS = ["Date code expiry", "Quality reject", "Damage", "Prep & trim loss"]

# Grouping waste by what actually controls it, not by what the label says.
# Ordering and rotation is the only bucket a department manager fully owns,
# which is why it is the bucket the ordering change was aimed at.
WASTE_REASON_META = {
    "Date code expiry": ("Ordering & rotation", 1),
    "Quality reject":   ("Supplier & quality", 2),
    "Damage":           ("Handling", 3),
    "Prep & trim loss": ("Production", 4),
}
WASTE_REASON_MIX = {
    "Fruit & Veg":     [0.44, 0.34, 0.16, 0.06],
    "Bakery":          [0.72, 0.10, 0.08, 0.10],
    "Deli":            [0.48, 0.16, 0.06, 0.30],
    "Meat & Seafood":  [0.56, 0.18, 0.08, 0.18],
    "Dairy & Chilled": [0.79, 0.07, 0.14, 0.00],
}

# Sub-departments where the ordering and rotation change was applied.
INTERVENTION_SUBDEPTS = {"Fruit & Veg", "Bakery"}


# ----------------------------------------------------------------------------
# Demand model
# ----------------------------------------------------------------------------

def seasonal_index(d: date) -> float:
    """Annual shape, plus the December run-up and the January hole."""
    doy = d.timetuple().tm_yday
    base = 1.0 + 0.055 * np.sin(2 * np.pi * (doy - 330) / 365.25)
    if d.month == 12:
        base *= 1.0 + 0.024 * d.day          # builds through December
    if d.month == 1:
        base *= 0.795 + 0.006 * d.day        # recovers through January
    if d.month == 2:
        base *= 0.955
    return float(base)


def holiday_factor(d: date, hol: dict[date, str]) -> float:
    """Trade lifts the day before a holiday and falls on and after it."""
    if d in hol:
        name = hol[d]
        if "Christmas Day" in name:
            return 0.05
        if "Good Friday" in name:
            return 0.30
        return 0.62
    if (d + timedelta(days=1)) in hol:
        return 1.26
    if (d - timedelta(days=1)) in hol:
        return 0.90
    return 1.0


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    days, hol = build_calendar()
    n_weeks = len(days) // 7

    # ---------------- dim_date ----------------
    dim_date = []
    for d in days:
        week_start = d - timedelta(days=d.weekday())
        fy = d.year + 1 if d.month >= 7 else d.year      # Australian FY, July to June
        dim_date.append({
            "Date": d.isoformat(),
            "WeekStartDate": week_start.isoformat(),
            "WeekEndDate": (week_start + timedelta(days=6)).isoformat(),
            "WeekLabel": f"W/E {(week_start + timedelta(days=6)).strftime('%d %b %Y')}",
            "WeekIndex": (week_start - START).days // 7 + 1,
            "Year": d.year,
            "MonthNumber": d.month,
            "MonthName": d.strftime("%B"),
            "MonthYear": d.strftime("%b %Y"),
            "MonthYearSort": d.year * 100 + d.month,
            "Quarter": f"Q{(d.month - 1) // 3 + 1}",
            "FinancialYear": f"FY{str(fy)[2:]}",
            "DayName": d.strftime("%A"),
            "DayOfWeekNumber": d.weekday() + 1,
            "IsWeekend": "TRUE" if d.weekday() >= 5 else "FALSE",
            "IsPublicHoliday": "TRUE" if d in hol else "FALSE",
            "HolidayName": hol.get(d, ""),
        })

    # ---------------- dim_product_group ----------------
    dim_pg = [{
        "ProductGroupKey": k,
        "SubDepartment": sub,
        "ProductGroup": pg,
        "ShelfLifeDays": shelf,
        "TargetGrossMarginPct": round(gp, 4),
        "PerishabilityBand": "High" if shelf <= 3 else ("Medium" if shelf <= 7 else "Low"),
    } for k, sub, pg, _share, gp, shelf, _w in PRODUCT_GROUPS]

    # Sub-department is its own dimension because the budget is set at that
    # level and nowhere finer. Joining budget straight to the product-group
    # table would have made a non-unique key and a fan-out.
    dim_subdept = [{
        "SubDepartment": sub,
        "SubDepartmentSort": i + 1,
        "Category": "Perishable" if sub in ("Fruit & Veg", "Bakery", "Deli") else "Chilled",
    } for i, sub in enumerate(sorted({p[1] for p in PRODUCT_GROUPS}))]

    dim_waste_reason = [{
        "WasteReason": r,
        "ReasonCategory": WASTE_REASON_META[r][0],
        "ReasonSort": WASTE_REASON_META[r][1],
    } for r in WASTE_REASONS]

    dim_role = [{
        "RoleKey": k, "Role": r, "BaseHourlyRate": rate,
        "RoleType": "Salaried support" if k == "R4" else "Rostered floor",
    } for k, r, rate, _s in ROLES]

    # ---------------- facts ----------------
    fact_sales, fact_waste, fact_labour, fact_budget = [], [], [], []

    # Weekly budget is set once a year at a flat uplift on the prior year and
    # then phased to days on the trading profile. Deliberately a little wrong,
    # which is what makes the variance page worth looking at.
    for wk in range(n_weeks):
        week_start = START + timedelta(weeks=wk)
        wk_days = [week_start + timedelta(days=i) for i in range(7)]
        wk_seasonal = float(np.mean([seasonal_index(x) for x in wk_days]))
        trend = (1 + ANNUAL_GROWTH) ** ((week_start - START).days / 365.25)
        # budget is smoothed: it ignores holiday timing entirely
        week_sales_budget = DEPT_WEEKLY_SALES * trend * (0.5 * wk_seasonal + 0.5)
        week_wage_budget = week_sales_budget * 0.1165
        week_waste_budget = week_sales_budget * 0.0300
        week_gp_budget = week_sales_budget * 0.3190

        for d in wk_days:
            share = DOW_PROFILE[d.weekday()]
            for sub in sorted({p[1] for p in PRODUCT_GROUPS}):
                sub_share = sum(p[3] for p in PRODUCT_GROUPS if p[1] == sub)
                fact_budget.append({
                    "Date": d.isoformat(),
                    "SubDepartment": sub,
                    "SalesBudget": round(week_sales_budget * share * sub_share, 2),
                    "WageBudget": round(week_wage_budget * share * sub_share, 2),
                    "WasteBudget": round(week_waste_budget * share * sub_share, 2),
                    "GrossProfitBudget": round(week_gp_budget * share * sub_share, 2),
                })

    for d in days:
        trend = (1 + ANNUAL_GROWTH) ** ((d - START).days / 365.25)
        day_factor = (DOW_PROFILE[d.weekday()] * 7) * seasonal_index(d) * holiday_factor(d, hol)
        day_sales_target = DEPT_WEEKLY_SALES / 7 * trend * day_factor
        day_noise = float(RNG.normal(1.0, 0.038))
        day_sales_target *= max(day_noise, 0.75)

        post_intervention = d >= INTERVENTION_START
        after_holiday = (d - timedelta(days=1)) in hol or (d - timedelta(days=2)) in hol

        day_sales_actual = 0.0

        for key, sub, pg, share, base_gp, shelf, base_waste in PRODUCT_GROUPS:
            group_sales = day_sales_target * share / sum(p[3] for p in PRODUCT_GROUPS)
            group_sales *= float(RNG.normal(1.0, 0.075))
            group_sales = max(group_sales, 0.0)
            day_sales_actual += group_sales

            gp_pct = base_gp + float(RNG.normal(0, 0.010))

            # Markdown: higher on short shelf life, on Sundays, and after the
            # intervention in the two sub-departments where markdowns were
            # pulled earlier in the day.
            md_rate = 0.014 + 0.011 * (1 / shelf) + (0.006 if d.weekday() == 6 else 0.0)
            if post_intervention and sub in INTERVENTION_SUBDEPTS:
                md_rate += 0.0060
            md_rate += float(RNG.normal(0, 0.0025))
            md_rate = max(md_rate, 0.0)
            markdown = group_sales * md_rate

            # Waste on cost. Short shelf life, holiday over-ordering and summer
            # heat all push it up; the intervention pulls it down.
            w = base_waste
            if after_holiday and shelf <= 4:
                w *= 1.55
            if d.month in (12, 1, 2) and sub == "Fruit & Veg":
                w *= 1.14
            if post_intervention and sub in INTERVENTION_SUBDEPTS:
                w *= 0.61
            w *= float(RNG.normal(1.0, 0.18))
            w = max(w, 0.0)

            cost_of_sales = group_sales * (1 - gp_pct)
            waste_cost = cost_of_sales * w
            units = max(int(group_sales / float(RNG.normal(6.4, 0.9))), 1)

            fact_sales.append({
                "Date": d.isoformat(),
                "ProductGroupKey": key,
                "NetSales": round(group_sales, 2),
                "CostOfSales": round(cost_of_sales, 2),
                "MarkdownValue": round(markdown, 2),
                "UnitsSold": units,
            })

            if waste_cost > 0.005:
                mix = WASTE_REASON_MIX[sub]
                draw = RNG.dirichlet(np.array(mix) * 22 + 1e-6)
                for reason, frac in zip(WASTE_REASONS, draw):
                    amount = waste_cost * float(frac)
                    if amount < 0.01:
                        continue
                    fact_waste.append({
                        "Date": d.isoformat(),
                        "ProductGroupKey": key,
                        "WasteReason": reason,
                        "WasteCost": round(amount, 2),
                        "WasteUnits": max(int(amount / float(RNG.normal(4.6, 0.7))), 1),
                    })

        # ---------------- labour ----------------
        # The roster is written a week ahead off a forecast that leans on the
        # trend rather than the week in front of it, so it is slow to come down
        # when trade falls away. That is the sticky-labour problem the dashboard
        # exists to show.
    
        baseline_day_sales = DEPT_WEEKLY_SALES / 7 * trend * (DOW_PROFILE[d.weekday()] * 7)
        roster_forecast = 0.48 * day_sales_actual + 0.52 * baseline_day_sales
        rostered_cost_total = roster_forecast * 0.1145 * float(RNG.normal(1.0, 0.022))

        for rkey, role, rate, hshare in ROLES:
            penalty = PUBLIC_HOLIDAY_PENALTY if d in hol else PENALTY.get(d.weekday(), 1.0)
            eff_rate = rate * penalty
            rostered_cost = rostered_cost_total * hshare
            rostered_hours = rostered_cost / eff_rate

            # Actual against roster: overruns on trade peaks, small underruns when quiet.
            drift = float(RNG.normal(0.012 if day_factor > 1.05 else -0.004, 0.030))
            if d in hol:
                drift += 0.05
            actual_hours = max(rostered_hours * (1 + drift), 0.0)

            fact_labour.append({
                "Date": d.isoformat(),
                "RoleKey": rkey,
                "RosteredHours": round(rostered_hours, 2),
                "ActualHours": round(actual_hours, 2),
                "EffectiveHourlyRate": round(eff_rate, 2),
                "RosteredCost": round(rostered_hours * eff_rate, 2),
                "ActualCost": round(actual_hours * eff_rate, 2),
            })

    # ---------------- write ----------------
    def write(name: str, rows: list[dict]) -> None:
        path = os.path.join(OUT, name)
        with open(path, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)
        print(f"  {name:<26} {len(rows):>7,} rows")

    print(f"Fresh Department Analytics, synthetic data, seed {SEED}")
    print(f"  {START} to {END}  ({n_weeks} weeks)\n")
    write("dim_date.csv", dim_date)
    write("dim_sub_department.csv", dim_subdept)
    write("dim_product_group.csv", dim_pg)
    write("dim_waste_reason.csv", dim_waste_reason)
    write("dim_role.csv", dim_role)
    write("fact_sales.csv", fact_sales)
    write("fact_waste.csv", fact_waste)
    write("fact_labour.csv", fact_labour)
    write("fact_budget.csv", fact_budget)
    tables = {
        "dim_date": dim_date, "dim_sub_department": dim_subdept,
        "dim_product_group": dim_pg, "dim_waste_reason": dim_waste_reason,
        "dim_role": dim_role, "fact_sales": fact_sales, "fact_waste": fact_waste,
        "fact_labour": fact_labour, "fact_budget": fact_budget,
    }
    write_workbook(tables)
    print("\nDone.")


def write_workbook(tables: dict[str, list[dict]]) -> None:
    """One .xlsx, one named Excel Table per sheet.

    Power BI Service in a browser imports an Excel workbook and turns each named
    table into a table in the semantic model. Loose CSVs cannot be uploaded the
    same way, so this workbook is the file that gets uploaded.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.worksheet.table import Table, TableStyleInfo
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("\n  openpyxl not installed, skipping the workbook (CSVs are complete).")
        return

    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in tables.items():
        ws = wb.create_sheet(name[:31])
        cols = list(rows[0].keys())
        ws.append(cols)
        for r in rows:
            ws.append([r[c] for c in cols])
        ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
        tbl = Table(displayName=name, ref=ref)
        tbl.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
        ws.add_table(tbl)
        for i, c in enumerate(cols, start=1):
            ws.column_dimensions[get_column_letter(i)].width = max(len(c) + 3, 13)
        ws.freeze_panes = "A2"

    path = os.path.join(OUT, "fresh_department_data.xlsx")
    wb.save(path)
    size = os.path.getsize(path) / 1_048_576
    print(f"\n  fresh_department_data.xlsx  {size:.1f} MB, {len(tables)} tables"
          f"  <- upload this one to Power BI")


if __name__ == "__main__":
    main()
