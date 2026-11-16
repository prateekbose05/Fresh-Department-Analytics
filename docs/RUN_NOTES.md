# Run notes

Everything needed to run, check and change the dashboard, and the problems I hit
on the way.

## Setup

Python 3.10 or later. Built and checked on Python 3.13 on macOS.

```bash
cd Fresh-Department-Analytics
pip3 install -r requirements.txt
```

## Run

```bash
python3 run.py
```

It opens at http://localhost:8501. Stop it with Ctrl+C in the terminal. Use
`run.py` and not `streamlit run app.py`: see "Segmentation fault" below.

## Using the dashboard

- **Financial year** sets the date range to that year (July to June). The data
  runs 2 Sep 2024 to 30 Aug 2026, so FY25 and FY27 are part years.
- **Date range** narrows it further.
- **Sub-department** filters sales, waste, markdown and budget. Leave it empty
  for the whole department.
- **Labour and roster** always shows the whole department, because rosters are
  not written by sub-department. The slider asks how many weeks would run over a
  wage budget set at that percentage of sales.
- **The ordering change** always uses all 104 weeks and ignores the filters,
  because it compares the 52 weeks before 1 September 2025 with the 52 after.

## Check it

```bash
python3 -m pytest tests/ -q
```

13 tests. `test_measures.py` pins the measures to the figures in the README.
`test_app.py` runs the whole app without a browser and changes the filters.

Figures to expect on screen:

| Filter | Net sales | Trading margin | Waste | Labour | Sales vs budget |
|---|---|---|---|---|---|
| None | $8,022,126 | 29.08% | 2.30% | 11.47% | -0.27% |
| Fruit & Veg only | $1,921,645 | 27.66% | 3.11% | 11.47% | -0.46% |
| FY26 | $4,062,760 | 29.18% | 2.11% | 11.49% | -0.34% |

## Rebuild the data

```bash
python3 scripts/generate_data.py    # rewrites data/ from seed 2026
python3 scripts/summarise.py        # weekly rollup, prints the headline figures
```

The seed is fixed, so the numbers come out the same every time. Change the seed
or the generator and the tests will fail until the published figures are
updated to match, which is the point of them.

## Change something

- A new measure goes in `dashboard/measures.py` as a ratio of sums, with a test.
- A new chart goes in `dashboard/charts.py` and is placed on a page in `app.py`.
- Colours come from `theme/fresh_department_theme.json`. Sub-department colours
  are fixed per sub-department so a filter never repaints the ones left.
- If a page changes, retake its screenshot into `images/` at 1500 px wide.

## Problems I hit

**Segmentation fault on macOS when a filter changes.** With
`streamlit run app.py` the first page loaded, then the server died with
`zsh: segmentation fault` as soon as a filter was changed. Running with
`python3 -X faulthandler -m streamlit run app.py` showed the crash inside
pyarrow (`pandas_compat.py`, `convert_column`), which Streamlit uses to send
chart data to the browser. It was Python 3.13.1, pyarrow 25.0.0, pandas 2.2.3
and Streamlit 1.59.1. Setting `ARROW_DEFAULT_MEMORY_POOL=system` before start
stopped it. Switching the allocator from inside `app.py` did not, because
pyarrow is already loaded by then. `run.py` sets it first, so start the app
with `python3 run.py`.

**Power BI.** The project was planned as a Power BI report. Power BI Desktop is
Windows only, and the licence available to me had data-model editing in the
browser turned off, so it was built in Python. The Power BI plan is in
`docs/powerbi/` and is labelled as not built.

**"Port 8501 is already in use".** Another copy is still running. Close that
terminal or stop it with Ctrl+C, then start again.
