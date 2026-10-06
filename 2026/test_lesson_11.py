import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "11-datetime-resample.md"
PANDAS2 = int(pd.__version__.split(".")[0]) < 3
PANDAS2_DIFFS = [("沒有報錯：dtype=object，.dt 不能用；警告 ['FutureWarning']", "ValueError: Mixed timezones detected")]


def test_11_output_matches_lesson():
    out = run_main(LESSON)
    if PANDAS2:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d11():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def events(d11):
    return d11["load_events"]()


@pytest.fixture(scope="module")
def workdays():
    days = pd.date_range("2026-08-31", "2026-09-26", freq="D", tz="Asia/Taipei")
    return days[days.dayofweek != 6]


def test_11_mixed_timezones_by_version():
    mixed = pd.Series(["2026-08-31T07:04:37+08:00", "2026-08-30T23:04:45+00:00"])
    if PANDAS2:
        with pytest.warns(FutureWarning, match="mixed time zones"):
            out = pd.to_datetime(mixed, format="ISO8601")
        assert out.dtype == object
        with pytest.raises(AttributeError, match="Can only use .dt accessor"):
            out.dt.hour
    else:
        with pytest.raises(ValueError, match="Mixed timezones detected"):
            pd.to_datetime(mixed, format="ISO8601")
    fixed = pd.to_datetime(mixed, format="ISO8601", utc=True).dt.tz_convert("Asia/Taipei")
    assert fixed.dt.strftime("%H:%M:%S").tolist() == ["07:04:37", "07:04:45"]


def test_11_dashboard_localized_matches_events(d11, events):
    dash = d11["load_dashboard"]()
    assert str(dash["ts"].dt.tz) == "Asia/Taipei" and len(dash) == 692
    ref = events.set_index("event_id").loc[dash["事件編號"], "ts"].dt.floor("min").reset_index(drop=True)
    assert dash["ts"].reset_index(drop=True).equals(ref)
    wrong = pd.to_datetime(dash["發生時間"], format=d11["DASH_FORMAT"], utc=True)
    assert ((wrong - dash["ts"]) == pd.Timedelta(hours=8)).all()       # 靜默 8 小時
    w = wrong.dt.tz_convert("Asia/Taipei")
    assert (w.dt.date != dash["ts"].dt.date).sum() == 65 and (w.dt.dayofweek == 6).sum() == 11


def test_11_require_aware_errors(d11, events):
    with pytest.raises(ValueError, match="沒有時區"):
        d11["daily_zone"](events.assign(ts=events["ts"].dt.tz_localize(None)))
    with pytest.raises(TypeError, match="不是 datetime"):
        d11["weekly"](events.assign(ts=events["event_time"]))
    with pytest.raises(ValueError, match="start 只能是"):
        d11["weekly"](events, "TUE")
    with pytest.raises(TypeError, match="Already tz-aware"):
        events["ts"].dt.tz_localize("Asia/Taipei")


def test_11_format_and_coerce():
    s = pd.Series(["2026/08/31 07:04", "2026-08-31 07:20", "N/A"])
    with pytest.raises(ValueError, match="doesn't match format"):
        pd.to_datetime(s, format="%Y/%m/%d %H:%M")
    assert pd.to_datetime(s, format="%Y/%m/%d %H:%M", errors="coerce").isna().sum() == 2


def test_11_errors_ignore_by_version():
    s = pd.Series(["2026/08/31 07:04"])
    if PANDAS2:
        with pytest.warns(FutureWarning, match="errors='ignore' is deprecated"):
            pd.to_datetime(s, errors="ignore")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(AssertionError):
                pd.to_datetime(s, errors="ignore")


def test_11_daily_zone_fills_zero(d11, events, workdays):
    t = d11["daily_zone"](events, workdays)
    assert t.shape == (24, 4)
    assert t.sum().to_dict() == {"Z1": 114, "Z2": 152, "Z3": 116, "Z4": 114}
    assert t.loc["2026-09-01", "Z4"] == 0 and t.loc["2026-09-22", "Z4"] == 20
    assert t.index.tz is not None and (t.index.dayofweek != 6).all()
    assert round(t["Z4"].mean(), 2) == 4.75
    # 不給 workdays 的 groupby 版：09-01 Z4 不存在
    v = events[events["event_type"] != "ppe_ok"]
    cells = v.groupby([v["ts"].dt.floor("D"), "zone"]).size()
    assert len(cells) == 95 and round(cells.xs("Z4", level="zone").mean(), 2) == 4.96


def test_11_grouper_vs_resample(events):
    by_res = events.set_index("ts").resample("D").size()
    assert len(by_res) == 27 and (by_res == 0).sum() == 3
    assert len(events.groupby(pd.Grouper(key="ts", freq="D")).size()) == 27
    two = events.groupby([pd.Grouper(key="ts", freq="D"), "zone"]).size()
    assert two.index.get_level_values(0).nunique() == 24 and (two == 0).sum() == 0
    assert len(events.groupby(events["ts"].dt.date).size()) == 24


def test_11_week_anchor(d11, events):
    v = events[events["event_type"] != "ppe_ok"]
    mon = d11["weekly"](v, "MON")
    assert mon.index.dayofweek.tolist() == [0, 0, 0, 0]
    assert mon.index.strftime("%m-%d").tolist() == ["08-31", "09-07", "09-14", "09-21"]
    assert mon.tolist() == [117, 116, 140, 123]
    assert d11["weekly"](v, "SUN").index.dayofweek.tolist() == [6, 6, 6, 6]
    naive = v.set_index("ts").resample("W-MON").size()
    assert naive.tolist() == [23, 117, 120, 135, 101]
    # 週表依區域（〈參考判讀〉）
    t = d11["daily_zone"](events)
    wk = t.resample("W-MON", label="left", closed="left").sum()
    assert wk.values.tolist() == [[26, 32, 38, 21], [29, 36, 26, 25], [35, 49, 30, 26], [24, 35, 22, 42]]
    assert t.resample("W-MON").sum().iloc[0].tolist() == [8, 6, 6, 3]


def test_11_daily_zone_reindex_adds_missing_day(d11, events, workdays):
    """某一天整天沒有違規（例如停電）：groupby 不會產生那一列，reindex 要補成 0。"""
    no_0903 = events[events["ts"].dt.strftime("%m-%d") != "09-03"]
    assert len(d11["daily_zone"](no_0903)) == 23
    t = d11["daily_zone"](no_0903, workdays)
    assert len(t) == 24 and t.loc["2026-09-03"].tolist() == [0, 0, 0, 0]
    assert t.notna().all().all()


def _run_main_on(tmp_path, dash_rows=None, drop_day=None):
    """把 Demo 指到暫存資料夾（截短的儀表板／拿掉一天的事件），確認印出的數字跟著資料變，不是寫死的。"""
    import io
    from contextlib import redirect_stdout
    src = ROOT / "data" / "events"
    dst = tmp_path / "data" / "events"
    dst.mkdir(parents=True)
    dash = (src / "dashboard-export.csv").read_text(encoding="utf-8-sig").splitlines()
    if dash_rows is not None:
        dash = dash[:dash_rows + 1]
    (dst / "dashboard-export.csv").write_text("\n".join(dash) + "\n", encoding="utf-8-sig")
    lines = (src / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if drop_day is not None:
        lines = [ln for ln in lines if f'"event_time": "{drop_day}T' not in ln]
    (dst / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    name, source, _ = load_demo(LESSON)
    out = io.StringIO()
    with redirect_stdout(out), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exec(compile(source, name, "exec"), {"__name__": "__main__", "__file__": str(tmp_path / name)})
    return out.getvalue()


def test_11_counts_in_output_follow_data(tmp_path):
    out = _run_main_on(tmp_path, dash_rows=200, drop_day="2026-09-17")
    assert "localize 版 200 筆全部相同：True" in out
    assert "692" not in out
    # 少了一個施工日：23 天 × 4 區，不是寫死的「24 天 × 4 區 = 96」
    assert "違規 日×區 的 groupby：91 格（23 天 × 4 區 = 92）" in out


def test_11_mixed_rows_prose_matches_output():
    """正文說「第 2、3 列」是 UTC 的 23:04、23:12，要對得上 Demo 印出的索引。"""
    out = run_main(LESSON)
    assert "2    2026-08-30T23:04:45+00:00\n3    2026-08-30T23:12:51+00:00" in out
    text = (ROOT / LESSON).read_text(encoding="utf-8")
    assert "第 2、3 列（UTC 的 23:04、23:12）" in text and "第 2、4 列" not in text
