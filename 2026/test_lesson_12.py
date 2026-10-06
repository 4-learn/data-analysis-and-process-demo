import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "12-groupby-denominator.md"
PANDAS2_DIFFS = []  # Demo 標準輸出在 pandas 2.3.3 逐字相同


def test_12_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d12():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def loaded(d12):
    raw, ev = d12["read_events"]()
    return raw, ev, d12["read_roster"](), d12["violation_types"]()


def test_12_dedup_and_violation_definition(loaded):
    raw, ev, _, viol = loaded
    assert (len(raw), len(ev)) == (2838, 2818)
    assert ev["event_id"].is_unique
    assert viol == {"no_helmet", "no_harness", "restricted_entry"}
    assert int(ev["event_type"].isin(viol).sum()) == 496


def test_12_size_vs_count_on_cam08(loaded):
    _, ev, _, _ = loaded
    g = ev.groupby("camera_id")
    assert g.size()["cam-08"] == 231
    assert g["confidence"].count()["cam-08"] == 0
    # 空字串不是缺值：worker_id 的 count 等於 size
    assert (g["worker_id"].count() == g.size()).all()


def test_12_groupby_drops_nan_keys_silently(loaded):
    _, ev, _, _ = loaded
    assert ev.groupby("worker_id").size().sum() == 2818
    as_nan = ev.assign(worker_id=ev["worker_id"].replace("", np.nan))
    assert as_nan.groupby("worker_id").size().sum() == 2454
    assert as_nan.groupby("worker_id", dropna=False).size().sum() == 2818


def test_12_per_worker_contract(d12, loaded):
    _, ev, roster, viol = loaded
    t = d12["per_worker"](ev, roster, viol)
    assert len(t) == 60 and t.index.is_unique
    assert t["events"].sum() == 2454 and t["violations"].sum() == 419
    assert (t.loc["W023", "events"], t.loc["W041", "violations"]) == (52, 36)
    zero = t.index[t["events"] == 0].tolist()
    assert zero == [f"W0{n}" for n in range(53, 61)]
    assert t.loc[zero, "violation_rate"].isna().all()
    assert t.loc[zero, "violations"].eq(0).all()


def test_12_roster_reindex_without_dedup_double_counts(loaded):
    _, ev, roster, _ = loaded
    counts = ev[ev["worker_id"] != ""].groupby("worker_id").size()
    assert counts.reindex(roster["worker_id"], fill_value=0).sum() == 2454 + 52


def test_12_per_worker_rejects_stranger(d12, loaded):
    _, ev, roster, viol = loaded
    with pytest.raises(ValueError, match="名冊沒有的人"):
        d12["per_worker"](ev, roster[roster["worker_id"] != "W041"], viol)


def test_12_per_worker_rejects_blank_roster_id(d12, loaded):
    _, ev, roster, viol = loaded
    bad = roster.copy()
    bad.loc[0, "worker_id"] = ""
    with pytest.raises(ValueError, match="空的 worker_id"):
        d12["per_worker"](ev, bad, viol)


def test_12_workshop_zone_week(loaded):
    _, ev, _, viol = loaded
    ev = ev.assign(is_violation=ev["event_type"].isin(viol))
    t = pd.to_datetime(ev["event_time"], format="ISO8601").dt.tz_convert("Asia/Taipei")
    ev["week"] = t.dt.tz_localize(None).dt.to_period("W-SUN").astype(str)
    table = ev.groupby(["zone", "week"]).agg(events=("event_id", "size"),
                                             violations=("is_violation", "sum"))
    assert len(table) == 16 and table["events"].sum() == 2818
    top = (table["violations"] / table["events"]).idxmax()
    assert top == ("Z4", "2026-09-21/2026-09-27")
    assert tuple(table.loc[top]) == (130, 42)


def test_12_workshop_naive_ai_version():
    raw = pd.read_json(ROOT / "data" / "events" / "events.jsonl", lines=True)
    raw["v"] = raw["event_type"] != "ppe_ok"
    n = raw.groupby("worker_id").agg(total=("event_id", "count"), v=("v", "sum"))
    assert len(n) == 53 and n["total"].sum() == 2838 and "W053" not in n.index
    top = n.sort_values("v", ascending=False)
    assert top.index[0] == "" and tuple(top.iloc[0]) == (367, 77)
    assert tuple(n.loc["W041"]) == (67, 36)


def test_12_section7_header_follows_table(tmp_path):
    """第 7 段標題的列數要從表算出來；名冊少一人（W060），標題就該是 59 列，不是寫死的 60。"""
    import io
    import shutil
    from contextlib import redirect_stdout
    src, dst = ROOT / "data" / "events", tmp_path / "data" / "events"
    dst.mkdir(parents=True)
    for f in ("events.jsonl", "event-types.csv"):
        shutil.copy(src / f, dst / f)
    roster = (src / "workers.csv").read_text(encoding="utf-8").splitlines()
    (dst / "workers.csv").write_text("\n".join(r for r in roster if not r.startswith("W060,")) + "\n", encoding="utf-8")
    name, source, _ = load_demo(LESSON)
    out = io.StringIO()
    with redirect_stdout(out):
        exec(compile(source, name, "exec"), {"__name__": "__main__", "__file__": str(tmp_path / name)})
    out = out.getvalue()
    assert "== 7. 每人彙總表：59 列，分母寫在表上 ==" in out
    assert "原始 2838 列 → 每人 59 列" in out


def test_12_tie_order_is_roster_order(d12, loaded):
    """第五名並列（W007、W017 都是 16）：stable 排序照名冊順序，W007 在前。"""
    _, ev, roster, viol = loaded
    t = d12["per_worker"](ev, roster, viol).sort_values("violations", ascending=False, kind="stable")
    assert t.index[:6].tolist() == ["W041", "W029", "W044", "W018", "W007", "W017"]
    assert t.loc[["W007", "W017"], "violations"].tolist() == [16, 16]
