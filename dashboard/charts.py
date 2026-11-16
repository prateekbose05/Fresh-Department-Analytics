"""Charts. One function per visual, each returning an Altair chart.

Colour rules, from theme/fresh_department_theme.json:

- Sub-departments keep a fixed colour wherever they appear, in a
  colourblind-checked order (blue, orange, aqua, yellow, magenta).
- A single series is blue. A reference series (budget, roster, "before") is grey.
- Over and under budget use the blue to red diverging pair.
- No chart has two y axes. Measures on different scales get separate charts
  stacked on a shared x axis.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

from .model import CHANGE_DATE, DAY_ORDER

BLUE, ORANGE, GREY, RED = "#2a78d6", "#eb6834", "#898781", "#d03b3b"
SUB_COLOURS = {"Bakery": "#2a78d6", "Dairy & Chilled": "#eb6834", "Deli": "#1baf7a",
               "Fruit & Veg": "#eda100", "Meat & Seafood": "#e87ba4"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e1e0d9"
PCT, PCT1, DOLLARS = ".2%", ".1%", "$,.0f"


def _style(chart: alt.TopLevelMixin) -> alt.TopLevelMixin:
    if chart.padding is alt.Undefined:
        chart = chart.properties(padding={"left": 16, "right": 16, "top": 16, "bottom": 16})
    return (chart
            .configure(background="#ffffff", font='"Source Sans", "Source Sans Pro", "Segoe UI", Helvetica, Arial, sans-serif')
            .configure_view(stroke=None)
            .configure_axis(gridColor=GRID, domainColor=GRID, tickColor=GRID, labelColor=MUTED,
                            titleColor=MUTED, labelFontSize=11, titleFontSize=11,
                            titleFontWeight="normal")
            .configure_legend(orient="top", direction="horizontal", title=None,
                              labelColor=MUTED, labelFontSize=11, symbolStrokeWidth=3)
            .configure_title(anchor="start", color=INK, fontSize=13, fontWeight=600, offset=10))


def _lines(long: pd.DataFrame, x: str, series: str, value: str, colours: dict[str, str],
           fmt: str, title: str, height: int = 260, zero: bool = False) -> alt.LayerChart:
    """Multi-series line chart with a hover rule that reads every series at once."""
    domain = [k for k in colours if k in set(long[series])]
    colour = alt.Color(f"{series}:N", scale=alt.Scale(domain=domain,
                                                      range=[colours[k] for k in domain]),
                       legend=alt.Legend() if len(domain) > 1 else None)
    base = alt.Chart(long).encode(
        x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%b %y", grid=False)),
        y=alt.Y(f"{value}:Q", title=None, scale=alt.Scale(zero=zero),
                axis=alt.Axis(format=fmt, tickCount=5)))
    lines = base.mark_line(strokeWidth=2, strokeJoin="round", strokeCap="round").encode(color=colour)

    hover = alt.selection_point(nearest=True, on="pointerover", fields=[x], empty=False,
                                clear="pointerout")
    wide = long.pivot_table(index=x, columns=series, values=value).reset_index()
    tips = [alt.Tooltip(f"{x}:T", title="Week ending", format="%d %b %Y")] + \
           [alt.Tooltip(f"{k}:Q", format=fmt if fmt.endswith("%") else DOLLARS) for k in domain]
    rule = (alt.Chart(wide).mark_rule(color=GREY, strokeWidth=1)
            .encode(x=f"{x}:T", tooltip=tips,
                    opacity=alt.condition(hover, alt.value(1), alt.value(0)))
            .add_params(hover))
    dots = (base.mark_point(filled=True, size=70, stroke="#ffffff", strokeWidth=2, opacity=1)
            .encode(color=colour).transform_filter(hover))
    return (lines + rule + dots).properties(title=title, height=height)


def sales_vs_budget(week: pd.DataFrame) -> alt.TopLevelMixin:
    long = week.melt("WeekEndDate", ["NetSales", "SalesBudget"], "Series", "Value")
    long["Series"] = long.Series.map({"NetSales": "Net sales", "SalesBudget": "Sales budget"})
    return _style(_lines(long, "WeekEndDate", "Series", "Value",
                         {"Net sales": BLUE, "Sales budget": GREY}, "$~s",
                         "Weekly net sales against budget", 300))


def margins(week: pd.DataFrame) -> alt.TopLevelMixin:
    long = week.melt("WeekEndDate", ["GrossMarginPct", "TradingMarginPct"], "Series", "Value")
    long["Series"] = long.Series.map({"GrossMarginPct": "Gross margin %",
                                      "TradingMarginPct": "Trading margin %"})
    return _style(_lines(long, "WeekEndDate", "Series", "Value",
                         {"Gross margin %": GREY, "Trading margin %": BLUE}, PCT1,
                         "Gross margin and trading margin (after waste and markdown)", 300))


def _hbar(df: pd.DataFrame, category: str, value: str, label: str, title: str,
          tips: list, sort="-x") -> alt.TopLevelMixin:
    base = alt.Chart(df).encode(
        y=alt.Y(f"{category}:N", sort=sort, title=None,
                axis=alt.Axis(labelLimit=180, ticks=False, domain=False, labelPadding=8)),
        x=alt.X(f"{value}:Q", title=None, axis=None, scale=alt.Scale(nice=False)))
    bars = base.mark_bar(size=20, color=BLUE, cornerRadiusEnd=4).encode(tooltip=tips)
    text = base.mark_text(align="left", dx=6, color=MUTED, fontSize=12).encode(text=f"{label}:N")
    return _style((bars + text).properties(title=title, height=alt.Step(34),
                                           padding={"right": 110, "left": 14, "top": 14, "bottom": 14}))


def trading_margin_by_sub_department(by: pd.DataFrame) -> alt.TopLevelMixin:
    df = by.assign(Label=by["Trading Margin %"].map(lambda v: f"{v:.2%}"))
    return _hbar(df, "SubDepartment", "Trading Margin %", "Label",
                 "Trading margin % by sub-department",
                 [alt.Tooltip("SubDepartment:N", title="Sub-department"),
                  alt.Tooltip("Trading Margin %:Q", format=PCT),
                  alt.Tooltip("Gross Margin %:Q", format=PCT),
                  alt.Tooltip("Net Sales:Q", format=DOLLARS)])


def waste_by_reason(by: pd.DataFrame) -> alt.TopLevelMixin:
    df = by.assign(Label=[f"${c:,.0f}  ({s:.1%})" for c, s in zip(by.WasteCost, by.Share)])
    return _hbar(df, "ReasonCategory", "WasteCost", "Label", "Waste cost by reason",
                 [alt.Tooltip("ReasonCategory:N", title="Reason"),
                  alt.Tooltip("WasteCost:Q", title="Waste cost", format=DOLLARS),
                  alt.Tooltip("Share:Q", title="Share of waste", format=PCT1)])


def waste_trend(by_week: pd.DataFrame, mark_change: bool = False,
                title: str = "Waste % of sales, four-week rolling") -> alt.TopLevelMixin:
    chart = _lines(by_week, "WeekEndDate", "SubDepartment", "WastePct4wk", SUB_COLOURS, PCT1,
                   title, 300, zero=True)
    if mark_change:
        when = pd.DataFrame({"Date": [CHANGE_DATE], "Label": ["Ordering change, 1 Sep 2025"]})
        rule = alt.Chart(when).mark_rule(color=INK, strokeWidth=1).encode(x="Date:T")
        label = (alt.Chart(when).mark_text(align="left", dx=6, dy=-4, baseline="top", color=INK,
                                            fontSize=11)
                 .encode(x="Date:T", y=alt.value(0), text="Label:N"))
        chart = chart + rule + label
    return _style(chart)


def waste_vs_shelf_life(groups: pd.DataFrame) -> alt.TopLevelMixin:
    """Waste % against shelf life. One colour: the argument is the slope, not the split."""
    base = alt.Chart(groups).encode(
        x=alt.X("ShelfLifeDays:Q", title="Shelf life (days)", scale=alt.Scale(domainMin=0),
                axis=alt.Axis(grid=False)),
        y=alt.Y("WastePct:Q", title=None, axis=alt.Axis(format=PCT1, tickCount=5)))
    dots = base.mark_circle(color=BLUE, opacity=0.85, stroke="#ffffff", strokeWidth=2).encode(
        size=alt.Size("NetSales:Q", scale=alt.Scale(range=[90, 700]), legend=None),
        tooltip=[alt.Tooltip("ProductGroup:N", title="Product group"),
                 alt.Tooltip("SubDepartment:N", title="Sub-department"),
                 alt.Tooltip("ShelfLifeDays:Q", title="Shelf life (days)"),
                 alt.Tooltip("WastePct:Q", title="Waste % of sales", format=PCT),
                 alt.Tooltip("NetSales:Q", title="Net sales", format=DOLLARS)])
    ends = pd.concat([groups.nlargest(2, "WastePct"), groups.nlargest(2, "ShelfLifeDays")])
    labels = (alt.Chart(ends.drop_duplicates("ProductGroup"))
              .mark_text(align="left", dx=16, color=MUTED, fontSize=11)
              .encode(x="ShelfLifeDays:Q", y="WastePct:Q", text="ProductGroup:N"))
    return _style((dots + labels).properties(
        title="Waste % against shelf life, by product group (bubble size is sales)",
        height=300, padding={"right": 90, "left": 14, "top": 14, "bottom": 14}))


def waste_by_day(by_day: pd.DataFrame, order: list[str]) -> alt.TopLevelMixin:
    mid = (by_day.WastePct.min() + by_day.WastePct.max()) / 2
    base = alt.Chart(by_day).encode(
        x=alt.X("DayName:N", sort=DAY_ORDER, title=None,
                axis=alt.Axis(orient="top", labelAngle=0, ticks=False, domain=False,
                              labelExpr="slice(datum.value, 0, 3)")),
        y=alt.Y("SubDepartment:N", sort=order, title=None,
                axis=alt.Axis(ticks=False, domain=False, labelLimit=160)))
    cells = base.mark_rect(stroke="#ffffff", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color("WastePct:Q", legend=None,
                        scale=alt.Scale(range=["#eaf2fc", "#1f5fae"])),
        tooltip=[alt.Tooltip("SubDepartment:N", title="Sub-department"),
                 alt.Tooltip("DayName:N", title="Day"),
                 alt.Tooltip("WastePct:Q", title="Waste % of sales", format=PCT)])
    text = base.mark_text(fontSize=11).encode(
        text=alt.Text("WastePct:Q", format=PCT1),
        color=alt.condition(alt.datum.WastePct > mid, alt.value("#ffffff"), alt.value(INK)))
    return _style((cells + text).properties(title="Waste % of sales by day of week",
                                            height=alt.Step(40)))


def _week_axis() -> alt.X:
    return alt.X("WeekEndDate:T", title=None, axis=alt.Axis(format="%b %y", grid=False))


def _labour_tips() -> list:
    return [alt.Tooltip("WeekLabel:N", title="Week"),
            alt.Tooltip("LabourPct:Q", title="Labour % of sales", format=PCT),
            alt.Tooltip("SalesVsBudgetPct:Q", title="Sales vs budget", format="+.2%"),
            alt.Tooltip("PayrollVariance:Q", title="Actual vs roster", format="+$,.0f")]


def labour_pct(week: pd.DataFrame) -> alt.TopLevelMixin:
    """Weekly labour %. Sits directly above `sales_vs_budget_pct` on the same time axis."""
    y = alt.Y("LabourPct:Q", title=None, scale=alt.Scale(zero=False),
              axis=alt.Axis(format=PCT1, tickCount=4, minExtent=44))
    line = alt.Chart(week).mark_line(color=BLUE, strokeWidth=2, strokeJoin="round").encode(
        x=_week_axis(), y=y)
    hit = alt.Chart(week).mark_circle(color=BLUE, size=90, opacity=0).encode(
        x="WeekEndDate:T", y="LabourPct:Q", tooltip=_labour_tips())
    return _style((line + hit).properties(title="Labour % of sales, weekly", height=190))


def sales_vs_budget_pct(week: pd.DataFrame) -> alt.TopLevelMixin:
    """Weekly sales against budget. Bars above zero are over budget, below are under."""
    signed = week.assign(Side=week.SalesVsBudgetPct.ge(0).map({True: "Over", False: "Under"}))
    bars = alt.Chart(signed).mark_bar(size=4, cornerRadiusEnd=2).encode(
        x=_week_axis(), tooltip=_labour_tips(),
        y=alt.Y("SalesVsBudgetPct:Q", title=None,
                axis=alt.Axis(format="+.0%", tickCount=4, minExtent=44)),
        color=alt.Color("Side:N", legend=None,
                        scale=alt.Scale(domain=["Over", "Under"], range=[BLUE, RED])))
    return _style(bars.properties(title="Sales against budget, weekly", height=170))


def _grouped_columns(long: pd.DataFrame, category: str, series: str, value: str,
                     colours: dict[str, str], fmt: str, title: str, sort,
                     label_expr: str = "datum.label") -> alt.TopLevelMixin:
    domain = list(colours)
    chart = alt.Chart(long).mark_bar(cornerRadiusEnd=4, size=16).encode(
        x=alt.X(f"{category}:N", sort=sort, title=None,
                axis=alt.Axis(labelAngle=0, ticks=False, labelLimit=110, labelOverlap=False,
                              labelExpr=label_expr)),
        xOffset=alt.XOffset(f"{series}:N", sort=domain),
        y=alt.Y(f"{value}:Q", title=None, axis=alt.Axis(format=fmt, tickCount=5)),
        color=alt.Color(f"{series}:N", scale=alt.Scale(domain=domain,
                                                       range=list(colours.values()))),
        tooltip=[alt.Tooltip(f"{category}:N"), alt.Tooltip(f"{series}:N", title="Series"),
                 alt.Tooltip(f"{value}:Q", title="Value", format=fmt if "%" in fmt else ",.0f")])
    return _style(chart.properties(title=title, height=260))


def hours_by_day(hours: pd.DataFrame) -> alt.TopLevelMixin:
    long = hours.melt("DayName", ["RosteredHours", "ActualHours"], "Series", "Hours")
    long["Series"] = long.Series.map({"RosteredHours": "Rostered hours",
                                      "ActualHours": "Actual hours"})
    return _grouped_columns(long, "DayName", "Series", "Hours",
                            {"Rostered hours": GREY, "Actual hours": BLUE}, ",.0f",
                            "Rostered and actual hours by day of week", DAY_ORDER,
                            label_expr="slice(datum.value, 0, 3)")


def waste_before_after(table: pd.DataFrame, order: list[str]) -> alt.TopLevelMixin:
    rows = table[table.SubDepartment.isin(order)]
    long = rows.melt("SubDepartment", ["Waste % of Sales Before", "Waste % of Sales After"],
                     "Series", "Waste")
    long["Series"] = long.Series.map({"Waste % of Sales Before": "Before change",
                                      "Waste % of Sales After": "After change"})
    return _grouped_columns(long, "SubDepartment", "Series", "Waste",
                            {"Before change": GREY, "After change": BLUE}, PCT1,
                            "Waste % of sales before and after, by sub-department", order,
                            label_expr="split(replace(datum.value, ' & ', ' &|'), '|')")
