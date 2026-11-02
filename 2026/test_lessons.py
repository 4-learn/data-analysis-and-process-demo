"""測試講義內嵌的 Demo——擷取講義裡的同一份程式碼執行，不維護另一份副本。

    python3 -m pytest -q          # 本檔＋各節的 test_lesson_NN.py

本檔放共用 helper、02／03／09／16 的測試，以及「每篇講義恰好一個 Demo、能以 python3 直接執行」的全節檢查。
其餘各節的測試在 test_lesson_NN.py（各自 import 本檔的 helper）。

需要 pandas、tabulate、pytest（版本見 README.md）。
"""

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent
DEMO = re.compile(r"<!-- demo: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)


def locate_excerpt(code, snippet):
    """節錄在完整 Demo 中的位置：(起始行號（0 起）, 縮排)。主程式那段在 Demo 裡縮 4 格，講義節錄時去掉縮排。
    找不到回傳 None。"""
    for indent in ("", "    ", "        "):
        shifted = "\n".join(indent + line if line.strip() else line for line in snippet.split("\n"))
        i = code.find(shifted)
        if i >= 0 and (i == 0 or code[i - 1] == "\n"):
            return code[:i].count("\n"), indent
    return None


def load_demo(lesson, file_dir=ROOT):
    """回傳 (檔名, 原始碼, namespace)。file_dir 讓測試能把 Demo 指到暫存資料夾。"""
    blocks = DEMO.findall((ROOT / lesson).read_text(encoding="utf-8"))
    assert len(blocks) == 1, f"{lesson} 應恰好有一個 demo 區塊，實際 {len(blocks)}"
    name, source = blocks[0]
    ns = {"__name__": "lesson_under_test", "__file__": str(file_dir / name)}
    exec(compile(source, name, "exec"), ns)
    return name, source, ns


def run_main(lesson):
    name, source, _ = load_demo(lesson)
    out = io.StringIO()
    with redirect_stdout(out):
        exec(compile(source, name, "exec"), {"__name__": "__main__", "__file__": str(ROOT / name)})
    return out.getvalue()


def pasted_blocks(lesson):
    """講義正文（Workshop 之前）貼的輸出區塊。Workshop 起手式的輸出另由 test_workshop_starters_run 檢查。"""
    text = (ROOT / lesson).read_text(encoding="utf-8")
    body = text.split("\n## Workshop", 1)[0]
    return re.findall(r"```text\n(.*?)\n```", body, re.S)


# pandas 2.x 與講義（pandas 3.0 實測）唯一允許的差異：字串欄顯示 object、日期解析度 ns。
# 每一條都寫在該講義的〈教師紀錄〉裡；不在這張表上的差異一律算失敗。
PANDAS2_DIFFS = {
    "03-read-files.md": [("slug=object, chapter=object", "slug=str, chapter=str"),
                         ("合計 186 列；slug dtype=object", "合計 186 列；slug dtype=str")],
    "04-read-jsonl.md": [("fetched_at=datetime64[ns, UTC]", "fetched_at=datetime64[us, UTC]"),
                         ("21 列；slug=object；", "21 列；slug=str；")],
}
# Workshop 起手式在 pandas 2.3.3 的顯示差異（同樣只有字串欄 object、日期解析度 ns）
WORKSHOP_PANDAS2_DIFFS = {
    "04_workshop_all_laws.py": [("slug 的型別：object", "slug 的型別：str")],
    "12_workshop_daily_zone.py": [("datetime64[ns, Asia/Taipei]", "datetime64[us, Asia/Taipei]")],
}


def assert_pasted_output(lesson):
    """講義裡貼的每個輸出區塊（以 `== ` 或 `全部 `、`v1 ` 開頭者）都必須逐字出現在實際輸出中。"""
    out = run_main(lesson)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS.get(lesson, []):
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(lesson) if b.startswith(("== ", "全部 ", "v1 "))]
    assert blocks, f"{lesson} 沒有可比對的輸出區塊"
    for block in blocks:
        assert block in out, f"{lesson} 貼的輸出與實際不符：\n{block[:300]}"


# ---------------------------------------------------------------- fixtures

def test_fixtures_match_manifest():
    manifest = json.loads((ROOT / "data" / "MANIFEST.json").read_text(encoding="utf-8"))
    for rel, meta in manifest["files"].items():
        data = (ROOT / "data" / rel).read_bytes()
        assert len(data) == meta["bytes"], rel
        assert hashlib.sha256(data).hexdigest() == meta["sha256"], rel


def test_event_fixtures_match_manifest_and_rebuild(tmp_path):
    """合成事件：檔案與 MANIFEST 一致，且以目前的 Python 重建位元組相同。"""
    import shutil
    import subprocess
    import sys
    manifest = json.loads((ROOT / "data" / "events" / "MANIFEST.json").read_text(encoding="utf-8"))
    for name, meta in manifest["files"].items():
        data = (ROOT / "data" / "events" / name).read_bytes()
        assert len(data) == meta["bytes"] and hashlib.sha256(data).hexdigest() == meta["sha256"], name
    (tmp_path / "tools").mkdir()
    shutil.copy(ROOT / "tools" / "build_events.py", tmp_path / "tools")
    subprocess.run([sys.executable, str(tmp_path / "tools" / "build_events.py")], check=True, capture_output=True)
    for name in manifest["files"]:
        assert (tmp_path / "data" / "events" / name).read_bytes() == (ROOT / "data" / "events" / name).read_bytes(), name


def test_articles_contract():
    df = pd.read_json(ROOT / "data" / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    assert len(df) == 749 and df["pcode"].nunique() == 9
    for col in ("source_url", "fetched_at", "content_hash", "source_version"):
        assert df[col].ne("").all(), col
    assert not df.duplicated(["pcode", "slug"]).any()
    recomputed = df["content"].map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    assert (recomputed == df["content_hash"]).all()


# ---------------------------------------------------------------- 02

@pytest.fixture(scope="module")
def d03():
    return load_demo("03-read-files.md")[2]


def test_03_output_matches_lesson():
    assert_pasted_output("03-read-files.md")


def test_03_naive_read_fails_loudly_only_on_big5(d03):
    df, note = d03["naive_read"](d03["DATA"] / "labor-disputes.csv")
    assert df is None and note.startswith("UnicodeDecodeError")
    df, _ = d03["naive_read"](d03["DATA"] / "mass-layoff.csv")
    assert df["slug"].dtype == "int64" and df["chapter"].dtype == "float64"


def test_03_read_folder_contract(d03):
    df = d03["read_folder"](d03["DATA"])
    assert len(df) == 186
    assert df["slug"].map(type).eq(str).all()
    assert (df["slug"] == "1").sum() == 3
    assert df["modified_date"].dt.year.between(2015, 2024).all()
    assert set(df["read_encoding"]) == {"utf-8-sig", "cp950"}
    assert (df["chapter"] == "").sum() == 21 and df["chapter"].notna().all()


def _copy_exports(tmp_path):
    folder = tmp_path / "exports"
    shutil.copytree(ROOT / "data" / "03-exports", folder)
    return folder


def test_03_duplicate_file_is_rejected(d03, tmp_path):
    folder = _copy_exports(tmp_path)
    shutil.copy(folder / "mass-layoff.csv", folder / "extra.csv")
    with pytest.raises(ValueError, match="重複 21 筆"):
        d03["read_folder"](folder)


def test_03_unknown_encoding_is_rejected(d03, tmp_path):
    bad = tmp_path / "utf16.csv"
    bad.write_text("pcode\nN1\n", encoding="utf-16")
    with pytest.raises(ValueError, match="請先問資料提供者"):
        d03["detect_encoding"](bad)


def test_03_missing_column_is_rejected(d03, tmp_path):
    bad = tmp_path / "x.csv"
    bad.write_text("pcode,slug\nN1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少欄位"):
        d03["read_export"](bad)


def test_03_bad_date_raises_not_1970(d03, tmp_path):
    src = (ROOT / "data" / "03-exports" / "mass-layoff.csv").read_text(encoding="utf-8")
    bad = tmp_path / "x.csv"
    bad.write_text(src.replace("20150701", "2015/07/01", 1), encoding="utf-8")
    with pytest.raises(ValueError):
        d03["read_export"](bad)


def test_03_empty_folder(d03, tmp_path):
    with pytest.raises(FileNotFoundError):
        d03["read_folder"](tmp_path)


# ---------------------------------------------------------------- 03

@pytest.fixture(scope="module")
def d04():
    return load_demo("04-read-jsonl.md")[2]


@pytest.mark.filterwarnings("ignore:The default 'epoch' date format")  # 講義第二段刻意示範的警告
def test_04_output_matches_lesson():
    assert_pasted_output("04-read-jsonl.md")


def test_04_api_fixture_is_byte_identical_to_site_format(d04):
    """04-api 的頁面必須是練習站 build.py 的序列化方式：indent=1、ensure_ascii=False、結尾換行。"""
    for page in sorted(d04["API"].glob("*.json")):
        raw = page.read_text(encoding="utf-8")
        assert raw == json.dumps(json.loads(raw), ensure_ascii=False, indent=1) + "\n", page.name


def test_04_read_jsonl_keeps_values_verbatim(d04):
    df = d04["read_jsonl"](d04["CRAWL"])
    original = [json.loads(x) for x in d04["CRAWL"].read_text(encoding="utf-8").splitlines()]
    assert df.to_dict("records") == original


def test_04_full_corpus_counts(d04):
    df = d04["read_jsonl"](ROOT / "data" / "articles.jsonl")
    counts = df.groupby("law_name", sort=False).size()
    assert counts.sum() == 749 and counts["大量解僱勞工保護法"] == 21 and counts["營造安全衛生設施標準"] == 189
    assert df.apply(lambda r: r.source_url.endswith(f"/{r.pcode}/articles/{r.slug}.html"), axis=1).all()


def _crawl_df(d04):
    return pd.read_json(d04["CRAWL"], lines=True, dtype=False, convert_dates=False)


@pytest.mark.parametrize("breakage, message", [
    (lambda df: df.drop(columns="source_url"), "缺少來源欄位"),
    (lambda df: df.assign(source_version=""), "空值"),
    (lambda df: df.assign(fetched_at="2026-10-05 12:05:23"), "沒有時區"),
    (lambda df: df.assign(content=df["content"] + "。"), "content_hash"),
])
def test_04_provenance_check_rejects(d04, breakage, message):
    with pytest.raises(ValueError, match=message):
        d04["check_provenance"](breakage(_crawl_df(d04)))


def test_04_flatten_api_counts_and_loops(d04, tmp_path):
    api = d04["flatten_api"](d04["API"])
    assert len(api) == 21 and api["slug"].tolist() == [str(i) for i in range(1, 22)]
    assert set(api["pcode"]) == {"N0020012"}
    # 只有第 1 頁：total=21 但只攤平 20 條，必須失敗
    one = json.loads((d04["API"] / "page-1.json").read_text(encoding="utf-8"))
    one["next"] = None
    (tmp_path / "page-1.json").write_text(json.dumps(one, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="total=21"):
        d04["flatten_api"](tmp_path)
    # next 指回自己：必須偵測迴圈，不能無窮迴圈
    one["next"] = "page-1.json"
    (tmp_path / "page-1.json").write_text(json.dumps(one, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="迴圈"):
        d04["flatten_api"](tmp_path)


# ---------------------------------------------------------------- 09

@pytest.fixture(scope="module")
def d10():
    return load_demo("10-validate-idempotent.md")[2]


@pytest.fixture(scope="module")
def batches(d10):
    return (d10["read_batch"](d10["DATA"] / "articles.jsonl"),
            d10["read_batch"](d10["DATA"] / "10-batches" / "v2-changes.jsonl"))


def test_10_output_matches_lesson():
    assert_pasted_output("10-validate-idempotent.md")


def test_10_idempotent_under_replay_and_reorder(d10, batches):
    v1, v2 = batches
    cur, _ = d10["apply_batch"](v1, v2)
    fp = d10["fingerprint"](cur)
    assert d10["fingerprint"](d10["apply_batch"](cur, v2)[0]) == fp
    assert d10["fingerprint"](d10["apply_batch"](cur, v1)[0]) == fp
    # 列的順序不影響結果
    shuffled = v2.sample(frac=1, random_state=0)
    assert d10["fingerprint"](d10["apply_batch"](v1, shuffled)[0]) == fp
    # 同一刻、不同時區寫法：視為同一時間點，略過
    same_instant = v2.assign(fetched_at="2026-10-12T12:00:00+08:00")
    _, report = d10["apply_batch"](cur, same_instant)
    assert report == {"新增": 0, "更新": 0, "略過（不比現有新）": 5}


def test_10_newer_means_time_not_string(d10, batches):
    """較舊的時刻、但字串比較大（+08:00）的舊內容晚到：必須略過，不能把 v2 修正蓋回去。"""
    v1, v2 = batches
    cur, _ = d10["apply_batch"](v1, v2)
    stale = v1[(v1["pcode"] == "N0030001") & (v1["slug"] == "24")].assign(
        fetched_at="2026-10-12T11:00:00+08:00")      # = 03:00 UTC，早於 v2 的 04:00 UTC
    after, report = d10["apply_batch"](cur, stale)
    assert report["略過（不比現有新）"] == 1
    assert d10["fingerprint"](after) == d10["fingerprint"](cur)


def test_10_v2_content_matches_upstream_modifications(d10, batches):
    v1, v2 = batches
    cur, report = d10["apply_batch"](v1, v2)
    assert report == {"新增": 1, "更新": 4, "略過（不比現有新）": 0}
    assert cur.loc[cur["source_version"] == "v2", "slug"].tolist() == ["24", "38", "86-1", "15", "6"]


def _set(df, col, value, row=0):
    df = df.copy()
    df.loc[df.index[row], col] = value
    return df


@pytest.mark.parametrize("breakage, message", [
    (lambda d: _set(d, "slug", "1.0"), "slug 格式"),
    (lambda d: _set(d, "source_version", "V2"), "白名單"),
    (lambda d: _set(d, "article_no", "第 24 條", row=1), "article_no 與 slug 不一致"),
    (lambda d: _set(d, "pcode", "n0030001"), "pcode 格式"),
    (lambda d: _set(d, "law_name", ""), "必填欄位有空值"),
    (lambda d: _set(d, "fetched_at", "2026-10-12 12:00:00"), "沒有時區"),
    (lambda d: _set(d, "content", "改過"), "content_hash"),
    (lambda d: pd.concat([d, d.tail(1)]), "業務鍵重複"),
    (lambda d: d.drop(columns="content_hash"), "缺少欄位"),
])
def test_10_validate_rejects(d10, batches, breakage, message):
    with pytest.raises(d10["ValidationError"], match=message):
        d10["validate"](breakage(batches[1]))


def test_10_validation_error_is_not_a_warning(d10):
    assert issubclass(d10["ValidationError"], ValueError)


def test_10_conflict_at_same_instant_stops(d10, batches):
    v1, _ = batches
    row = v1.head(1).copy()
    row["content"] = "同一時間點的另一種內容"
    row["content_hash"] = d10["sha"](row["content"].iloc[0])
    with pytest.raises(d10["ValidationError"], match="同一時間點有兩種內容"):
        d10["apply_batch"](v1, row)


def test_10_workshop_claims(d10, batches):
    """講義〈參考判讀〉的宣稱：4 不該被擋（只是較舊）、5 擋不下來（驗證的界線）。"""
    v1, v2 = batches
    older = _set(v2, "fetched_at", "2026-01-01T00:00:00+00:00")
    _, report = d10["apply_batch"](v1, older)
    assert report["略過（不比現有新）"] == 1
    deleted = _set(_set(v2, "content", "（刪除）"), "content_hash", d10["sha"]("（刪除）"))
    d10["apply_batch"](v1, deleted)  # 不拋例外
    assert (v1["content"] == "（刪除）").sum() == 9


def test_10_naive_keep_last_is_not_order_safe(d10, batches):
    """講義宣稱：AI 常見的 keep='last' 同批重跑看似冪等，但舊資料晚到會翻盤。"""
    v1, v2 = batches
    key, fp = d10["KEY"], d10["fingerprint"]
    cur = pd.concat([v1, v2]).drop_duplicates(key, keep="last")
    assert fp(pd.concat([cur, v2]).drop_duplicates(key, keep="last")) == fp(cur)
    assert fp(pd.concat([cur, v1]).drop_duplicates(key, keep="last")) != fp(cur)


def test_10_reconcile_finds_only_the_deletion(d10, batches):
    v1, v2 = batches
    cur, _ = d10["apply_batch"](v1, v2)
    diff = d10["reconcile"](cur, d10["DATA"] / "10-batches" / "v2-laws.json")
    assert diff.to_dict("index") == {"N0020012": {"來源條文數": 20, "本地條文數": 21}}
    # 若上游補送刪除後的狀態，對帳應為空
    fixed = cur[~((cur["pcode"] == "N0020012") & (cur["slug"] == "21"))]
    assert d10["reconcile"](fixed, d10["DATA"] / "10-batches" / "v2-laws.json").empty


# ---------------------------------------------------------------- 16

@pytest.fixture(scope="module")
def d17():
    return load_demo("17-context-budget.md")[2]


@pytest.fixture(scope="module")
def hits(d17):
    df = pd.read_json(d17["DATA"], lines=True, dtype=False, convert_dates=False)
    h = df[df["content"].str.contains("墜落", regex=False)].copy()
    h["hits"] = h["content"].str.count("墜落")
    return h


def test_17_output_matches_lesson():
    assert_pasted_output("17-context-budget.md")


def test_17_tokenizer_fixture_is_llm_course_copy():
    """data/17-tokenizer/ 是 LLM 課 data/tokenizer-fixtures.json 的逐位元組複本（本機原稿目錄才比對）。"""
    llm = ROOT.parent / "llm" / "data" / "tokenizer-fixtures.json"
    if not llm.exists():
        pytest.skip("不在 swarm 原稿目錄")
    assert (ROOT / "data" / "17-tokenizer" / "tokenizer-fixtures.json").read_bytes() == llm.read_bytes()


def test_17_estimator_is_conservative_vs_teacher_fixture(d17):
    fx = json.loads((ROOT / "data" / "17-tokenizer" / "tokenizer-fixtures.json").read_text(encoding="utf-8"))
    under = {m: [c["id"] for c in fx["cases"] if d17["estimate_tokens"](c["text"]) < c["counts"][m]]
             for m in fx["tokenizers"]}
    # 講義宣稱：Qwen 0/8；bge 只在兩個極短詞低估
    assert under["Qwen2.5-0.5B-Instruct"] == []
    assert sorted(under["bge-small-zh-v1.5"]) == ["zh_unseen", "zh_word"]


def test_17_fit_budget_respects_budget_and_keeps_whole_rows(d17, hits):
    for budget in (1500, 3000, 6000):
        text, kept, dropped = d17["fit_budget"](hits, budget, d17["KEEP"], rank_by="hits")
        assert d17["estimate_tokens"](text) <= budget
        assert len(kept) + len(dropped) == len(hits)
        assert set(kept.index).isdisjoint(dropped.index)
        sent = [json.loads(line) for line in text.splitlines()]
        assert [r["content"] for r in sent] == kept["content"].tolist()  # 整條送出，沒有截斷
        assert all(r["source_url"] for r in sent)
        assert "\\u" not in text


def test_17_fit_budget_is_greedy_prefix(d17, hits):
    """第 kept+1 條放進去就會超過預算——不是隨便停在某處。"""
    text, kept, dropped = d17["fit_budget"](hits, 3000, d17["KEEP"], rank_by="hits")
    if len(dropped):
        nxt = pd.concat([kept, dropped.head(1)])[d17["KEEP"]]
        assert d17["estimate_tokens"](d17["serialize"](nxt, "jsonl")) > 3000


def test_17_injectable_counter(d17, hits):
    text, kept, _ = d17["fit_budget"](hits, 3, d17["KEEP"], rank_by="hits", count=lambda s: s.count("\n"))
    assert len(kept) == 3


def test_17_errors(d17, hits):
    with pytest.raises(ValueError, match="連一條都放不下"):
        d17["fit_budget"](hits, 10, d17["KEEP"], rank_by="hits")
    with pytest.raises(ValueError, match="缺少欄位"):
        d17["fit_budget"](hits, 3000, ["nope"], rank_by="hits")
    with pytest.raises(ValueError, match="未知格式"):
        d17["serialize"](hits, "yaml")


def test_17_markdown_breaks_rows(d17, hits):
    md = d17["serialize"](hits.drop(columns="hits"), "markdown")
    assert md.count("\n") + 1 == 171  # 講義宣稱 171 行
    assert md.count("\n") + 1 > len(hits) + 2


# ---------------------------------------------------------------- CLI

@pytest.mark.parametrize("lesson", sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md")))
def test_demo_runs_as_script(lesson, tmp_path):
    """講義說可以 `python3 檔名` 直接執行：把 Demo 原樣寫成檔案，用子行程跑。"""
    name, source, _ = load_demo(lesson)
    script = tmp_path / name
    script.write_text(source + "\n", encoding="utf-8")
    (tmp_path / "data").symlink_to(ROOT / "data")
    r = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr


EXCERPT = re.compile(r"<!-- 節錄: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)
WORKSHOP = re.compile(r"<!-- workshop: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)


@pytest.mark.parametrize("lesson", sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md")))
def test_walkthrough_excerpts_are_verbatim(lesson):
    """〈程式逐段解說〉的每個節錄都必須逐字出現在同一篇的完整 Demo 裡，改了 Demo 就會在這裡失敗。"""
    text = (ROOT / lesson).read_text(encoding="utf-8")
    excerpts = EXCERPT.findall(text)
    if not excerpts:
        pytest.skip("本節沒有逐段解說")
    (name, code), = DEMO.findall(text)
    for file, snippet in excerpts:
        assert file == name, f"節錄標的 {file} 與 Demo {name} 不同"
        assert locate_excerpt(code, snippet) is not None, f"{lesson} 節錄與 Demo 不一致：\n{snippet[:200]}"


STEPWISE = re.compile(r"<!-- 格式：每段一張圖 -->")


@pytest.mark.parametrize("lesson", sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md")))
def test_stepwise_excerpts_cover_whole_demo(lesson):
    """逐段教的講義（開頭有 `<!-- 格式：每段一張圖 -->`）：正文各段節錄合起來，要涵蓋完整程式的每一行有內容的程式碼。
    只有模組 docstring 與 `if __name__ == "__main__":` 這一行可以不講。"""
    text = (ROOT / lesson).read_text(encoding="utf-8")
    if not STEPWISE.search(text.split("\n## ")[0]):
        pytest.skip("尚未改成逐段教")
    (name, code), = DEMO.findall(text)
    lines = code.split("\n")
    covered = set()
    for _, snippet in EXCERPT.findall(text):
        start, _ = locate_excerpt(code, snippet)
        covered |= set(range(start, start + snippet.count("\n") + 1))
    doc_end = 0
    if lines[0].startswith('"""'):
        doc_end = next(i for i, l in enumerate(lines) if l.rstrip().endswith('"""') and (i or l.count('"""') >= 2)) + 1
    missing = [i + 1 for i, l in enumerate(lines)
               if i >= doc_end and l.strip() and i not in covered and l.strip() != 'if __name__ == "__main__":']
    assert not missing, f"{lesson} 完整程式第 {missing[:10]} 行沒有在任何一段講到"


@pytest.mark.parametrize("lesson", sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md")))
def test_exported_demo_matches_lesson(lesson):
    """demo repo 裡的 NN_xxx.py 必須與講義內嵌 Demo 逐字相同（本機原稿目錄沒有 .py 時略過）。"""
    (name, code), = DEMO.findall((ROOT / lesson).read_text(encoding="utf-8"))
    exported = ROOT / name
    if not exported.exists():
        pytest.skip("講義原稿目錄，沒有匯出的 .py")
    assert exported.read_text(encoding="utf-8") == code + "\n"
    for wname, wcode in WORKSHOP.findall((ROOT / lesson).read_text(encoding="utf-8")):
        assert (ROOT / wname).read_text(encoding="utf-8") == wcode + "\n", f"{wname} 與講義不同"


@pytest.mark.parametrize("lesson", sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md")))
def test_workshop_starters_run(lesson, tmp_path):
    """Workshop 起手式（`<!-- workshop: 檔名 -->`）必須是可以直接執行的完整檔案。
    把整個講義目錄（data、同節 Demo）複製到暫存資料夾，在那裡執行，不會弄髒原稿。"""
    import shutil, subprocess, sys
    text = (ROOT / lesson).read_text(encoding="utf-8")
    starters = WORKSHOP.findall(text)
    if not starters:
        pytest.skip("本節沒有 Workshop 起手式")
    shutil.copytree(ROOT / "data", tmp_path / "data")
    for md in ROOT.glob("[0-1][0-9]-*.md"):
        (name, code), = DEMO.findall(md.read_text(encoding="utf-8"))
        (tmp_path / name).write_text(code + "\n", encoding="utf-8")
    for wname, wcode in starters:
        (tmp_path / wname).write_text(wcode + "\n", encoding="utf-8")
    for wname, _ in starters:
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", wname] if wname.startswith("test_") \
            else [sys.executable, wname]
        r = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, f"{wname} 執行失敗：\n{r.stdout[-800:]}\n{r.stderr[-800:]}"
        m = re.search(r"📄 來源：執行 `[^`]*" + re.escape(wname) + r"` 的輸出[^\n]*\n\n```text\n(.*?)\n```", text, re.S)
        assert m, f"{lesson} 沒有貼 {wname} 的預期輸出"
        got = r.stdout.rstrip("\n")
        if wname.startswith("test_"):
            got = re.sub(r" in [\d.]+s", "", got.splitlines()[-1])
        if int(pd.__version__.split(".")[0]) < 3:
            for old, new in WORKSHOP_PANDAS2_DIFFS.get(wname, []):
                got = got.replace(old, new)
        assert m.group(1) == got, f"{wname} 的預期輸出與實際不同：\n{got[:500]}"
