import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "15-condense.md"
PANDAS2_DIFFS = []  # 2.3.3 實測逐字相同
ZONES = {"Z1": "出入口", "Z2": "鋼構組立", "Z3": "開挖區", "Z4": "施工架"}


def test_15_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d15():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def cleaned(d15):
    raw = d15["read_events"]()
    ev, audit = d15["clean"](raw)
    return raw, ev, audit


def test_15_clean_dedupes_and_fixes_percent(d15, cleaned):
    raw, ev, audit = cleaned
    assert audit == {"原始列數": 2838, "重送去重": 20, "confidence 百分比÷100": 69, "補傳（到達晚於 1 小時）": 20}
    assert ev["event_id"].is_unique and len(ev) == 2818
    assert ev["confidence"].max() <= 1 and ev["confidence"].isna().sum() == 231   # null 不補
    assert set(ev.loc[ev["conf_fixed"], "camera_id"]) == {"cam-02"}
    # 重送的就是補傳那批；保留最先到達的那筆
    assert set(ev.loc[ev["late"], "event_id"]) == set(raw.loc[raw["event_id"].duplicated(), "event_id"])
    first = raw.drop_duplicates("event_id", keep="first").set_index("event_id")["ingested_at"]
    assert (ev.set_index("event_id")["ingested_at"] == first.loc[ev["event_id"]]).all()


def test_15_every_summary_row_traces_back(d15, cleaned):
    _, ev, _ = cleaned
    summary = d15["condense"](ev, ZONES)
    assert len(summary) <= 10
    assert summary["key"].ne("").all()
    for key, n in zip(summary["key"], summary["n"]):
        assert len(ev.query(key)) == n, key
    detail = d15["trace"](ev, summary)
    assert detail.groupby("line").size().tolist() == summary["n"].tolist()
    assert detail["event_id"].isin(ev["event_id"]).all()


def test_15_summary_contents(d15, cleaned):
    _, ev, _ = cleaned
    s = d15["condense"](ev, ZONES).set_index("項目")
    top = s[s["類別"] == "Top 人"]
    assert top.index.tolist() == ["W041", "W029", "W044"] and top["n"].tolist() == [36, 33, 27]
    assert "" not in top.index                                       # 未辨識不參加排名
    assert s.loc["辨識不到臉", "n"] == 77
    anomalies = s[s["類別"] == "異常"]
    assert anomalies.index.tolist() == ["W041 2026-09-22"] and anomalies["n"].tolist() == [18]
    assert "14:02–14:53 no_harness" in anomalies["說明"].iloc[0]
    assert s.loc["14:00–14:59", "n"] == 78 and s.loc["Z2 鋼構組立", "n"] == 152
    assert s.loc["週 2026-09-21", "n"] == 123


def test_15_naive_summary_claims(d15, cleaned):
    raw, ev, _ = cleaned
    naive = raw[raw["event_type"] != "ppe_ok"].groupby("worker_id").size().sort_values(ascending=False)
    assert naive.index[0] == "" and naive.iloc[0] == 77
    assert naive.sum() == 498 and ev["is_violation"].sum() == 496
    assert round(ev["confidence"].mean(), 3) == 0.774
    # 修正前後要在同一批（去重後）列上比：2.682；沒去重的 2.667 混進了去重的影響
    before = raw.drop_duplicates("event_id", keep="first")
    assert round(before["confidence"].mean(), 3) == 2.682 and round(raw["confidence"].mean(), 3) == 2.667


def test_15_workshop_removing_w041_rewrites_summary(d15, cleaned):
    """〈參考判讀〉：拿掉 W041 09-22 的 18 筆，四個地方同時改寫。"""
    _, ev, _ = cleaned
    cut = ev.query("not (worker_id == 'W041' and date == '2026-09-22' and is_violation)")
    assert len(cut) == 2800
    s = d15["condense"](cut, ZONES)
    assert s.loc[s["類別"] == "Top 人", "項目"].tolist() == ["W029", "W044", "W018"]
    assert s.loc[s["類別"] == "Top 時段", "項目"].tolist() == ["13:00–13:59"]
    assert s.loc[s["類別"] == "Top 時段", "n"].tolist() == [64]
    trend = s[s["類別"] == "趨勢"].iloc[0]
    assert trend["n"] == 105 and "19.6%→15.0%" in trend["說明"]
    assert "異常" not in set(s["類別"]) and len(s) == 9


def test_15_threshold_claims(d15, cleaned):
    _, ev, _ = cleaned
    v = ev[ev["is_violation"] & (ev["worker_id"] != "")]
    per_day = v.groupby(["worker_id", "date"]).size()
    assert (per_day >= 3).sum() == 14 and (per_day >= 4).sum() == 1
    assert per_day.drop(("W041", "2026-09-22")).max() == 3


def test_15_errors(d15, cleaned):
    raw, ev, _ = cleaned
    with pytest.raises(ValueError, match="event_id 有重複"):
        d15["condense"](raw.assign(is_violation=raw["event_type"] != "ppe_ok"), ZONES)
    summary = d15["condense"](ev, ZONES)
    broken = summary.copy()
    broken.loc[0, "key"] = "is_violation and worker_id == 'W401'"
    with pytest.raises(ValueError, match="追不回任何事件"):
        d15["trace"](ev, broken)


def test_15_lengths(d15, cleaned):
    raw, ev, _ = cleaned
    est = d15["estimate_tokens"]
    full = raw.drop_duplicates("event_id").to_json(orient="records", lines=True, force_ascii=False)
    summary = d15["condense"](ev, ZONES)
    md = summary.to_markdown(index=False)
    assert est(md) * 600 < est(full)
    assert len(md) == 1655 and len(summary.drop(columns="key").to_markdown(index=False)) == 887


def test_15_raw_length_measures_file_lines_not_pandas_json(d15, cleaned):
    """「原始事件」要量檔案原行；to_json() 重新序列化會去空白、把 / 寫成 \\/，量到的是 pandas 格式。"""
    raw, _, _ = cleaned
    text = d15["raw_lines"](raw)
    lines = text.splitlines()
    assert len(text) == 975_730 and len(lines) == 2818
    assert lines[0] == (ROOT / "data" / "events" / "events.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert '"event_id": "' in text and "\\/" not in text
    assert len(raw.drop_duplicates("event_id").to_json(orient="records", lines=True, force_ascii=False)) == 916_552
    with pytest.raises(ValueError, match="行號對不上"):
        d15["raw_lines"](raw.iloc[1:])


def test_15_key_share_without_padding(d15, cleaned):
    """殘留審稿意見：去掉 Markdown 對齊空白後 key 欄佔比——實測 47%，「約一半」成立。"""
    _, ev, _ = cleaned
    s = d15["condense"](ev, ZONES)
    dense = len("".join(s.to_markdown(index=False).split()))
    no_key = len("".join(s.drop(columns="key").to_markdown(index=False).split()))
    assert (dense, no_key) == (750, 400) and round((dense - no_key) / dense, 2) == 0.47


def test_15_notes_are_computed_from_data(d15, cleaned):
    """說明欄不得寫死「連續發生」「隔天才到」：用另一份資料，說明要跟著變。"""
    _, ev, _ = cleaned
    s = d15["condense"](ev, ZONES).set_index("項目")
    assert s.loc["W041 2026-09-22", "說明"] == "14:02–14:53 no_harness，間隔 ≤4 分鐘"
    assert s.loc["補傳", "說明"] == "cam-05 09-10 的事件晚 16–23 小時才到；重送已去重"
    # 把 W041 那天一半的違規搬到 16 點以後：間隔變大，說明要誠實反映
    hit = ev.index[(ev["worker_id"] == "W041") & (ev["date"] == "2026-09-22") & ev["is_violation"]]
    moved = ev.copy()
    moved.loc[hit[9:], "event_time"] = moved.loc[hit[9:], "event_time"].str.replace("T14:", "T16:")
    note = d15["condense"](moved, ZONES).set_index("項目").loc["W041 2026-09-22", "說明"]
    assert note.startswith("14:02–16:53") and "間隔 ≤" in note and "≤4 分鐘" not in note
    # 補傳再晚一天到：延遲小時數要跟著變
    later = ev.copy()
    later.loc[later["late"], "ingested_at"] = (pd.to_datetime(later.loc[later["late"], "ingested_at"], format="ISO8601")
                                               + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    assert d15["condense"](later, ZONES).set_index("項目").loc["補傳", "說明"] == "cam-05 09-10 的事件晚 40–47 小時才到；重送已去重"


def test_15_trace_order_does_not_depend_on_file_order(d15, cleaned):
    _, ev, _ = cleaned
    s = d15["condense"](ev, ZONES)
    a = d15["trace"](ev, s)
    b = d15["trace"](ev.iloc[::-1], s)
    pd.testing.assert_frame_equal(a, b)
    assert a.groupby("line")["event_time"].apply(lambda x: x.is_monotonic_increasing).all()


def test_15_w041_average_ties_w029(d15, cleaned):
    """正文：只看平均，W041 與 W029 同為 1.57，分不出來。"""
    _, ev, _ = cleaned
    v = ev[ev["is_violation"]]
    avg = {w: round((v["worker_id"] == w).sum() / ev.loc[ev["worker_id"] == w, "date"].nunique(), 2)
           for w in ("W041", "W029")}
    assert avg == {"W041": 1.57, "W029": 1.57}
