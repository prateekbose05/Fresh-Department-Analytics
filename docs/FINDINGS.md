# What the data says

Every figure below is printed by `python3 scripts/summarise.py`. Nothing here was
typed in by hand, which is the only way numbers in a write-up stay true after the
tenth edit.

## The department, 104 weeks

| | |
|---|---|
| Net sales | $8,022,126, or $77,136 a week |
| Gross margin | 33.29% |
| Waste | $184,178, 2.30% of sales |
| Markdown | $153,487, 1.91% of sales |
| Trading margin, after waste and markdown | 29.08% |
| Labour cost | $919,750, 11.47% of sales, $8,844 a week |
| Actual against roster | $3,831 over, 0.42% |
| Actual against wage budget | $17,355 under, 1.85% |
| Sales against budget | 0.27% under |

Four points of margin sit between the gross number and the trading number. That
gap is the whole job. Nothing in cost of sales moves it; ordering, rotation and
markdown timing move all of it.

---

## 1. The department was on budget for a year and never on budget for a week

Sales landed 0.27% under budget across 104 weeks. Underneath that, weekly
variance runs from 10.25% under to 22.37% over, and the pattern is not random.
The best week of the two years is the week ending 21 December 2025, at 22.37%
over. The two worst are the weeks ending 20 and 27 April 2025, Easter and ANZAC
Day, both 10.25% under. The budget follows the seasonal trend but takes no view on holiday
timing, so a week with a public holiday in it is planned as an ordinary week.

This is the most common reason a department that hits its year misses every
month. The annual number is right, and it is right by cancellation.

## 2. Labour percentage moves when sales move, not when hours do

Labour ran 11.47% of sales for the period, and the payroll variance to roster was
0.42%. On those two numbers the roster was managed well.

Weekly, labour percentage ranges from 9.61% to 12.65%. The three worst weeks:

| Week | Labour % of sales | Sales vs budget |
|---|---|---|
| W/E 11 Jan 2026 | 12.65% | 9.85% under |
| W/E 18 Jan 2026 | 12.42% | 6.22% under |
| W/E 27 Apr 2025 | 12.31% | 10.25% under |

Every one is a week sales fell short, not a week anyone overspent on hours. The
roster is written a week ahead against a forecast that leans on the trend, so
when trade drops away the hours do not drop with it. Three points of labour
percentage, and none of it is a rostering failure.

The distinction matters because the two problems have different fixes. A payroll
variance is fixed on the floor by sending someone home. This is fixed a week
earlier, by forecasting the drop.

## 3. Waste follows shelf life, so a waste percentage is not comparable across departments

| Sub-department | Waste % of sales |
|---|---|
| Fruit & Veg | 3.11% |
| Meat & Seafood | 2.59% |
| Bakery | 2.56% |
| Deli | 2.52% |
| Dairy & Chilled | 0.76% |

Dairy looks four times better than Fruit and Veg. It is not four times better
run. It sells product with a ten to eighteen day shelf life against three or
four. On the page 2 scatter, waste percentage against shelf life, the
relationship is almost the whole story.

Ranking sub-departments on a raw waste percentage rewards the product mix and
tells you nothing about the ordering. Compare a sub-department to itself over
time, or compare like shelf life to like.

## 4. Most waste is the part you control

| Reason category | Waste | Share |
|---|---|---|
| Ordering & rotation | $100,973 | 54.8% |
| Supplier & quality | $38,265 | 20.8% |
| Production | $25,408 | 13.8% |
| Handling | $19,532 | 10.6% |

More than half of all waste is product that expired on the shelf. That is an
ordering and rotation outcome, and it is the one bucket a department manager
owns outright. It is also the bucket the change in the next section aimed at.

## 5. The ordering change: spend 0.60 points of markdown, save 1.40 points of waste

From 1 September 2025, Fruit & Veg and Bakery moved to tighter order quantities
and earlier markdowns. The other three sub-departments did not change, which
makes them a control group over the same 52 weeks.

| | Waste % | Markdown % | Trading margin % |
|---|---|---|---|
| **Fruit & Veg + Bakery**, before | 3.62% | 1.86% | 34.55% |
| **Fruit & Veg + Bakery**, after | 2.22% | 2.45% | 35.37% |
| Change | **1.40 points down** | 0.60 points up | **0.82 points up** |
| | | | |
| Control sub-departments, before | 1.92% | 1.76% | 25.48% |
| Control sub-departments, after | 1.93% | 1.76% | 25.47% |
| Change | 0.01 points up | flat | 0.01 points down |

Worth $12,712 of trading margin on the $1,553,871 those two sub-departments sold
in the 52 weeks after the change.

The trade is the finding. Marking down earlier costs margin on every unit that
would have sold at full price anyway, and that cost is real and visible at 0.60
points. It is worth paying because the alternative is throwing the stock out at
full cost a day later. Netting the two is the only way to tell, and looking at
either number alone gives the wrong answer: waste alone says the change was
twice as good as it was, markdown alone says it was a failure.

The control group is doing the real work here. A waste line trending down proves
nothing, because waste trends down for all sorts of reasons, including a mild
summer. A waste line trending down while three comparable lines hold flat over
the same weeks is an argument.

---

## What this data cannot tell you

Written down because a portfolio piece that only lists what it proves is not
worth reading.

- **It is synthetic, so the relationships are ones I built in.** The ordering
  change works because the generator makes it work. What the project
  demonstrates is the model, the measures and the reasoning, not a discovery.
- **The control group is not randomised.** Fruit & Veg and Bakery are the two
  most perishable sub-departments, which is why they were chosen for the change
  and also why they had the most room to improve. On real data you would expect
  a regression-to-the-mean argument against this result and you would need a
  longer pre-period to answer it.
- **No promotions, no supplier price movement, no stock-on-hand.** All three
  drive real fresh margin, and a real version of this needs them.
- **One store.** Nothing here says whether the change would hold anywhere else.
