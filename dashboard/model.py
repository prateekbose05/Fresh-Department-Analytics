"""Load the star schema and filter it.

Nine CSVs: four fact tables on a shared date dimension, plus product group,
sub-department, waste reason and role. The joins here mirror the relationships
in docs/DATA_DICTIONARY.md. Two rules carry over from the model design:

- Budget exists at sub-department level and nowhere finer.
- Labour exists at role level only. It has no sub-department, so a
  sub-department filter can never apply to it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
CHANGE_DATE = pd.Timestamp("2025-09-01")
CHANGED = ["Fruit & Veg", "Bakery"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class Model:
    date: pd.DataFrame
    sales: pd.DataFrame
    waste: pd.DataFrame
    labour: pd.DataFrame
    budget: pd.DataFrame
    product_group: pd.DataFrame
    sub_department: pd.DataFrame

    @property
    def sub_departments(self) -> list[str]:
        return list(self.sub_department.sort_values("SubDepartmentSort").SubDepartment)


def load(data_dir: Path = DATA) -> Model:
    """Read the CSVs and attach the dimension columns each fact is sliced by."""
    read = lambda name: pd.read_csv(data_dir / name)

    date = read("dim_date.csv")
    for col in ("Date", "WeekEndDate"):
        date[col] = pd.to_datetime(date[col])
    date["ChangePeriod"] = date.Date.ge(CHANGE_DATE).map(
        {True: "After change", False: "Before change"})
    keys = date[["Date", "WeekIndex", "WeekEndDate", "WeekLabel", "FinancialYear",
                 "DayName", "ChangePeriod"]]

    product_group = read("dim_product_group.csv")
    reason = read("dim_waste_reason.csv")
    role = read("dim_role.csv")

    def fact(name: str) -> pd.DataFrame:
        df = read(name)
        df["Date"] = pd.to_datetime(df["Date"])
        return df.merge(keys, on="Date", how="left", validate="many_to_one")

    sales = fact("fact_sales.csv").merge(product_group, on="ProductGroupKey", validate="many_to_one")
    waste = (fact("fact_waste.csv")
             .merge(product_group, on="ProductGroupKey", validate="many_to_one")
             .merge(reason, on="WasteReason", validate="many_to_one"))
    labour = fact("fact_labour.csv").merge(role, on="RoleKey", validate="many_to_one")
    budget = fact("fact_budget.csv")

    return Model(date, sales, waste, labour, budget, product_group,
                 read("dim_sub_department.csv"))


def apply_filters(model: Model, start=None, end=None,
                  sub_departments: list[str] | None = None) -> Model:
    """Filter by date range and sub-department.

    Dates filter every fact. Sub-department filters sales, waste and budget.
    Labour is left alone: it is not recorded by sub-department.
    """
    def by_date(df: pd.DataFrame) -> pd.DataFrame:
        if start is not None:
            df = df[df.Date >= pd.Timestamp(start)]
        if end is not None:
            df = df[df.Date <= pd.Timestamp(end)]
        return df

    def by_sub(df: pd.DataFrame) -> pd.DataFrame:
        return df if not sub_departments else df[df.SubDepartment.isin(sub_departments)]

    return replace(model, date=by_date(model.date),
                   sales=by_sub(by_date(model.sales)), waste=by_sub(by_date(model.waste)),
                   budget=by_sub(by_date(model.budget)), labour=by_date(model.labour))
