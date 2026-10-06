import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "10-event-vs-ingest.md"
PANDAS2_DIFFS = []  # pandas 2.3.3 標準輸出逐字相同


def test_10_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d10():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def raw(d10):
    return d10["load_events"]()


@pytest.fixture(scope="module")
def events(d10, raw):
    return d10["dedupe"](raw)


def test_10_times_are_tz_aware_taipei(raw):
    for col in ("event_ts", "ingest_ts"):
        assert str(raw[col].dt.tz) == "Asia/Taipei"
    # 同一刻：event_time 字串的本地時刻 = 轉換後的時刻
    assert (raw["event_ts"].dt.strftime("%Y-%m-%dT%H:%M:%S+08:00") == raw["event_time"]).all()


def test_10_dedupe_keeps_first_arrival_and_is_idempotent(d10, raw, events):
    assert len(events) == 2818 and events["event_id"].is_unique
    twice = raw[raw["event_id"].duplicated(keep=False)]
    first = twice.groupby("event_id")["ingest_ts"].min()
    assert (events.set_index("event_id").loc[first.index, "ingest_ts"] == first).all()
    # 列的順序打亂、重跑一次，結果一樣
    again = d10["dedupe"](raw.sample(frac=1, random_state=1))
    assert again.sort_values("event_id")["ingested_at"].tolist() == events.sort_values("event_id")["ingested_at"].tolist()
    assert d10["dedupe"](events).equals(events)


def test_10_daily_difference_is_exactly_the_late_batch(d10, events):
    e, i = d10["daily"](events, "event"), d10["daily"](events, "ingest")
    diff = (i - e).fillna(0)
    assert diff[diff != 0].to_dict() == {"2026-09-10": -20, "2026-09-11": 20}
    assert e.sum() == i.sum() == 2818
    moved = events[events["event_ts"].dt.date != events["ingest_ts"].dt.date]
    assert len(moved) == 20 and moved["event_id"].str.startswith("cam-05-20260910-").all()
    assert moved["event_type"].value_counts().to_dict() == {"ppe_ok": 18, "restricted_entry": 2}
    assert len(e) == 24  # 24 個施工日，沒有週日


def test_10_without_dedupe_counts_are_inflated(d10, raw):
    assert d10["daily"](raw, "event")["2026-09-10"] == 137
    assert d10["daily"](raw, "ingest")["2026-09-11"] == 151


def test_10_as_of(d10, events):
    f = d10["as_of"]
    assert f(events, "2026-09-10", "2026-09-10T23:59:59+08:00") == 97
    assert f(events, "2026-09-10", "2026-09-11T09:05:00+08:00") == 97
    assert f(events, "2026-09-10", "2026-09-11T09:06:00+08:00") == 117
    assert f(events, "2026-09-10", "2026-09-11T01:06:00+00:00") == 117   # 同一刻、UTC 寫法
    with pytest.raises(ValueError, match="cutoff 要帶時區"):
        f(events, "2026-09-10", "2026-09-11 12:00:00")


def test_10_utc_date_trap(events):
    utc = events.groupby(events["ingested_at"].str[:10]).size()
    local = events.groupby(events["event_ts"].dt.strftime("%Y-%m-%d")).size()
    t = pd.concat([local, utc], axis=1).fillna(0)
    assert len(t) == 28 and (t.iloc[:, 0] != t.iloc[:, 1]).sum() == 24
    wrong = events[events["ingested_at"].str[:10] != events["event_ts"].dt.strftime("%Y-%m-%d")]
    assert len(wrong) == 230 and (wrong["event_ts"].dt.hour == 7).sum() == 210
    assert utc[[d for d in utc.index if pd.Timestamp(d).dayofweek == 6]].sum() == 31


def test_10_naive_ai_daily_counts():
    """〈參考判讀〉：預設 read_json、不去重、groupby(ingested_at.dt.date)。"""
    import datetime as dt
    x = pd.read_json(ROOT / "data" / "events" / "events.jsonl", lines=True)
    n = x.groupby(x["ingested_at"].dt.date).size()
    assert (n[dt.date(2026, 9, 10)], n[dt.date(2026, 9, 11)], len(n)) == (95, 154, 28)
    assert x.groupby(x["event_time"].dt.date).size()[dt.date(2026, 9, 10)] == 137


def test_10_load_rejects_naive_time(d10, tmp_path):
    lines = (ROOT / "data" / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()[:5]
    lines[2] = lines[2].replace("+00:00", "")
    bad = tmp_path / "e.jsonl"
    bad.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ingested_at 有沒帶時區"):
        d10["load_events"](bad)


def test_10_modified_vs_fetched(d10):
    laws = d10["read_modified_dates"]()
    assert dict(zip(laws["pcode"], laws["modified_date"])) == {
        "N0020007": "20210428", "N0030001": "20240731", "N0020012": "20150701"}
    a = pd.read_json(ROOT / "data" / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    assert a["fetched_at"].unique().tolist() == ["2026-10-05T04:05:23+00:00"]


def test_10_longest_delay_is_first_arrival(raw, events):
    """最長延遲要在每個 event_id 的第一次到達上找；未去重的 idxmax 會落在重送的第二份（23:08:24）。"""
    raw_delay = raw["ingest_ts"] - raw["event_ts"]
    assert raw_delay.max() == pd.Timedelta("23:08:24")
    assert raw["event_id"].duplicated()[raw_delay.idxmax()]          # 天真寫法找到的是重送列
    d = events["ingest_ts"] - events["event_ts"]
    assert d.max() == pd.Timedelta("22:54:24")
    assert events.loc[d.idxmax(), "event_id"] == "cam-05-20260910-0002"
    out = run_main(LESSON)
    assert "最長延遲（第一次到達）：0 days 22:54:24，cam-05-20260910-0002" in out
    assert "23:08:24" not in out
    # 印出的四列裡，最長延遲那一列在第三列，且是同一 event_id 的第一次到達
    sec = out.split("== 2.")[0].rstrip().splitlines()
    assert sec[-2].split()[1] == "cam-05-20260910-0002" and "01:05:29" in sec[-2]


def test_10_late_rows_are_resent_and_backward_rows_split(raw):
    delay = raw["ingest_ts"] - raw["event_ts"]
    late = delay > pd.Timedelta("1min")
    assert late.sum() == 40 and raw.loc[late, "event_id"].nunique() == 20
    back = raw["event_ts"] < raw["event_ts"].shift()
    assert (back.sum(), (back & late).sum(), (back & ~late).sum()) == (45, 20, 25)
    assert (back & ~late & (raw["camera_id"] == "cam-05")).sum() == 5


def test_10_seven_oclock_rows_not_all_shifted(events):
    h7 = events["event_ts"].dt.hour == 7
    wrong = events["ingested_at"].str[:10] != events["event_ts"].dt.strftime("%Y-%m-%d")
    assert h7.sum() == 211 and (h7 & wrong).sum() == 210
    assert events.loc[h7 & ~wrong, "event_time"].tolist() == ["2026-09-16T07:59:56+08:00"]
    out = run_main(LESSON)
    assert "07:xx 發生的共 211 列，沒換日的：['2026-09-16T07:59:56+08:00']" in out
