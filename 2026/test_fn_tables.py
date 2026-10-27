"""程式區塊上方的「函式名稱／說明／官方文件連結」表格。

- 每個 Python 程式區塊正上方都有一張表，表頭固定三欄。
- 表格內容等於 tools/fn_tables.py 依目前 Demo 重新產生的結果：改了 Demo 卻沒重跑 `apply`，這裡會失敗。
- 每個連結都在 tools/fn_docs.json（已實測 200、錨點存在）裡；不允許手寫未驗證的網址。
- 拿掉表格後，講義其餘內容與表格無關（產生器只插入、不改字）。
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import fn_tables as T  # noqa: E402

LESSONS = sorted(p.name for p in ROOT.glob("[0-1][0-9]-*.md"))
DOCS = set(json.loads((ROOT / "tools" / "fn_docs.json").read_text(encoding="utf-8")).values())


@pytest.fixture(scope="module")
def planned():
    out, docs, errors = T.plan()
    return out, docs, errors


def test_generator_has_no_unresolved_functions(planned):
    assert planned[2] == []


@pytest.mark.parametrize("lesson", LESSONS)
def test_every_python_block_has_a_table_directly_above(lesson):
    text = (ROOT / lesson).read_text(encoding="utf-8")
    n_blocks = len(T.blocks(T.TABLE.sub("", text)))
    tables = list(T.TABLE.finditer(text))
    assert len(tables) == n_blocks > 0
    for m in tables:
        rest = text[m.end():]
        assert re.match(r" *(?:<!-- (?:demo|節錄):[^\n]*-->\n)? *```python\n", rest), f"{lesson} 表格下方不是程式區塊"
        assert m.group(0).split("\n")[1].strip() == T.HEADER


@pytest.mark.parametrize("lesson", LESSONS)
def test_tables_match_generator(planned, lesson):
    out, docs, _ = planned
    text, tables = out[lesson]
    assert (ROOT / lesson).read_text(encoding="utf-8") == T.build(text, tables, docs), \
        f"{lesson} 的表格與產生器不一致：請執行 python3 tools/fn_tables.py apply"


@pytest.mark.parametrize("lesson", LESSONS)
def test_links_are_verified_official_docs(lesson):
    text = (ROOT / lesson).read_text(encoding="utf-8")
    for m in T.TABLE.finditer(text):
        for url in re.findall(r"\]\((https?://[^)]+)\)", m.group(0)):
            assert url in DOCS, f"{lesson} 有未驗證的連結 {url}"


def test_catalog_entries_all_have_docs():
    docs = json.loads((ROOT / "tools" / "fn_docs.json").read_text(encoding="utf-8"))
    assert set(T.C.ENTRIES) <= set(docs)
