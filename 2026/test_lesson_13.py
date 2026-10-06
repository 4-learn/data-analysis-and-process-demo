import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "13-derived-rules.md"
PANDAS2_DIFFS = []  # Demo 標準輸出在 pandas 2.3.3 逐字相同


def test_13_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d13():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def weekly(d13):
    return d13["weekly_counts"]()


def test_13_weekly_grid_keeps_unseen_as_nan(weekly):
    table, _, period = weekly
    assert len(table) == 240 and not table.duplicated(["worker_id", "week"]).any()
    assert period == ("2026-08-31", "2026-09-26")
    assert sorted(table["week"].unique()) == ["2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21"]
    nan = table[table["violations"].isna()]
    assert len(nan) == 32 and set(nan["worker_id"]) == {f"W0{n}" for n in range(53, 61)}
    assert (table["violations"] == 0).sum() == 44
    assert table["violations"].sum() == 419 and table["events"].sum() == 2454


def test_13_risk_level_boundaries_and_nan(d13):
    got = d13["risk_level"](pd.Series([0, 2, 3, 4, 5, 24, np.nan])).tolist()
    assert got == ["低", "低", "中", "中", "高", "高", "無資料"]


def test_13_risk_level_matches_cut_right_false(d13, weekly):
    x = weekly[0]["violations"]
    lv = d13["risk_level"](x)
    assert lv.value_counts().to_dict() == {"低": 154, "中": 39, "高": 15, "無資料": 32}
    cut = pd.cut(x, [0, 3, 5, np.inf], right=False, labels=["低", "中", "高"]).astype(object).fillna("無資料")
    assert (cut == lv).all()
    # 預設 right=True：0 次變 NaN
    assert pd.cut(x, [0, 3, 5, np.inf]).isna().sum() == 76


@pytest.mark.parametrize("values, message", [
    ([1, -1], "不可為負"),
    ([1, 2.5], "必須是整數"),
])
def test_13_risk_level_rejects(d13, values, message):
    with pytest.raises(ValueError, match=message):
        d13["risk_level"](pd.Series(values))


def test_13_rule_with_gap_is_rejected(d13):
    gap = dict(d13["RULE"], levels=[("低", 0, 3), ("高", 5, None)])
    with pytest.raises(ValueError, match="規則沒有涵蓋"):
        d13["risk_level"](pd.Series([4]), gap)


def test_13_qcut_thresholds_move(weekly):
    seen = weekly[0].dropna(subset=["violations"])
    four = {}
    for week, grp in seen.groupby("week"):
        cats = pd.qcut(grp["violations"], [0, 0.5, 0.9, 1], labels=["低", "中", "高"])
        four[week] = set(cats[grp["violations"] == 4].astype(str))
    assert four == {"2026-08-31": {"中"}, "2026-09-07": {"高"}, "2026-09-14": {"中"}, "2026-09-21": {"高"}}


def test_13_rule_description_is_generated_from_rule(d13, weekly):
    _, types, period = weekly
    rule = dict(d13["RULE"], version="risk-v9", levels=[("低", 0, 2), ("高", 2, None)])
    text = d13["describe_rule"](rule, types, period)
    assert "規則 risk-v9" in text and "2026-08-31 ～ 2026-09-26" in text
    assert "低：0 次以上、未滿 2 次" in text and "高：2 次以上" in text
    assert "N0060014 第 19 條" in text and "ppe_ok" not in text
    assert "不是任何法規" in text


def test_13_workshop_claims(d13, weekly):
    table = weekly[0]
    x = table["violations"]
    v1 = d13["risk_level"](x)
    v2 = d13["risk_level"](x, dict(d13["RULE"], version="risk-v2",
                                   levels=[("低", 0, 2), ("中", 2, 4), ("高", 4, None)]))
    assert int((v1 != v2).sum()) == 67
    assert v2.value_counts().to_dict() == {"低": 101, "中": 78, "高": 29, "無資料": 32}
    assert (d13["risk_level"](x.fillna(0)) == "低").sum() == 186
    ai = x.apply(lambda n: "高" if n >= 5 else ("中" if n >= 3 else "低"))
    assert int((ai != v1).sum()) == 32


def test_13_whole_week_level_leaks_future(d13, weekly):
    """教師紀錄：整週等級接回事件，與「事件當下」的等級不同者 490 筆。"""
    table = weekly[0].assign(risk_level=lambda t: d13["risk_level"](t["violations"]))
    ev = pd.read_json(ROOT / "data" / "events" / "events.jsonl", lines=True, dtype=False,
                      convert_dates=False).drop_duplicates("event_id")
    ev = ev[ev["worker_id"] != ""].copy()
    ev["v"] = ev["event_type"].isin({"no_helmet", "no_harness", "restricted_entry"})
    day = pd.to_datetime(ev["event_time"].str[:10])
    ev["week"] = (day - pd.to_timedelta(day.dt.dayofweek, unit="D")).dt.strftime("%Y-%m-%d")
    ev["t"] = pd.to_datetime(ev["event_time"], format="ISO8601")
    ev = ev.sort_values(["t", "event_id"])
    ev["prior"] = ev.groupby(["worker_id", "week"])["v"].cumsum() - ev["v"]
    m = ev.merge(table[["worker_id", "week", "risk_level"]], on=["worker_id", "week"],
                 how="left", validate="many_to_one")
    asof = d13["risk_level"](m["prior"].astype(float))
    assert len(m) == 2454 and int((asof != m["risk_level"]).sum()) == 490
    assert ((m["risk_level"] == "高").sum(), (asof == "高").sum()) == (213, 82)
    assert ((ev["handled_at"] != "") & ev["v"]).sum() == 190 and ev["v"].sum() == 419


def test_13_error_breakdown_counts_actual_wrong_rows(d13, weekly):
    """分錯原因要拿「實際分錯的列」拆，不是拿「值剛好是 3 或 5 的列」去湊。"""
    x = weekly[0]["violations"]
    v1 = d13["risk_level"](x)
    naive = x.apply(lambda n: "高" if n > 5 else ("中" if n > 3 else "低"))
    assert d13["error_breakdown"](x, naive, v1) == (61, {"邊界 3 或 5 次": 29, "NaN": 32, "其他": 0})
    # 邊界寫對的 AI 版本：只剩 NaN 錯。若用 x.isin([3, 5]) 湊數，會誤報邊界錯 29 列
    fixed = x.apply(lambda n: "高" if n >= 5 else ("中" if n >= 3 else "低"))
    assert d13["error_breakdown"](x, fixed, v1) == (32, {"邊界 3 或 5 次": 0, "NaN": 32, "其他": 0})


def test_13_cut_zero_count_is_measured_not_assumed(d13, weekly):
    """「其中 0 次的 N 列」要真的數 NaN 裡原值為 0 的列，不能 right=False 就寫死 0。"""
    x = weekly[0]["violations"]
    assert d13["cut_counts"](x, [0, 3, 5, np.inf], True) == {"低": 135, "中": 18, "高": 11, "NaN": 76, "0 次": 44}
    assert d13["cut_counts"](x, [0, 3, 5, np.inf], False) == {"低": 154, "中": 39, "高": 15, "NaN": 32, "0 次": 0}
    # right=False 但下限從 1 起算：0 次照樣變 NaN
    assert d13["cut_counts"](x, [1, 3, 5, np.inf], False)["0 次"] == 44
