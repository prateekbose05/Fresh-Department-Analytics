# DAX measure library

Every measure in the report, in the order I would build them. Nothing here is
copied from a template. The comments explain the choices that are easy to get
wrong, because those are the ones an interviewer asks about.

Create them all on a dedicated `_Measures` table (Home, Enter data, one empty
table named `_Measures`, then hide its placeholder column). Keeping measures off
the fact tables means the field list stays readable and no one mistakes a
measure for a column.

---

## 1. Base measures

The only measures that touch a column directly. Everything else is built from
these, so a change to the source model happens in one place.

```dax
Net Sales = SUM ( fact_sales[NetSales] )

Cost of Sales = SUM ( fact_sales[CostOfSales] )

Markdown = SUM ( fact_sales[MarkdownValue] )

Units Sold = SUM ( fact_sales[UnitsSold] )

Waste Cost = SUM ( fact_waste[WasteCost] )

Actual Labour Cost = SUM ( fact_labour[ActualCost] )

Rostered Labour Cost = SUM ( fact_labour[RosteredCost] )

Actual Hours = SUM ( fact_labour[ActualHours] )

Rostered Hours = SUM ( fact_labour[RosteredHours] )

Sales Budget = SUM ( fact_budget[SalesBudget] )

Wage Budget = SUM ( fact_budget[WageBudget] )

Waste Budget = SUM ( fact_budget[WasteBudget] )
```

---

## 2. Margin

`Gross Margin %` is the number the P&L reports. `Trading Margin %` is the number
that decides whether the department made money, because waste and markdown both
land on the department and neither appears in cost of sales.

```dax
Gross Profit = [Net Sales] - [Cost of Sales]

Gross Margin % = DIVIDE ( [Gross Profit], [Net Sales] )

Shrink = [Waste Cost] + [Markdown]

Trading Margin = [Gross Profit] - [Shrink]

Trading Margin % = DIVIDE ( [Trading Margin], [Net Sales] )

Waste % of Sales = DIVIDE ( [Waste Cost], [Net Sales] )

Markdown % of Sales = DIVIDE ( [Markdown], [Net Sales] )

Shrink % of Sales = DIVIDE ( [Shrink], [Net Sales] )
```

`DIVIDE` rather than `/` throughout: a filter combination with no sales returns
blank instead of an error, and blanks drop out of a visual cleanly.

---

## 3. Labour

```dax
Labour % of Sales = DIVIDE ( [Actual Labour Cost], [Net Sales] )

Sales per Labour Hour = DIVIDE ( [Net Sales], [Actual Hours] )

Average Effective Rate = DIVIDE ( [Actual Labour Cost], [Actual Hours] )

Payroll Variance = [Actual Labour Cost] - [Rostered Labour Cost]

Payroll Variance % = DIVIDE ( [Payroll Variance], [Rostered Labour Cost] )

Hours Variance = [Actual Hours] - [Rostered Hours]
```

`Average Effective Rate` is a weighted average by construction: total cost over
total hours. Averaging the rate column instead would weight a two-hour Sunday
shift the same as a full weekday, and the number would move whenever the roster
mix changed rather than when pay did.

Two different variances, and they answer different questions:

- **Payroll variance** is actual against the roster. It is the shift-by-shift
  question: did we work the hours we said we would.
- **Wage variance to budget** below is the roster and the actuals together
  against the budget. It is the planning question: was the roster ever the right
  size for the trade that turned up.

A department can have a clean payroll variance and still be badly over budget,
which is the case for most of the January weeks in this data.

---

## 4. Budget variance

```dax
Sales vs Budget = [Net Sales] - [Sales Budget]

Sales vs Budget % = DIVIDE ( [Sales vs Budget], [Sales Budget] )

Wage vs Budget = [Actual Labour Cost] - [Wage Budget]

Wage vs Budget % = DIVIDE ( [Wage vs Budget], [Wage Budget] )

Waste vs Budget = [Waste Cost] - [Waste Budget]
```

For wage and waste, over budget is bad, so the sign has to be read the other way
from sales. Rather than trust the reader, the report uses an explicit measure
for conditional formatting:

```dax
Wage Variance Colour =
VAR v = [Wage vs Budget %]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( v ),  "#8A8F98",
        v > 0.03,       "#C0392B",   -- more than 3% over budget
        v > 0.005,      "#E08A2E",
        "#2E7D5B"
    )
```

---

## 5. Time intelligence

`dim_date` must be marked as a date table (Table tools, Mark as date table,
`Date`) or every function below silently returns the wrong window.

```dax
Net Sales LY = CALCULATE ( [Net Sales], SAMEPERIODLASTYEAR ( dim_date[Date] ) )

Sales Growth % LY =
DIVIDE ( [Net Sales] - [Net Sales LY], [Net Sales LY] )

Net Sales PW = CALCULATE ( [Net Sales], DATEADD ( dim_date[Date], -7, DAY ) )

Sales Growth % WoW = DIVIDE ( [Net Sales] - [Net Sales PW], [Net Sales PW] )
```

Rolling four weeks. Written as a ratio of two windowed sums, never as an average
of weekly percentages, because averaging ratios weights a quiet week the same as
a peak week and quietly moves the answer:

```dax
Waste % (4wk) =
VAR Window = DATESINPERIOD ( dim_date[Date], MAX ( dim_date[Date] ), -28, DAY )
RETURN
    DIVIDE (
        CALCULATE ( [Waste Cost], Window ),
        CALCULATE ( [Net Sales], Window )
    )

Labour % (4wk) =
VAR Window = DATESINPERIOD ( dim_date[Date], MAX ( dim_date[Date] ), -28, DAY )
RETURN
    DIVIDE (
        CALCULATE ( [Actual Labour Cost], Window ),
        CALCULATE ( [Net Sales], Window )
    )

Net Sales (4wk avg) =
VAR Window = DATESINPERIOD ( dim_date[Date], MAX ( dim_date[Date] ), -28, DAY )
RETURN DIVIDE ( CALCULATE ( [Net Sales], Window ), 4 )
```

---

## 6. Before and after the ordering change

First a calculated column on `dim_date`, so the split can be used as a slicer
and on an axis, not only inside a measure:

```dax
Change Period =
IF ( dim_date[Date] >= DATE ( 2025, 9, 1 ), "After change", "Before change" )
```

Set its sort order with a second column so "Before change" plots first:

```dax
Change Period Sort = IF ( dim_date[Date] >= DATE ( 2025, 9, 1 ), 2, 1 )
```

Then the comparison measures. `REMOVEFILTERS ( dim_date )` clears whatever the
page's date slicer is doing and the column filter re-applies, so these hold
still while every other slicer on the page still works:

```dax
Waste % Before Change =
CALCULATE (
    [Waste % of Sales],
    REMOVEFILTERS ( dim_date ),
    dim_date[Change Period] = "Before change"
)

Waste % After Change =
CALCULATE (
    [Waste % of Sales],
    REMOVEFILTERS ( dim_date ),
    dim_date[Change Period] = "After change"
)

Waste % Change (pts) = [Waste % After Change] - [Waste % Before Change]
```

Same pattern for markdown and trading margin:

```dax
Markdown % Before Change =
CALCULATE ( [Markdown % of Sales], REMOVEFILTERS ( dim_date ), dim_date[Change Period] = "Before change" )

Markdown % After Change =
CALCULATE ( [Markdown % of Sales], REMOVEFILTERS ( dim_date ), dim_date[Change Period] = "After change" )

Trading Margin % Before Change =
CALCULATE ( [Trading Margin %], REMOVEFILTERS ( dim_date ), dim_date[Change Period] = "Before change" )

Trading Margin % After Change =
CALCULATE ( [Trading Margin %], REMOVEFILTERS ( dim_date ), dim_date[Change Period] = "After change" )

Markdown % Change (pts) = [Markdown % After Change] - [Markdown % Before Change]

Trading Margin % Change = [Trading Margin % After Change] - [Trading Margin % Before Change]
```

The number that pays for the whole exercise. The margin points gained, applied
to the sales that actually ran through the changed period:

```dax
Value of Change =
VAR MarginGain = [Trading Margin % After Change] - [Trading Margin % Before Change]
VAR SalesAfter =
    CALCULATE (
        [Net Sales],
        REMOVEFILTERS ( dim_date ),
        dim_date[Change Period] = "After change"
    )
RETURN MarginGain * SalesAfter
```

Because these respect the sub-department slicer, putting `Waste % Change (pts)`
in a table by sub-department is what shows the control group: the two changed
sub-departments move, the other three do not. Without that comparison the
improvement is just a line that went down, and lines go down for all sorts of
reasons.

---

## 7. Roster what-if

A numeric range parameter (Modeling, New parameter, Numeric range) named
`Wage Budget %`, from 0.09 to 0.14, step 0.0025, default 0.1165. Power BI
generates the table itself; the equivalent by hand is:

```dax
'Wage Budget %' = GENERATESERIES ( 0.09, 0.14, 0.0025 )
```

```dax
Wage Budget (scenario) = [Net Sales] * SELECTEDVALUE ( 'Wage Budget %'[Value], 0.1165 )

Wage vs Scenario = [Actual Labour Cost] - [Wage Budget (scenario)]

Weeks Over Scenario =
VAR Weeks =
    SUMMARIZE (
        dim_date,
        dim_date[WeekIndex],
        "Cost", [Actual Labour Cost],
        "Target", [Wage Budget (scenario)]
    )
RETURN COUNTROWS ( FILTER ( Weeks, [Cost] > [Target] ) )
```

`Weeks Over Scenario` answers the question a department manager actually asks:
not "what is the average", but "how many weeks would I have blown this". Drag
the parameter to 10.5% and the count jumps, which is the honest way to show that
a tighter target is not free.

---

## 8. Dynamic titles

Cheap, and it stops a screenshot being ambiguous about what is filtered.

```dax
Page Subtitle =
VAR Sub =
    IF (
        ISFILTERED ( dim_sub_department[SubDepartment] ),
        CONCATENATEX (
            VALUES ( dim_sub_department[SubDepartment] ),
            dim_sub_department[SubDepartment], ", "
        ),
        "All sub-departments"
    )
VAR Period =
    FORMAT ( MIN ( dim_date[Date] ), "d mmm yyyy" ) & " to "
        & FORMAT ( MAX ( dim_date[Date] ), "d mmm yyyy" )
RETURN Sub & "  |  " & Period
```

---

## Formatting

Set these once on each measure, in the Measure tools ribbon. A dashboard that
shows `0.114732` in a card is not finished.

| Measure group | Format | Decimals |
|---|---|---|
| Sales, cost, margin, labour, budget dollars | Currency, `$`, thousands separator | 0 |
| All `%` measures | Percentage | 1, except `Waste %` and `Labour %` at 2 |
| `Waste % Change (pts)` | Percentage with a `+;-` custom sign | 2 |
| Hours | Whole number, thousands separator | 0 |
| `Sales per Labour Hour`, `Average Effective Rate` | Currency | 2 |
