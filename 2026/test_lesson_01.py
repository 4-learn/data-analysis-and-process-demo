import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "01-position.md"
PANDAS2_DIFFS = []  # pandas 2.3.3 標準輸出逐字相同


def test_01_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert len(blocks) == 3
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d01():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def events(d01):
    return d01["read_events"]()


@pytest.fixture(scope="module")
def types(d01):
    return pd.read_csv(d01["TYPES"], dtype=str, keep_default_na=False)


def test_01_estimator_is_the_same_rule_as_lesson_16(d01):
    d16 = load_demo("16-context-budget.md")[2]
    samples = ["", "a", "安全帽", "W041 no_harness 2026-09-22", '{"zone":"Z4"}\n', "第 19 條，高度二公尺以上"]
    for s in samples:
        assert d01["estimate_tokens"](s) == d16["estimate_tokens"](s), s
    assert d01["estimate_tokens"]("ab") == 2            # 0.5*2*1.2=1.2 → 無條件進位 2
    assert d01["estimate_tokens"]("安1") == 3           # 2*1.2=2.4 → 3


def test_01_stream_sees_only_the_burst(d01):
    lines = d01["EVENTS"].read_text(encoding="utf-8").splitlines()
    alerts, peak = d01["stream_alerts"](lines)
    assert len(alerts) == 16 and {a[0] for a in alerts} == {"W041"}
    assert alerts[0] == ("W041", "2026-09-22T14:08:38+08:00", "cam-07")
    assert peak == 4  # 所有人都只留最近 10 分鐘
    # 講義宣稱：W029、W044 四週違規多，但即時規則從未告警
    assert not {"W029", "W044"} & {a[0] for a in alerts}


def test_01_dedupe_and_its_guard(d01, events):
    unique = d01["dedupe"](events)
    assert len(events) == 2838 and len(unique) == 2818 and unique["event_id"].is_unique
    dup_ids = events.loc[events["event_id"].duplicated(), "event_id"]
    bad = events.copy()
    second = bad.index[bad["event_id"] == dup_ids.iloc[0]][1]
    bad.loc[second, "zone"] = "Z9"      # 同一 event_id，內容不同：不是重送
    with pytest.raises(ValueError, match="同一 event_id 內容不同：1 個"):
        d01["dedupe"](bad)


def test_01_weekly_table(d01, events, types):
    table = d01["weekly_violations"](d01["dedupe"](events), types)
    assert list(table.columns) == ["08-31", "09-07", "09-14", "09-21"]
    assert int(table.values.sum()) == 496
    assert table.loc["Z4", "09-21"] == 42 and table.loc["Z2", "09-14"] == 49
    # 沒去重：498（重送裡有 2 筆 restricted_entry）
    assert int(d01["weekly_violations"](events, types).values.sum()) == 498
    with pytest.raises(ValueError, match="未知事件類型"):
        d01["weekly_violations"](events.assign(event_type="no_glove"), types)


def _burst(events):
    return events.index[(events["worker_id"] == "W041") & events["event_time"].str.startswith("2026-09-22T14")]


def test_01_tail_misses_the_anomaly(events):
    burst = _burst(events)
    assert len(burst) == 18
    assert events.tail(500).index.isin(burst).sum() == 0
    # 〈參考判讀〉：先依 event_time 排序再取最後 500 筆，同樣 0／18
    by_time = events.sort_values("event_time", kind="stable").tail(500)
    assert by_time.index.isin(burst).sum() == 0
    assert by_time["event_time"].min().startswith("2026-09-22T15:16")


def test_01_context_sizes(d01, events, types):
    raw = d01["EVENTS"].read_text(encoding="utf-8")
    table = d01["weekly_violations"](d01["dedupe"](events), types)
    assert d01["estimate_tokens"](raw) == 727156
    assert d01["estimate_tokens"](table.to_csv()) == 85
    assert d01["estimate_tokens"](raw) > 3000 * 200


def test_01_workshop_z4_week4_is_mostly_one_person(d01, events, types):
    u = d01["dedupe"](events)
    violation = set(types.loc[types["is_violation"] == "true", "event_type"])
    z4 = u[(u["zone"] == "Z4") & u["event_type"].isin(violation) & (u["event_time"] >= "2026-09-21")]
    assert len(z4) == 42 and (z4["worker_id"] == "W041").sum() == 24


def test_01_three_shapes(d01):
    reports = pd.read_json(d01["DATA"] / "events" / "near-miss-reports.jsonl", lines=True,
                           dtype=False, convert_dates=False)
    assert len(reports) == 40
    assert reports["text"].str.contains(r"09\d\d-\d{3}-\d{3}").sum() == 15
    assert reports["tags"].map(type).eq(list).all()
