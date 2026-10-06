"""教師用：把講義內嵌的 Demo 匯出成公開 demo repo 的 2026/ 資料夾。

    python3 tools/export_demo_repo.py <demo-repo>/2026

講義是唯一原稿：Demo 程式碼從 `<!-- demo: 檔名 -->` 區塊逐字取出，不另外維護一份。
匯出內容：每節一支 `NN_xxx.py`、`data/`（含 MANIFEST）、`tools/`（資料產生器）、
`test_lessons.py` 與各節 `test_lesson_NN.py`（測試會從同目錄的講義 .md 擷取 Demo，
所以講義原稿 `NN-*.md` 也一併放在同一層）。匯出後在目標資料夾跑 pytest 必須全過。
"""

import re
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
DEMO = re.compile(r"<!-- demo: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)

README = """# 2026 改版：資料處理與分析（pandas 3）

勞動部 AI 大數據人才養成班「Python 資料處理與分析（2026 改版）」的上課示範程式與練習資料。
本資料夾與上層舊版（`numpy/`、`pandas/`、`plot/`、`workshop/`）互不相干；舊版內容保留不動。

- 講義（HackMD Book）：{book}

## 環境

Ubuntu LTS、**Python 3.11 以上**（pandas 3.0 的要求）。

```bash
cd 2026
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 01_position.py          # 每支都可以直接執行，只讀 data/、不寫檔、不連網
python3 -m pytest -q            # 驗證：講義貼的輸出與實際執行結果逐字相同
```

以 Python 3.10／pandas 2.3.3 執行也能跑，但部分輸出不同（字串欄顯示 `object`、chained assignment 與混合時區行為不同）；差異逐條列在各測試的 `PANDAS2_DIFFS`。

## 目錄

| 檔案 | 節次 | 主題 |
|---|---|---|
{rows}

## 練習資料：`data/`

- `articles.jsonl`、`02-exports/`、`03-*`、`09-batches/`：來自爬蟲課練習站 [crawler-playground](https://github.com/4-learn/crawler-playground)（MIT）固定 commit，由 `tools/build_fixtures.py` 產生。條文**可能經刻意修改，不具法律效力**。
- `events/`：**合成**的工地 AI 攝影機事件、人員名冊、虛驚通報，由 `tools/build_events.py` 以固定種子產生。**人名、電話、工號、事件全部虛構**，不代表任何真實工地。
- 每個檔案的位元組數與 SHA-256 記在 `MANIFEST.json`；重建結果位元組相同。

## 給老師

`NN-*.md` 是講義原稿（與 HackMD 同內容），測試從這裡擷取 Demo 並比對貼上的輸出；`.py` 由 `tools/export_demo_repo.py` 從講義逐字取出，請改講義、再重新匯出，不要直接改 `.py`。
"""


def main() -> None:
    out = Path(sys.argv[1]).resolve()
    book = sys.argv[2] if len(sys.argv) > 2 else "（發布後補上）"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    rows = []
    for md in sorted(SRC.glob("[0-1][0-9]-*.md")):
        text = md.read_text(encoding="utf-8")
        (name, code), = DEMO.findall(text)
        (out / name).write_text(code + "\n", encoding="utf-8")
        shutil.copy(md, out / md.name)
        title = text.splitlines()[0].lstrip("# ").split("｜", 1)[1]
        rows.append(f"| `{name}` | {md.name[:2]} | {title} |")
    shutil.copytree(SRC / "data", out / "data", symlinks=True)
    if any(p.is_symlink() for p in (out / "data").rglob("*")):
        raise SystemExit("data/ 裡有 symlink，請先清掉")
    shutil.copytree(SRC / "tools", out / "tools", ignore=shutil.ignore_patterns("__pycache__"))
    for t in sorted(SRC.glob("test_lesson*.py")):
        shutil.copy(t, out / t.name)
    (out / "requirements.txt").write_text(
        "pandas==3.0.6\nnumpy==2.4.6\ntabulate==0.10.0\nopenpyxl==3.1.5\npytest==9.1.1\n", encoding="utf-8")
    (out / "README.md").write_text(README.format(book=book, rows="\n".join(rows)), encoding="utf-8")
    print(f"exported {len(rows)} demos to {out}")


if __name__ == "__main__":
    main()
