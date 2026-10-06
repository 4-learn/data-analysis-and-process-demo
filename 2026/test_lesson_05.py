import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "05-event-row.md"
# pandas 2.3.3 concat 時略過全缺值的單列表來決定型別（FutureWarning），3.0.6 不略過 → object。見講義教師紀錄。
PANDAS2_DIFFS = [
    ("事後 pd.concat(frames)：confidence=float64", "事後 pd.concat(frames)：confidence=object"),
    ("迴圈累積的 confidence=float64；數值欄 select_dtypes('number')=['confidence']",
     "迴圈累積的 confidence=object；數值欄 select_dtypes('number')=[]"),
]
PANDAS3 = int(pd.__version__.split(".")[0]) >= 3


@pytest.fixture(scope="module")
def d05():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def first200(d05):
    return d05["load_records"](d05["EVENTS"], 200)


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_05_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_05_concat_in_loop_breaks_index_and_counts_copies(d05, first200):
    df, calls, copied = d05["concat_in_loop"](first200)
    assert len(df) == 200 and calls == 200
    assert copied == 200 * 201 // 2 == 20100
    assert not df.index.is_unique and (df.index == 0).all()
    assert len(df.loc[0]) == 200
    # 計數本身是對的——「計數對、表是壞的」
    assert df.groupby("event_type").size().to_dict() == {
        "no_harness": 7, "no_helmet": 18, "ppe_ok": 169, "restricted_entry": 6}
    assert df["confidence"].dtype == (object if PANDAS3 else "float64")


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_05_concat_in_loop_is_much_slower(d05, first200):
    """講義宣稱慢 100 倍以上（教師本機）；測試只斷言保守的 10 倍，避免在慢機器上抖動。"""
    t = time.perf_counter()
    d05["concat_in_loop"](first200)
    loop = time.perf_counter() - t
    t = time.perf_counter()
    for _ in range(5):
        d05["build_table"](first200)
    once = (time.perf_counter() - t) / 5
    assert loop > 10 * once


def test_05_build_table_contract(d05, first200):
    df = d05["build_table"](first200)
    assert df.shape == (200, 12) and df.index.is_unique
    assert list(df.columns) == d05["SCHEMA"]
    assert df["confidence"].dtype == "float64" and df["confidence"].isna().sum() == 15
    assert df["worker_id"].map(type).eq(str).all()


@pytest.mark.parametrize("breakage, message", [
    (lambda r: {k: v for k, v in r.items() if k != "zone"}, r"缺少 \['zone'\]"),
    (lambda r: {**r, "zone_name": "出入口"}, r"多出 \['zone_name'\]"),
])
def test_05_build_table_rejects_schema_drift(d05, first200, breakage, message):
    bad = list(first200)
    bad[5] = breakage(bad[5])
    with pytest.raises(ValueError, match="第 5 筆欄位不符 schema"):
        d05["build_table"](bad)
    with pytest.raises(ValueError, match=message):
        d05["build_table"](bad)


def test_05_single_row_frames_guess_type_per_row(d05, first200):
    kinds = [str(pd.DataFrame([r])["confidence"].dtype) for r in first200]
    assert kinds.count("object") == 15 and kinds.count("float64") == 185


def test_05_groupby_result_has_no_columns(d05, first200):
    by = d05["build_table"](first200).groupby(["zone", "event_type"]).size()
    with pytest.raises(KeyError):
        by["event_type"]
    assert by.reset_index().columns.tolist() == ["zone", "event_type", 0]
    assert by.reset_index(name="次數").columns.tolist() == ["zone", "event_type", "次數"]


def test_05_event_id_duplicates(d05):
    full = d05["build_table"](d05["load_records"](d05["EVENTS"]))
    assert len(full) == 2838 and full["event_id"].nunique() == 2818
    with pytest.raises(ValueError, match="event_id 重複：20 個 id 共 40 列，例如 cam-05-20260910-0016"):
        d05["index_by_event_id"](full)
    ok = d05["index_by_event_id"](full.drop_duplicates("event_id"))
    assert ok.index.is_unique and len(ok) == 2818


def test_05_dataframe_append_is_gone():
    with pytest.raises(AttributeError, match="append"):
        pd.DataFrame().append({"a": 1})


@pytest.mark.filterwarnings("ignore::FutureWarning")
def test_05_workshop_claims(d05):
    recs = d05["load_records"](d05["EVENTS"], 500)
    df = d05["build_table"](recs)
    frames = [pd.DataFrame([r]) for r in recs]
    assert sum(f["event_type"].iloc[0] == "no_helmet" for f in frames) == 44
    assert (df["event_type"] == "no_helmet").sum() == 44
    v = df[df["event_type"] != "ppe_ok"]
    per_zone = v.groupby("zone").size().reset_index(name="次數")
    assert per_zone.columns.tolist() == ["zone", "次數"]
    assert dict(zip(per_zone["zone"], per_zone["次數"])) == {"Z1": 18, "Z2": 22, "Z3": 30, "Z4": 14}
    by_worker = v.groupby("worker_id").size()
    assert by_worker.idxmax() == "" and by_worker.max() == 14
    named = by_worker.drop("").sort_values(ascending=False)
    assert named.head(3).to_dict() == {"W018": 7, "W029": 7, "W020": 4}
    assert df["event_time"].iloc[0] == "2026-08-31T07:04:37+08:00"
    assert df["event_time"].iloc[-1] == "2026-09-04T10:17:06+08:00"
    looped, _, _ = d05["concat_in_loop"](recs)
    assert (looped["event_type"] == "no_helmet").sum() == 44 and not looped.index.is_unique
