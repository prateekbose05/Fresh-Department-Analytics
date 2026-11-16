# Build guide

> **Status: specification only. This Power BI report was not built.** The
> dashboard in this repo is the Python one (`app.py`). My Power BI licence would
> not allow data models to be edited in the browser, so these notes are kept as
> the plan for a Power BI version of the same model.

How the report gets built, written for Power BI in a browser because that is
where it was built. Power BI Desktop is Windows only and this was made on a Mac,
which turns out to matter for one step. That step is called out below rather
than hidden.

Rough time: two hours for the model and measures, three or four for the pages.

---

## 0. Before you start

You need a Power BI account on a work or school email. Personal Gmail and
Outlook addresses cannot sign up. A university address usually can.

Sign in at `app.powerbi.com` and create a workspace, or use My Workspace.

---

## 1. Generate the data

```bash
python3 scripts/generate_data.py
python3 scripts/summarise.py
```

The first writes nine CSVs and `data/fresh_department_data.xlsx`. The second
writes the weekly rollup and prints every figure quoted in the README, which is
how those figures get checked rather than remembered.

The workbook is the file you upload. Power BI in a browser imports an Excel
workbook and turns each named Excel Table into a table in the semantic model. It
will not take loose CSVs the same way, which is why the generator writes both.

---

## 2. Upload and create the semantic model

1. In your workspace, **New** then **Upload a file**, and pick
   `data/fresh_department_data.xlsx`.
2. Choose **Import** so the Excel tables become a semantic model. Do not choose
   the option that pins the workbook itself; that gives you a spreadsheet on a
   page, not a model.
3. When it finishes you should have a semantic model with nine tables. If you
   have one table, the named Excel Tables did not come through. Re-run the
   generator and check the workbook opens with each sheet as a real table.

### If you cannot edit the model in the browser

Open the semantic model and look for **Edit data model**. If it is not there,
your licence does not include web modelling. Three ways forward:

- Start the free Fabric trial from the account menu, top right. Student and
  staff accounts can usually start one, and it switches web modelling on.
- Build it in Power BI Desktop on any Windows machine and publish it up.
- Fall back to `data/agg_weekly.csv`, which has the ratios precomputed as
  columns so the trend pages work without a single measure. This is a fallback
  and it is worse: a percentage stored as a column is only correct at the grain
  it was computed on, so any total or subtotal over it is wrong. Use it to get
  something on screen, not to ship.

---

## 3. Relationships

Nine tables, a star on both sides of a shared date table. Build these in the
model view by dragging one field onto another. All are one to many, single
direction, from the dimension to the fact.

| From (one) | To (many) | On |
|---|---|---|
| `dim_date[Date]` | `fact_sales[Date]` | Date |
| `dim_date[Date]` | `fact_waste[Date]` | Date |
| `dim_date[Date]` | `fact_labour[Date]` | Date |
| `dim_date[Date]` | `fact_budget[Date]` | Date |
| `dim_product_group[ProductGroupKey]` | `fact_sales[ProductGroupKey]` | ProductGroupKey |
| `dim_product_group[ProductGroupKey]` | `fact_waste[ProductGroupKey]` | ProductGroupKey |
| `dim_sub_department[SubDepartment]` | `dim_product_group[SubDepartment]` | SubDepartment |
| `dim_sub_department[SubDepartment]` | `fact_budget[SubDepartment]` | SubDepartment |
| `dim_waste_reason[WasteReason]` | `fact_waste[WasteReason]` | WasteReason |
| `dim_role[RoleKey]` | `fact_labour[RoleKey]` | RoleKey |

Two decisions worth being able to defend:

**Sub-department is its own table.** The budget is set at sub-department level
and nowhere finer, so it cannot join to `dim_product_group`, where
`SubDepartment` repeats across fourteen rows. Joining on a non-unique key would
fan the budget out fourteen ways and inflate it. The separate table also means a
product-group filter correctly does not filter the budget, because no budget
exists at that grain. That is the model telling the truth about what was
planned, rather than inventing a number.

**Budget is stored daily, not weekly.** The budget is genuinely set by week, and
the generator phases it to days on the trading profile before writing it out.
That keeps one date table and one relationship per fact. The alternative, a
separate week table, needs bridging and breaks the moment someone drags a date
onto an axis. Phasing is what a planning system does anyway.

### Then, in the model view

- Select `dim_date`, and set **Mark as date table** on `Date`. Skip this and
  every time-intelligence measure returns a subtly wrong window.
- Sort `dim_date[MonthYear]` by `MonthYearSort`, and `dim_date[DayName]` by
  `DayOfWeekNumber`. Otherwise months and days sort alphabetically and April
  leads the year.
- Sort `dim_waste_reason[WasteReason]` by `ReasonSort`.
- Hide from report view: every key column, `dim_product_group[SubDepartment]`
  (so people slice on the dimension, not the foreign key), and the raw date
  columns on the fact tables.

---

## 4. Measures

Create an empty table called `_Measures` (**Enter data**, one column, one blank
row, hide the column) and put every measure on it.

Then work through `DAX_MEASURES.md` in order. The base measures first, then
margin, labour, budget, time intelligence, the before-and-after set, the what-if.
Format each one as you create it. Coming back to format forty measures at the end
is how a dashboard ends up showing `0.114732` in a card.

---

## 5. Theme

**View**, **Themes**, **Browse for themes**, and pick
`theme/fresh_department_theme.json`.

The palette is not decorative. The categorical hues run blue, orange, aqua,
yellow, magenta in that fixed order, which is a colourblind-safe ordering:
validated on the adjacent pairs at Delta E 9.1 for protanopia against a floor of
8, and 19.6 for normal vision against a floor of 15. Three of the five sit below
3:1 contrast on a light canvas, so anywhere they carry meaning the visual also
needs a legend and direct labels. That is the reason for the labelled bars and
the table on every page, not neatness.

Budget variance uses a diverging blue to red with a grey midpoint, so zero reads
as nothing rather than as a colour. Status colours are reserved and never reused
for a series.

---

## 6. Pages

Four pages, in the order a department manager would ask the questions.
16:9, 1280 x 720.

Every page carries the same slicer row across the top: date range,
sub-department, financial year. Set these to **sync across pages** so a filter
follows you. On each page, the slicer row sits in the top 80px and the visuals
start below it.

### Page 1, Overview

The one-screen answer to "how did the department do".

| Position | Visual | Fields |
|---|---|---|
| KPI row, 5 cards | Card | `Net Sales`, `Trading Margin %`, `Waste % of Sales`, `Labour % of Sales`, `Sales vs Budget %` |
| Left, large | Line chart | Axis `dim_date[WeekEndDate]`, values `Net Sales`, second line `Sales Budget` |
| Right, top | Line chart | Axis `WeekEndDate`, value `Trading Margin %` and `Gross Margin %` |
| Right, lower | Clustered bar | Axis `dim_sub_department[SubDepartment]`, value `Trading Margin %`, data labels on |
| Bottom | Table | Sub-department by `Net Sales`, `Gross Margin %`, `Waste % of Sales`, `Markdown % of Sales`, `Trading Margin %`, `Labour % of Sales` |

Two separate charts for sales and margin rather than one chart with two y-axes.
A dual axis lets you slide two unrelated scales until they appear to move
together, and the reader has no way to tell. Two charts, one scale each.

### Page 2, Margin and waste

| Position | Visual | Fields |
|---|---|---|
| KPI row | Card | `Waste Cost`, `Waste % of Sales`, `Markdown % of Sales`, `Waste vs Budget` |
| Top left | Line chart | Axis `WeekEndDate`, value `Waste % (4wk)`, by `dim_sub_department[SubDepartment]` |
| Top right | Stacked bar | Axis `dim_waste_reason[ReasonCategory]`, value `Waste Cost` |
| Lower left | Scatter | X `dim_product_group[ShelfLifeDays]`, Y `Waste % of Sales`, size `Net Sales`, detail `ProductGroup` |
| Lower right | Matrix | Rows `SubDepartment`, columns `dim_date[DayName]`, values `Waste % of Sales`, background conditional formatting on the diverging scale |

The scatter is the page's argument: waste tracks shelf life, so a department with
a different product mix is not comparable on a waste percentage, and comparing
them on one is a mistake people make constantly. Cap the scatter at the first
three palette slots or facet it. Beyond three series, an all-pairs form like a
scatter stops being reliably distinguishable, which is why the sub-department
split lives on the line chart and not here.

### Page 3, Labour and roster

| Position | Visual | Fields |
|---|---|---|
| KPI row | Card | `Actual Labour Cost`, `Labour % of Sales`, `Payroll Variance`, `Sales per Labour Hour` |
| Top | Line chart | Axis `WeekEndDate`, values `Labour % (4wk)` |
| Below it | Column chart | Axis `WeekEndDate`, value `Sales vs Budget %` |
| Lower left | Clustered column | Axis `dim_date[DayName]`, values `Rostered Hours` and `Actual Hours` |
| Lower right | Table, top 10 by `Labour % of Sales` | `WeekLabel`, `Net Sales`, `Sales vs Budget %`, `Actual Labour Cost`, `Labour % of Sales`, `Payroll Variance` |
| Side panel | Slider | `Wage Budget %` parameter, with `Weeks Over Scenario` as a card beside it |

Labour percentage and sales-to-budget go one above the other, sharing an x axis
by alignment rather than by a second y axis. Stacked that way the relationship is
obvious: the weeks where labour percentage spikes are the weeks sales missed
budget, not the weeks anyone overspent on hours.

### Page 4, The ordering change

The page that makes the report an analysis instead of a status screen.

| Position | Visual | Fields |
|---|---|---|
| Top | Text box | What changed, when, and in which sub-departments |
| KPI row | Card | `Waste % Change (pts)`, `Value of Change`, and cards for before and after waste |
| Left | Line chart | Axis `WeekEndDate`, value `Waste % (4wk)`, legend `dim_sub_department[SubDepartment]`, with a constant line at 1 September 2025 |
| Right | Clustered column | Axis `SubDepartment`, legend `dim_date[Change Period]`, value `Waste % of Sales` |
| Bottom | Table | Sub-department by `Waste % Before Change`, `Waste % After Change`, `Waste % Change (pts)`, `Markdown % Before Change`, `Markdown % After Change`, `Trading Margin % Change` |

The bottom table is the whole point. It shows the two changed sub-departments
moving and the other three flat over the same window, which is the closest thing
to a control group this data allows. A single line trending down proves nothing.
A line trending down while three comparable lines hold flat is an argument.

---

## 7. Publish and capture

1. Save the report into the workspace.
2. Take a screenshot of each page at full width and drop them in `images/`.
   Name them `01-overview.png` through `04-ordering-change.png`.
3. Reference them in the README. A Power BI project with no images is a project
   nobody can see, and most people reading a repo will not have a Power BI
   licence.
4. If you want a live link, **File**, **Embed report**, **Publish to web**. That
   makes the report public to anyone with the link, so only do it with synthetic
   data. That is one of the reasons this dataset is synthetic.

---

## 8. Before you call it done

- Every measure formatted, no raw decimals anywhere.
- No visual titled "Sum of NetSales by WeekEndDate".
- Tooltips carry more than the plotted value.
- Every page reads on its own with the slicers cleared.
- Cross-filtering works in both directions and nothing goes blank.
- Someone who has never seen the data can say what the fourth page argues.
