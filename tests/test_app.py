"""Run the whole app headless and change the filters, the way a user would."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def metrics(app: AppTest) -> dict[str, str]:
    found: dict[str, str] = {}
    for metric in app.metric:
        found.setdefault(metric.label, metric.value)
    return found


def test_default_view_shows_the_published_figures():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    shown = metrics(app)
    assert shown["Net sales"] == "$8,022,126"
    assert shown["Trading margin %"] == "29.08%"


def test_sub_department_filter_changes_sales_and_leaves_labour_alone():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.sidebar.multiselect[0].set_value(["Fruit & Veg"]).run()
    assert not app.exception
    shown = metrics(app)
    assert shown["Net sales"] == "$1,921,645"
    assert shown["Waste % of sales"] == "3.11%"
    assert shown["Labour % of sales"] == "11.47%"

    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert metrics(app)["Net sales"] == "$8,022,126"


def test_financial_year_filter():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.sidebar.selectbox[0].set_value("FY26").run()
    assert not app.exception
    shown = metrics(app)
    assert shown["Net sales"] == "$4,062,760"
    assert shown["Labour % of sales"] == "11.49%"
