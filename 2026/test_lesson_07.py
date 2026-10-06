import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "07-select-filter.md"
PANDAS3 = int(pd.__version__.split(".")[0]) >= 3
PANDAS2_DIFFS = [
    ("df[cond][col] = x：警告 SettingWithCopyWarning；原表仍 > 1 的有 69 筆",
     "df[cond][col] = x：警告 ChainedAssignmentError；原表仍 > 1 的有 69 筆"),
    ("df[col][cond] = x：警告 FutureWarning,SettingWithCopyWarning；原表仍 > 1 的有 0 筆",
     "df[col][cond] = x：警告 ChainedAssignmentError；原表仍 > 1 的有 69 筆"),
]


@pytest.fixture(scope="module")
def d07():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def df(d07):
    return d07["load_events"]()


def test_07_output_matches_lesson():
    out = run_main(LESSON)
    if not PANDAS3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


def test_07_loc_vs_iloc_after_filter(df):
    viol = df[df["is_violation"]]
    assert len(viol) == 498 and viol.index[0] == 2
    with pytest.raises(KeyError):
        viol.loc[0]
    assert viol.iloc[0]["event_id"] == viol.loc[2, "event_id"]
    assert len(df.loc[0:2]) == 3 and len(df.iloc[0:2]) == 2


def test_07_precedence_traps(df):
    hour = df["event_time"].str[11:13].astype(int)
    v = df["is_violation"]
    assert (v & (hour >= 14)).sum() == 174
    assert (v & hour >= 14).sum() == 0
    assert (v & (df["confidence"] > 0.9)).sum() == 72
    assert (v & df["confidence"] > 0.9).sum() == 454 == (v & df["confidence"].notna()).sum()
    with pytest.raises(TypeError):
        df["zone"] == "Z4" | df["zone"] == "Z3"
    with pytest.raises(ValueError, match="ambiguous"):
        hour >= 14 and hour < 16


def test_07_nan_falls_out_of_both_sides(df):
    c = df["confidence"]
    high, low = c > 0.6, c <= 0.6
    assert c.isna().sum() == 231
    assert high.sum() + low.sum() == len(df) - 231
    assert (~high).sum() == low.sum() + 231
    assert not (high & c.isna()).any() and not (low & c.isna()).any()
    assert (c == float("nan")).sum() == 0
    assert (c > 1).sum() == 69 and ((c > 1) & high).sum() == 69


def test_07_chained_assignment(d07, df):
    bug = df["confidence"] > 1
    kind, left = d07["chained_assignment"](df, bug, "df[cond][col] = x")
    assert left == 69
    assert kind == ("ChainedAssignmentError" if PANDAS3 else "SettingWithCopyWarning")
    kind, left = d07["chained_assignment"](df, bug, "df[col][cond] = x")
    assert left == (69 if PANDAS3 else 0)
    assert d07["chained_assignment"](df, bug, "df.loc[cond, col] = x") == ("無", 0)
    assert (df["confidence"] > 1).sum() == 69  # 原 df 未被動到
    with pytest.raises(ValueError, match="未知寫法"):
        d07["chained_assignment"](df, bug, "df.iloc[cond] = x")


def test_07_ai_fixes_do_not_fix(df):
    bug = df["confidence"] > 1
    d = df.copy()
    sub = d[bug].copy()
    sub["confidence"] = sub["confidence"] / 100
    assert (d["confidence"] > 1).sum() == 69 and (sub["confidence"] > 1).sum() == 0
    with pd.option_context("mode.chained_assignment", None):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            d[bug]["confidence"] = d[bug]["confidence"] / 100
    names = {w.category.__name__ for w in caught}
    assert names == ({"ChainedAssignmentError"} if PANDAS3 else set())
    assert (d["confidence"] > 1).sum() == 69
    d["confidence"] = d["confidence"].mask(bug, d["confidence"] / 100)
    assert (d["confidence"] > 1).sum() == 0
    assert hasattr(pd.errors, "SettingWithCopyWarning") == (not PANDAS3)


def test_07_subset_and_query(d07, df):
    s = d07["subset"](df, "Z4", "2026-09-22T14:00", "2026-09-22T16:00", "no_harness")
    assert len(s) == 18 and set(s["worker_id"]) == {"W041"}
    q = df.query('zone == "Z4" and event_type == "no_harness" '
                 'and "2026-09-22T14:00" <= event_time < "2026-09-22T16:00"')
    assert q.index.equals(s.index)
    s = d07["subset"](df, "Z3", "2026-09-10T00:00", "2026-09-11T00:00", "restricted_entry")
    assert len(s) == 4 and s["event_id"].nunique() == 2


def test_07_subset_rejects_other_timezone(d07, df):
    bad = df.head(5).copy()
    bad.loc[bad.index[0], "event_time"] = "2026-08-31T00:00:00+00:00"
    with pytest.raises(ValueError, match=r"\+08:00"):
        d07["subset"](bad, "Z1", "2026-08-31", "2026-09-01", "ppe_ok")


def test_07_top_k_ties(d07, df):
    counts = df[df["is_violation"]].groupby("worker_id").size()
    assert counts.idxmax() == "" and counts.max() == 77
    named = counts.drop("")
    assert list(named.nlargest(3).index) == list(named.sort_values(ascending=False).head(3).index) == ["W041", "W029", "W044"]
    assert list(d07["top_k"](named, 5, "first").index)[-1] == "W007"
    assert list(d07["top_k"](named, 5, "last").index)[-1] == "W017"
    assert len(d07["top_k"](named, 5, "all")) == 6
    with pytest.raises(ValueError, match="keep"):
        d07["top_k"](named, 5, "random")


def test_07_workshop(d07, df):
    s = d07["subset"](df, "Z1", "2026-09-15T00:00", "2026-09-18T00:00", "no_helmet")
    c = s["confidence"]
    assert len(s) == 16 and s["camera_id"].value_counts().to_dict() == {"cam-01": 9, "cam-02": 7}
    assert c.isna().sum() == 0 and (c > 1).sum() == 7
    assert (c > 0.8).sum() == 10
    fixed = df.copy()
    bug = fixed["confidence"] > 1
    fixed.loc[bug, "confidence"] = fixed.loc[bug, "confidence"] / 100
    assert (fixed.loc[s.index, "confidence"] > 0.8).sum() == 6
    t = df["event_time"]
    wrong = (df["zone"] == "Z1") & (t >= "2026-09-15") & (t <= "2026-09-17") & (df["event_type"] == "no_helmet")
    assert wrong.sum() < 16

    def restricted(d):
        r = d[(d["event_type"] == "restricted_entry") & (d["worker_id"] != "")]
        return r.groupby("worker_id").size()

    raw = restricted(df)
    for keep in ("first", "last", "all"):
        assert raw.nlargest(3, keep=keep).to_dict() == {"W018": 11, "W025": 7, "W007": 6}
    dedup = restricted(df.drop_duplicates("event_id"))
    assert dedup.nlargest(3, keep="first").to_dict() == {"W018": 11, "W007": 6, "W004": 5}
    assert dedup.nlargest(3, keep="last").to_dict() == {"W018": 11, "W007": 6, "W025": 5}
    assert dedup.nlargest(3, keep="all").to_dict() == {"W018": 11, "W007": 6, "W004": 5, "W025": 5}


def test_07_subset_end_is_exclusive(d07, df):
    edge = df.head(3).copy()
    edge["zone"], edge["event_type"] = "Z1", "no_helmet"
    edge["event_time"] = ["2026-09-15T00:00:00+08:00", "2026-09-17T23:59:00+08:00", "2026-09-18T00:00:00+08:00"]
    end = "2026-09-18T00:00:00+08:00"  # 與第三筆字串完全相同：含 start、不含 end
    assert len(d07["subset"](edge, "Z1", "2026-09-15T00:00:00+08:00", end, "no_helmet")) == 2


def test_07_conf_gt_09_includes_percentage_bug(df):
    """72 列不是「正確答案」：其中 7 列是 cam-02 百分比 bug，改回小數後是 67。"""
    v, c = df["is_violation"], df["confidence"]
    assert (v & (c > 0.9)).sum() == 72 and (v & (c > 1)).sum() == 7
    fixed = c.mask(c > 1, c / 100)
    assert (v & (fixed > 0.9)).sum() == 67
    text = (ROOT / LESSON).read_text(encoding="utf-8")
    assert "正確的 72" not in text
    block2 = next(b for b in pasted_blocks(LESSON) if b.startswith("== 2."))
    assert "百分比改回小數後再算是 67 列" in block2


def test_07_stable_sort_matches_nlargest(df):
    """Demo 的 sort_values 必須是穩定排序，並列時 head(k) 才會與 nlargest(keep='first') 一致。"""
    out = run_main(LESSON)
    line = next(l for l in out.splitlines() if l.startswith("sort_values(kind='stable').head(5)"))
    first = next(l for l in out.splitlines() if l.startswith("nlargest(5, keep='first')"))
    assert line.split("→")[1] == first.split("→")[1]
    near = next(l for l in out.splitlines() if l.startswith("第 5 名附近"))
    assert near.index("W007") < near.index("W017")
    named = df[df["is_violation"]].groupby("worker_id").size().drop("")
    stable = named.sort_values(ascending=False, kind="stable")
    assert list(stable.head(5).index) == list(named.nlargest(5).index)
    # 講義宣稱：不加 kind 的預設排序在本機兩環境給 W017（並列順序不保證的實例）
    assert list(named.sort_values(ascending=False).head(5).index)[-1] == "W017"


def test_07_workshop_dedup_tie_two_ways_agree(df):
    d = df.drop_duplicates("event_id")
    r = d[(d["event_type"] == "restricted_entry") & (d["worker_id"] != "")].groupby("worker_id").size()
    assert list(r.sort_values(ascending=False, kind="stable").head(3).index) == list(r.nlargest(3).index) == ["W018", "W007", "W004"]
    table = r.rename("次數").reset_index()
    tb = table.sort_values(["次數", "worker_id"], ascending=[False, True]).head(3)
    assert tb["worker_id"].tolist() == ["W018", "W007", "W004"]
    ranked = r.rank(method="min", ascending=False)
    assert sorted(ranked[ranked <= 3].index) == ["W004", "W007", "W018", "W025"]
