import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import numpy as np, pandas as pd, pytest  # noqa: E402

LESSON = "08-missing-anomaly.md"
PANDAS2_DIFFS = []  # pandas 2.3.3 標準輸出逐字相同


def test_08_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d08():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def raw(d08):
    return d08["load_events"]()


@pytest.fixture(scope="module")
def events(raw):
    return raw.drop_duplicates("event_id")


def test_08_three_kinds_of_missing(d08, events):
    t = d08["missing_meaning"](events).set_index("情況")["列數"]
    assert t.to_dict() == {"違規、沒有處理": 262, "ppe_ok": 2322, "null": 231, "空字串": 364}
    # isna 只看得到 confidence（讀法保留空字串）
    assert events.isna().sum()[lambda s: s > 0].to_dict() == {"confidence": 231}
    assert set(events.loc[events["confidence"].isna(), "camera_id"]) == {"cam-08"}


def test_08_clean_audit_trail(d08, raw):
    cleaned, log, dropped = d08["clean"](raw)
    assert (len(raw), len(cleaned), len(dropped)) == (2838, 2818, 20)
    assert len(raw) - len(cleaned) == log["丟棄"].sum() == len(dropped)
    assert not cleaned["event_id"].duplicated().any()
    assert set(dropped["event_id"]) <= set(cleaned["event_id"])        # 丟的是重送，原件還在
    assert dropped["理由"].notna().all()
    assert log.loc[log["步驟"].str.startswith("cam-02"), "修改"].item() == 69
    assert cleaned["confidence"].max() <= 1
    # 注意：NaN != NaN 為 True，直接用 != 會把 cam-08 的 231 列算成「被修改」（69 + 231 = 300）
    changed = cleaned["confidence"].ne(cleaned["confidence_raw"]) & cleaned["confidence_raw"].notna()
    assert changed.sum() == 69 and set(cleaned.loc[changed, "camera_id"]) == {"cam-02"}
    assert cleaned["confidence"].isna().sum() == 231                   # 沒有補 0
    w41 = cleaned[(cleaned["worker_id"] == "W041") & cleaned["event_time"].str.startswith("2026-09-22")]
    assert (w41["event_type"] == "no_harness").sum() == 18             # 真的異常沒被清掉


def test_08_clean_keeps_first_arrival(d08, raw):
    cleaned, _, dropped = d08["clean"](raw)
    first = cleaned.set_index("event_id").loc[dropped["event_id"], "ingested_at"]
    assert (first.values < dropped["ingested_at"].values).all()


def test_08_clean_rejects_unknown_anomaly(d08, raw):
    bad = raw.copy()
    bad.loc[bad["camera_id"] == "cam-05", "confidence"] = 87.0
    with pytest.raises(ValueError, match="cam-02 以外"):
        d08["clean"](bad)
    bad = raw.copy()
    bad.loc[bad.index[0], "event_id"] = ""
    with pytest.raises(ValueError, match="event_id 有空值"):
        d08["clean"](bad)


def test_08_outlier_rules_remove_w041(d08, events):
    v = d08["is_violation"](events) & (events["worker_id"] != "")
    per_day = events[v].groupby([events["worker_id"], events["event_time"].str[:10]]).size()
    z, iqr = d08["zscore_outliers"](per_day), d08["iqr_outliers"](per_day)
    assert per_day[z].index.tolist() == [("W041", "2026-09-22")]
    assert iqr.sum() == 68 and per_day[iqr].sum() == 165 and iqr[("W041", "2026-09-22")]


def test_08_fill_zero_and_dropna_claims(d08, events):
    fixed = events.copy()
    bug = d08["percent_bug"](fixed)
    fixed.loc[bug, "confidence"] /= 100
    z4 = fixed[fixed["zone"] == "Z4"]
    assert round(z4["confidence"].mean(), 3) == 0.762 and round(z4["confidence"].fillna(0).mean(), 3) == 0.399
    assert round(fixed["confidence"].mean(), 3) == 0.774 and round(fixed["confidence"].fillna(0).mean(), 3) == 0.710
    kept = fixed.dropna(subset=["confidence"])
    assert len(kept) == 2587
    assert d08["is_violation"](kept).sum() == 452
    kz4 = kept[kept["zone"] == "Z4"]
    assert d08["is_violation"](kz4).sum() == 70 and (kz4["event_type"] == "no_harness").sum() == 56
    assert d08["is_violation"](z4).sum() == 114 and (z4["event_type"] == "no_harness").sum() == 86
    # NaN 比較：~(c >= 0.6) 把 NaN 算進低信心
    c = fixed["confidence"]
    assert (~(c >= 0.6)).sum() - (c < 0.6).sum() == 231


def test_08_naive_ai_pipeline(raw):
    """〈參考判讀〉：預設 read_json → drop_duplicates → dropna → IQR。"""
    x = pd.read_json(ROOT / "data" / "events" / "events.jsonl", lines=True)
    assert len(x.drop_duplicates()) == 2838                            # 整列去重一列都沒刪
    r = x.drop_duplicates().dropna()
    c = r["confidence"]
    q1, q3 = c.quantile([0.25, 0.75])
    r2 = r[c.between(q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1))]
    assert (len(r), len(r2)) == (212, 207)
    assert r2["event_id"].duplicated().sum() == 2
    w = r2[(r2["worker_id"] == "W041") & (r2["event_time"].dt.strftime("%m-%d") == "09-22")]
    assert len(w) == 14
    naive = raw.drop_duplicates("event_id").replace("", np.nan).dropna()
    assert len(naive) == 174


def test_08_review_table_claims():
    path = ROOT / "data" / "events" / "dashboard-export.csv"
    default = pd.read_csv(path)
    assert default["信心度"].isna().sum() == 63
    s = pd.read_csv(path, dtype=str, keep_default_na=False)
    assert s.isna().sum().sum() == 0 and (s["信心度"] == "N/A").sum() == 63 and (s["人員"] == "未辨識").sum() == 92
    with pytest.raises(ValueError, match="70%"):
        s["信心度"].astype(float)
    assert pd.to_numeric(s["信心度"].str.rstrip("%"), errors="coerce").isna().sum() == 63


def test_08_zscore_uses_mean_and_std(d08):
    s = pd.Series([1] * 9 + [10])          # mean 1.9、std 2.85：10 的 z = 2.85，不算異常
    assert not d08["zscore_outliers"](s).any()
    assert d08["zscore_outliers"](s, threshold=2.5).tolist() == [False] * 9 + [True]


def test_08_clean_rejects_bug_outside_known_days(d08, raw):
    """修正：clean() 也要檢查日期範圍，不只攝影機。"""
    assert d08["PERCENT_BUG_CAMERA"] == "cam-02" and d08["PERCENT_BUG_DAYS"] == ("2026-09-15", "2026-09-17")
    bad = raw.copy()
    i = bad.index[(bad["camera_id"] == "cam-02") & bad["event_time"].str.startswith("2026-09-22")][0]
    bad.loc[i, "confidence"] = 87.0                     # 同一支攝影機，但在已確認的三天以外
    with pytest.raises(ValueError, match="2026-09-15～2026-09-17 以外：\\['2026-09-22'\\]"):
        d08["clean"](bad)


def test_08_clean_log_dates_come_from_data(d08, raw):
    """修正：紀錄的日期由被修改的列算出，不是寫死「09-15～17」。"""
    _, log, _ = d08["clean"](raw)
    assert log.loc[1, "理由"] == "韌體 bug（09-15～09-17）；原值存 confidence_raw"
    narrow = raw.copy()
    on17 = narrow["event_time"].str.startswith("2026-09-17") & (narrow["confidence"] > 1)
    narrow.loc[on17, "confidence"] /= 100               # 只剩 09-15、09-16 有 bug
    _, log2, _ = d08["clean"](narrow)
    assert log2.loc[1, "理由"] == "韌體 bug（09-15～09-16）；原值存 confidence_raw"


def _run_main_on(tmp_path, events_df):
    """把（改過的）事件寫到暫存的 data/，以 __main__ 執行 Demo，回傳標準輸出。"""
    import io
    from contextlib import redirect_stdout
    d = tmp_path / "data" / "events"
    d.mkdir(parents=True)
    events_df.to_json(d / "events.jsonl", orient="records", lines=True, force_ascii=False)
    name, source, _ = load_demo(LESSON)
    out = io.StringIO()
    with redirect_stdout(out):
        exec(compile(source, name, "exec"), {"__name__": "__main__", "__file__": str(tmp_path / name)})
    return out.getvalue()


def test_08_printed_counts_are_computed(tmp_path, raw):
    """修正：「handled_at、worker_id 都是 0 個」「Z1 平均 6.148」改由資料計算；資料一變，輸出要跟著變。"""
    x = raw.copy().astype({"handled_at": object})
    x.loc[x.index[:5], "handled_at"] = None             # 5 個真正的 null
    x.loc[(x["camera_id"] == "cam-02") & (x["confidence"] > 1), "confidence"] = 50.0
    out = _run_main_on(tmp_path, x)
    assert "所以 handled_at 5 個、worker_id 0 個" in out
    z1 = x.drop_duplicates("event_id").query("zone == 'Z1'")["confidence"].mean()
    assert f"Z1 平均 {z1:.3f}：信心度不可能大於 1" in out and "6.148" not in out


def test_08_outlier_removal_actually_applies_rules(d08, events):
    """修正：「清掉後剩幾筆」要拿規則判定結果去濾，不是 worker_id != 'W041'。"""
    v = d08["is_violation"](events) & (events["worker_id"] != "")
    day = events["event_time"].str[:10]
    per_day = events[v].groupby([events["worker_id"], day]).size()
    cell = pd.Series(list(zip(events["worker_id"], day)), index=events.index)
    d22 = (events["event_type"] == "no_harness") & (day == "2026-09-22")
    left = {}
    for name, flag in [("z", d08["zscore_outliers"](per_day)), ("iqr", d08["iqr_outliers"](per_day))]:
        removed = v & cell.isin(set(per_day.index[flag]))
        left[name] = int((d22 & ~removed).sum())
    assert left == {"z": 6, "iqr": 2}
    out = run_main(LESSON)
    assert "z-score > 3  清掉  1 格、 18 筆事件；W041 09-22 被清掉：True；清完 09-22 no_harness 剩 6 筆" in out
    assert "IQR 1.5 倍    清掉 68 格、165 筆事件；W041 09-22 被清掉：True；清完 09-22 no_harness 剩 2 筆" in out


def test_08_dropna_check_is_meaningful():
    """修正：dropna 後檢查 handled_at.notna() 必然為 True；改印 ppe_ok 與 cam-08 的前後列數。"""
    out = run_main(LESSON)
    assert "2818 列 → 174 列；ppe_ok 2322 → 0 列；cam-08 231 → 0 列" in out
    assert "notna()).all()" not in load_demo(LESSON)[1]
