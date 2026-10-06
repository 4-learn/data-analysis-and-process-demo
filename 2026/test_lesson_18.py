import sys
import io
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "18-end-to-end.md"
PANDAS2_DIFFS = []  # 2.3.3 實測逐字相同（dtype 字串差異 Demo 已避開）
FINGERPRINT = "deea741b228d613d"


def test_18_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert len(blocks) == 6
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d18():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def lines(d18):
    return (d18["DATA"] / "events.jsonl").read_text(encoding="utf-8").splitlines()


def test_18_fingerprint_stable_and_order_free(d18, lines):
    path = d18["DATA"] / "events.jsonl"
    fp = d18["fingerprint"]
    assert fp(d18["run"](path)[0]) == FINGERPRINT
    assert fp(d18["run"](io.StringIO("\n".join(reversed(lines)) + "\n"))[0]) == FINGERPRINT
    # 換成同一時刻的 UTC 寫法：意義相同，指紋不變
    assert fp(d18["run"](d18["broken"](lines, 5, event_time="2026-08-30T23:54:26Z"))[0]) == FINGERPRINT


def test_18_summary_contract(d18):
    text, tokens, table, audit = d18["run"](d18["DATA"] / "events.jsonl")
    assert "\\u" not in text and tokens == 640 and tokens <= d18["BUDGET"]
    rows = [json.loads(x) for x in text.splitlines()]
    assert [r["kind"] for r in rows] == ["top_worker"] * 3 + ["unidentified", "trend", "anomaly", "data_note", "data_note"]
    assert [r["item"] for r in rows[:3]] == ["W041", "W029", "W044"]
    # 每一列的 key 都能追回 n 筆
    known, violation = d18["read_event_types"]()
    ev, _ = d18["clean"](d18["read_events"](d18["DATA"] / "events.jsonl"))
    ev = d18["validate"](ev, known, violation)
    for r in rows:
        assert len(ev.query(r["key"])) == r["n"] > 0
    assert table["violations"].sum() == ev["is_violation"].sum() == 496
    assert [(a["step"], a["rows"], a["cameras"]) for a in audit] == [("去重", 20, ["cam-05"]), ("修正", 69, ["cam-02"])]


def test_18_weekly_table(d18):
    table = d18["run"](d18["DATA"] / "events.jsonl")[2]
    assert len(table) == 212 and table["who"].nunique() == 53
    w41 = table[table["who"] == "W041"].set_index("week")["max_per_day"]
    assert w41.to_dict() == {"2026-08-31": 1, "2026-09-07": 2, "2026-09-14": 2, "2026-09-21": 18}
    unk = table[table["who"] == "(未辨識)"]
    assert unk["violations"].sum() == 77 and unk["max_per_day"].max() == 7


BAD = [
    ("少了時區", dict(event_time="2026-08-31T07:30:00"), "沒有時區"),
    ("未知 event_type", dict(event_type="no_vest"), "未知 event_type"),
    ("缺鍵", dict(worker_id=None), "worker_id 有空值"),
    ("worker_id 是數字", dict(worker_id=41), "worker_id 不是字串"),
    ("confidence 字串", dict(confidence="0.8"), "confidence 不是數字"),
    ("confidence 負值", dict(confidence=-0.3), "超出 0–1"),
    ("ingested_at 沒時區", dict(ingested_at="2026-08-31T07:54:40"), "ingested_at 沒有時區"),
]


@pytest.mark.parametrize("label,change,msg", BAD, ids=[b[0] for b in BAD])
def test_18_bad_data_blocked(d18, lines, label, change, msg):
    with pytest.raises(d18["PipelineError"], match=msg):
        d18["run"](d18["broken"](lines, 5, **change))


def test_18_conflict_vs_resend(d18, lines):
    first = json.loads(lines[0])["event_id"]
    with pytest.raises(d18["PipelineError"], match="不唯一"):
        d18["run"](d18["broken"](lines, 5, event_id=first))
    # 完全相同的重送：放行，audit 多 1 筆，只有補傳那列的說明改變
    text, _, _, audit = d18["run"](io.StringIO("\n".join(lines + [lines[5]]) + "\n"))
    assert audit[0]["rows"] == 21 and d18["fingerprint"](text) == "78398ed17d238166"
    base = d18["run"](d18["DATA"] / "events.jsonl")[0].splitlines()
    assert sum(a != b for a, b in zip(base, text.splitlines())) == 1


def test_18_missing_column_and_budget(d18, lines):
    stripped = "\n".join(json.dumps({k: v for k, v in json.loads(x).items() if k != "zone"}, ensure_ascii=False) for x in lines)
    with pytest.raises(d18["PipelineError"], match=r"缺少欄位 \['zone'\]"):
        d18["run"](io.StringIO(stripped + "\n"))
    with pytest.raises(d18["PipelineError"], match="超過預算 500"):
        d18["run"](d18["DATA"] / "events.jsonl", budget=500)


def test_18_extra_checks_hook(d18, lines):
    def no_z9(ev):
        if (ev["zone"] == "Z9").any():
            raise d18["PipelineError"]("Z9")
    assert d18["fingerprint"](d18["run"](d18["DATA"] / "events.jsonl", checks=[no_z9])[0]) == FINGERPRINT
    with pytest.raises(d18["PipelineError"], match="Z9"):
        d18["run"](d18["broken"](lines, 5, zone="Z9"), checks=[no_z9])


def test_18_small_batches_do_not_crash(d18, lines):
    """只有 cam-08 一天：confidence 整欄 null（pandas 3 讀成 object）、只有一週、沒有未辨識。"""
    sub = [x for x in lines if '"cam-08"' in x and "2026-08-31" in x]
    text = d18["run"](io.StringIO("\n".join(sub) + "\n"))[0]
    assert [json.loads(x)["kind"] for x in text.splitlines()] == ["top_worker", "top_worker"]


def test_18_naive_dedupe_drops_conflict_silently(d18, lines):
    """〈參考判讀〉：AI 的 drop_duplicates('event_id') 會安靜丟掉衝突的那筆。"""
    first = json.loads(lines[0])["event_id"]
    df = d18["read_events"](d18["broken"](lines, 5, event_id=first))
    assert len(df.drop_duplicates("event_id")) == 2817


def test_18_ties_ranked_by_worker_id(d18):
    """同分時名次由工號決定，不受輸入順序影響（kind="stable"）。"""
    ids = [f"W{i:03d}" for i in range(30, 0, -1)]          # 倒序輸入、每人 1 筆違規
    ev = pd.DataFrame({
        "worker_id": ids, "is_violation": True, "week": "2026-09-21", "date": "2026-09-22",
        "event_time": "2026-09-22T09:00:00+08:00", "event_type": "no_helmet", "conf_fixed": False, "late": False,
    })
    summary = d18["condense"](ev, d18["weekly"](ev), [])
    assert summary["item"].tolist()[:3] == ["W001", "W002", "W003"]


def test_18_dedupe_keeps_first_arrival_regardless_of_input_order():
    """audit 說「留最先到達的一筆」：倒序輸入也必須成立。"""
    ns = load_demo(LESSON)[2]
    raw = pd.read_json(ROOT / "data" / "events" / "events.jsonl", lines=True, dtype=False, convert_dates=False)
    for frame in (raw, raw.iloc[::-1]):
        ev, _ = ns["clean"](frame)
        kept = ev.set_index("event_id")["ingested_at"]
        first = raw.groupby("event_id")["ingested_at"].min()
        assert (kept.sort_index() == first.loc[kept.index].sort_index()).all()
