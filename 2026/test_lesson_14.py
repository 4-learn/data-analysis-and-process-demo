import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "14-merge-fanout.md"
PANDAS2_DIFFS = []  # Demo 標準輸出在 pandas 2.3.3 逐字相同


def test_14_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d14():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def src(d14):
    ev = d14["read_events"]()
    ev["violation"] = ev["event_type"].isin(d14["VIOLATIONS"])
    articles = pd.read_json(ROOT / "data" / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    return ev, d14["read_csv"]("workers.csv"), d14["read_csv"]("event-types.csv"), articles


def test_14_predicted_row_counts(src):
    ev, roster, _, _ = src
    got = {how: len(ev.merge(roster, on="worker_id", how=how)) for how in ("inner", "left", "outer")}
    assert got == {"inner": 2506, "left": 2870, "outer": 2878}
    with pytest.raises(pd.errors.MergeError, match="not a many-to-one"):
        ev.merge(roster, on="worker_id", how="left", validate="many_to_one")


def test_14_attach_roster_splits_w023_by_validity(d14, src):
    ev, roster, _, _ = src
    staff = d14["attach_roster"](ev, roster)
    assert len(staff) == 2818 and staff["event_id"].is_unique
    w23 = staff[staff["worker_id"] == "W023"]
    assert w23["contractor"].value_counts().to_dict() == {"乙鋼構": 29, "丙土木": 23}
    assert (w23.loc[w23["contractor"] == "丙土木", "event_time"] >= "2026-09-14").all()
    known = staff[staff["worker_id"] != ""]
    t = known.groupby("contractor").agg(events=("event_id", "size"), v=("violation", "sum"))
    assert t.to_dict("index") == {"甲營造": {"events": 817, "v": 105},
                                  "乙鋼構": {"events": 846, "v": 201},
                                  "丙土木": {"events": 791, "v": 113}}
    assert (staff["worker_id"] == "").sum() == 364 and staff.loc[staff["worker_id"] == "", "contractor"].isna().all()


def test_14_naive_inner_double_counts_w023(src):
    ev, roster, _, _ = src
    n = ev.merge(roster, on="worker_id")
    t = n.groupby("contractor").agg(events=("event_id", "size"), v=("violation", "sum"))
    assert t["events"].sum() == 2506 and t["v"].sum() == 424
    assert tuple(t.loc["乙鋼構"]) == (869, 204) and tuple(t.loc["丙土木"]) == (820, 115)


@pytest.mark.parametrize("breakage, message", [
    ("overlap", r"有效期間重疊：\['W023'\]"),
    ("missing_worker", "67 筆已辨識事件對不到名冊"),
    ("blank_from", "空的 valid_from"),
])
def test_14_attach_roster_rejects(d14, src, breakage, message):
    ev, roster, _, _ = src
    r = roster.copy()
    if breakage == "overlap":
        r.loc[(r["worker_id"] == "W023") & (r["valid_to"] != ""), "valid_to"] = "2026-09-20"
    elif breakage == "missing_worker":
        r = r[r["worker_id"] != "W041"]
    else:
        r.loc[0, "valid_from"] = ""
    with pytest.raises(ValueError, match=message):
        d14["attach_roster"](ev, r)


def test_14_utc_dates_break_validity(d14, src):
    ev, roster, _, _ = src
    utc = ev.assign(event_time=pd.to_datetime(ev["event_time"], format="ISO8601")
                    .dt.tz_convert("UTC").dt.strftime("%Y-%m-%dT%H:%M:%S"))
    with pytest.raises(ValueError, match="4 筆已辨識事件對不到名冊"):
        d14["attach_roster"](utc, roster)


def test_14_articles_need_pcode_and_slug(d14, src):
    ev, _, types, articles = src
    assert len(ev.merge(types, on="event_type").merge(articles, on="slug")) == 2374
    full = d14["attach_articles"](ev, types, articles)
    assert len(full) == 2818
    v = full[full["violation"]]
    assert v["content"].notna().all() and set(v["law_name"]) == {"營造安全衛生設施標準"}
    assert v.groupby("event_type")["article_no"].unique().map(list).to_dict() == {
        "no_harness": ["第 19 條"], "no_helmet": ["第 11-1 條"], "restricted_entry": ["第 24 條"]}
    assert full.loc[full["event_type"] == "ppe_ok", "content"].isna().sum() == 2322


def test_14_attach_articles_rejects(d14, src):
    ev, _, types, articles = src
    with pytest.raises(ValueError, match="違規事件找不到法條"):
        d14["attach_articles"](ev, types, articles[~((articles["pcode"] == "N0060014") & (articles["slug"] == "19"))])
    bad = ev.copy()
    bad.loc[0, "event_type"] = "no_vest"
    with pytest.raises(ValueError, match=r"事件類型不在對照表：\['no_vest'\]"):
        d14["attach_articles"](bad, types, articles)


def test_14_concat_vs_merge_with_dashboard(d14, src):
    ev, _, types, _ = src
    dash = pd.read_csv(ROOT / "data" / "events" / "dashboard-export.csv", dtype=str,
                       keep_default_na=False, encoding="utf-8-sig")
    week1 = ev[ev["event_time"] < "2026-09-07"].drop(columns="violation")
    assert pd.concat([week1, dash], ignore_index=True).shape == (1384, 19)
    aligned = d14["dashboard_as_events"](dash, types)
    assert aligned.notna().drop(columns="confidence").all().all()
    assert aligned["confidence"].isna().sum() == 63
    check = week1.merge(aligned, on="event_id", how="outer", validate="one_to_one",
                        indicator=True, suffixes=("", "_dash"))
    assert (check["_merge"] == "both").all() and len(check) == 692
    assert (check["worker_id"] == check["worker_id_dash"]).all()
    assert ((check["confidence"] - check["confidence_dash"]).abs() <= 0.005).sum() == 692 - 63


def test_14_predict_rows_comes_from_key_counts(d14, src):
    """預測不是抄實際列數：換一份名冊（W023 變三列、W041 變兩列），預測要跟著變且仍等於實際。"""
    ev, roster, _, _ = src
    predict = d14["predict_rows"]
    assert {h: predict(ev, roster, "worker_id", h) for h in ("inner", "left", "outer")} == \
        {"inner": 2506, "left": 2870, "outer": 2878}
    extra = pd.concat([roster[roster["worker_id"] == "W023"].head(1), roster[roster["worker_id"] == "W041"]])
    bigger = pd.concat([roster, extra], ignore_index=True)
    for how in ("inner", "left", "outer", "right"):
        assert predict(ev, bigger, "worker_id", how) == len(ev.merge(bigger, on="worker_id", how=how)), how
    assert predict(ev, bigger, "worker_id", "left") == 2870 + 52 + 67


def test_14_checked_merge_records_prediction_and_stops_on_mismatch(d14, src, monkeypatch):
    ev, roster, _, _ = src
    log = []
    d14["checked_merge"](log, "naive", ev, roster, "r", on="worker_id", how="left")
    assert log == [("naive", 2818, 2870, 2870, "r")]
    # 預測算錯（例如忘了 fan-out）就要停，不能靜靜把實際列數記成預測
    monkeypatch.setitem(d14, "predict_rows", lambda *a: len(a[0]))
    with pytest.raises(ValueError, match="預測 2818 列，實際 2870 列"):
        d14["checked_merge"]([], "naive", ev, roster, "r", on="worker_id", how="left")


def test_14_report_reasons_are_computed(d14):
    """第七段原因欄的數字要由資料算出：Demo 原始碼裡不能有寫死的 52／364／2322。"""
    main = load_demo(LESSON)[1].split('if __name__ == "__main__":')[1]
    for literal in ('"W023 名冊兩列', "未辨識 364", "ppe_ok 2322", "19 對 9 部", "7＋12"):
        assert literal not in main, literal
    out = run_main(LESSON)
    assert "預測與實際全部一致：True" in out
    assert "W023 名冊 2 列：52 筆事件被複製" in out and "ppe_ok 2322 筆被 inner 丟掉" in out
