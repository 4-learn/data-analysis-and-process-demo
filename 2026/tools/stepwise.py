"""把一節講義改寫成「每段一張圖」格式（第 05 節為樣板）。

    python3 tools/stepwise.py specs/NN.py      # 依規格檔改寫對應講義

規格檔（tools/stepwise_specs/NN.py）定義：
- LESSON：講義檔名
- KEEP_BEFORE：保留原講義從開頭到哪個標題之前（例如範例程式碼連結）
- SUBTITLE：節首一行說明
- GOALS：[(時間, 段落, 學完能做到)]
- OVERVIEW：整節流程圖（mermaid flowchart 內容，不含 ``` 與 flowchart 那一行）
- SECTIONS：每段一個 dict：
    title、short（位置圖用的短名）、question、steps（步驟圖 mermaid 行）、
    code：[(起行, 迄行)]（Demo 行號，含頭尾；主程式的行會自動去掉 4 格縮排）、
    out：要貼的輸出段落編號 list（對應 `== N.`），points：重點 list，
    extra：（可選）放在重點之後的 Markdown，例如對照表
- KEEP_AFTER：原講義從哪個標題開始保留到結尾（Workshop、教師紀錄）
- MIDDLE_KEEP：（可選）原講義中要原樣保留、放在最後一段之後的標題清單（例如「換成 MariaDB 時要改什麼」）

輸出段落、程式節錄都從實際 Demo 取得，不手抄。
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEMO = re.compile(r"(<!-- demo: ([\w.]+) -->\n```python\n(.*?)\n```\n)", re.S)
TABLE = re.compile(r"^( *)<!-- fn-table -->\n(?:\1\|[^\n]*\n)+\n", re.M)
MAIN = 'if __name__ == "__main__":'


def load_spec(path):
    spec = importlib.util.spec_from_file_location("spec", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def section(text, title_prefix):
    """回傳原講義中以 title_prefix 開頭的 ## 標題那一段（到下一個 ## 為止）。"""
    m = re.search(r"^## " + re.escape(title_prefix) + r".*?(?=^## |\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit(f"找不到段落：{title_prefix}")
    return m.group(0)


def outputs(lesson):
    py = sys.executable
    code = (f"import sys,warnings;warnings.simplefilter('ignore');sys.path.insert(0,{str(ROOT)!r});"
            f"from test_lessons import run_main;print(run_main({lesson!r}),end='')")
    out = subprocess.run([py, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True).stdout
    parts = {}
    cur = None
    head = []
    for line in out.split("\n"):
        if cur is None and not re.match(r"== (\d+)\.", line):
            head.append(line)
            continue
        m = re.match(r"== (\d+)\.", line)
        if m:
            cur = int(m.group(1))
            parts[cur] = [line]
        elif cur is not None:
            parts[cur].append(line)
    result = {k: "\n".join(v).rstrip("\n") for k, v in parts.items()}
    lead = "\n".join(head).strip("\n")
    if lead:
        result[0] = lead           # 第一個 == 之前印的開場行（例如「全部 749 條…」）
    return result


def _lint(lines):
    """節點文字不能以 markdown 符號開頭（> - # 1.），mermaid 11 會把它當 markdown 而顯示錯誤；不用 ✗ ✓ 以外的特殊符號。"""
    for line in lines:
        for label in re.findall(r'[\[\(\{]+"([^"]*)"', line):
            if re.match(r"\s*(?:>|-\s|#|\d+\.\s|\*\s)", label):
                raise SystemExit(f"節點文字不能以 markdown 符號開頭：{label!r}")


def mermaid(kind, lines):
    _lint(lines)
    return "```mermaid\nflowchart " + kind + "\n" + "\n".join("    " + x for x in lines) + "\n```\n"


def strip(sections, i):
    shorts = [s["short"] for s in sections]
    nums = [s["title"].split("、")[0] for s in sections]
    done = "、".join(nums[:i]) or "—"
    todo = "、".join(nums[i + 1:]) or "—"
    return mermaid("LR", [
        f'P["已完成：{done}"] --> C["{nums[i]}、{shorts[i]}"] --> N["接下來：{todo}"]',
        "classDef other fill:#f4f4f4,stroke:#cccccc,color:#888888",
        "class P,N other",
        "style C fill:#ffd54f,stroke:#e69500,stroke-width:3px,color:#000",
    ])


def steps(lines):
    """步驟圖。節點文字以「✗ 」開頭標紅（錯誤結果）、「✓ 」開頭標綠（正確結果），其他不上色；記號本身不顯示。"""
    body, bad, good = [], [], []
    for line in lines:
        for nid, mark in re.findall(r'(\w+)[\[\(\{]+"([✗✓]) ', line):
            (bad if mark == "✗" else good).append(nid)
        body.append(re.sub(r'"[✗✓] ', '"', line))
    body += ["classDef bad fill:#fde2e1,stroke:#c0392b", "classDef good fill:#ddf3e4,stroke:#27ae60"]
    if bad:
        body.append(f"class {','.join(dict.fromkeys(bad))} bad")
    if good:
        body.append(f"class {','.join(dict.fromkeys(good))} good")
    return mermaid("TD", body)


def overview(spec):
    """整節流程。OVERVIEW 是 [(id, 文字), ...] 依序相接；或 mermaid 行的 list（原樣輸出，可畫分支）。
    節點 ≤ 5 個由左到右，否則由上往下（頁寬只有約 700px，橫排 6 個以上字會小到看不清）。"""
    items = spec.OVERVIEW
    if items and isinstance(items[0], str):
        return mermaid(getattr(spec, "OVERVIEW_DIR", "LR"), [re.sub(r" ?[✗✓]", "", x) for x in items])
    lines = [" --> ".join(f"{i}{_shape(t)}" for i, t in items)]
    for i, t in items:
        if t.startswith("✗ "):
            lines.append(f"style {i} fill:#fde2e1,stroke:#c0392b")
        elif t.startswith("✓ "):
            lines.append(f"style {i} fill:#ddf3e4,stroke:#27ae60,stroke-width:3px")
    return mermaid("LR" if len(items) <= 5 else "TD", lines)


def _shape(t):
    t = re.sub(r"^[✗✓] ", "", t)
    if t.startswith("(") and t.endswith(")"):
        return f'[("{t[1:-1]}")]'
    return f'["{t}"]'


def excerpt(name, src_lines, a, b, main_line):
    body = src_lines[a - 1:b]
    if a > main_line:
        body = [l[4:] if l.startswith("    ") else l for l in body]
    return f"<!-- 節錄: {name} -->\n```python\n" + "\n".join(body) + "\n```\n"


def build(spec):
    path = ROOT / spec.LESSON
    text = TABLE.sub("", path.read_text(encoding="utf-8"))
    demo_block, name, src = DEMO.search(text).groups()
    src_lines = src.split("\n")
    main_line = next(i + 1 for i, l in enumerate(src_lines) if l.strip() == MAIN)
    outs = outputs(spec.LESSON)

    title = text.split("\n", 1)[0]
    links = section(text, "範例程式碼")
    keep_after = text[text.index("## " + spec.KEEP_AFTER):]
    keep_after = TABLE.sub("", keep_after)
    # 參考判讀與教師紀錄收合
    if "### 參考判讀" in keep_after and ":::spoiler 教師用" not in keep_after:
        a = keep_after.index("### 參考判讀")
        b = keep_after.find("\n### ", a + 5)
        b = b if b != -1 else keep_after.index("\n## ", a)
        inner = keep_after[a + len("### 參考判讀"):b].strip("\n")
        keep_after = keep_after[:a] + "### 參考判讀\n\n:::spoiler 教師用（點開）\n" + inner + "\n:::\n" + keep_after[b:]
    if "## 教師紀錄與下一步" in keep_after and ":::spoiler 實測環境" not in keep_after:
        a = keep_after.index("## 教師紀錄與下一步")
        b = keep_after.find("**下一節**", a)
        b = b if b != -1 else len(keep_after)
        inner = keep_after[a + len("## 教師紀錄與下一步"):b].strip("\n")
        inner = re.sub(r"^:::spoiler[^\n]*\n|^:::\n", "", inner, flags=re.M).strip("\n")
        keep_after = (keep_after[:a] + "## 附錄：完整程式\n\n```bash\npython3 " + name + "\n```\n\n" + demo_block +
                      "\n## 教師紀錄與下一步\n\n:::spoiler 實測環境、版本差異、資料來源（點開）\n" + inner + "\n:::\n\n" + keep_after[b:])
    middle = "".join(TABLE.sub("", section(text, t)) for t in getattr(spec, "MIDDLE_KEEP", []))
    for a, b in getattr(spec, "MIDDLE_REPLACE", []):
        if a not in middle:
            raise SystemExit(f"MIDDLE_REPLACE 找不到：{a[:40]}")
        middle = middle.replace(a, b, 1)

    out = [title, "",
           "> **2026-10-21 改版：每段一張圖。** " + spec.SUBTITLE, "",
           "[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)", "", links.rstrip("\n"), "",
           "## 學完能做到", "", "| 時間 | 段落 | 學完能做到 |", "| --- | --- | --- |"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in spec.GOALS]
    out += ["", "## 本節流程", "", overview(spec).rstrip("\n"), "",
            "每段都是：**問題 → 位置（黃色）→ 步驟圖 → 程式 → 輸出 → 重點**。", ""]
    covered = set()
    for i, s in enumerate(spec.SECTIONS):
        out += [f"## {s['title']}", ""]
        if s.get("question"):
            out += [f"**問題：** {s['question']}", ""]
        out += ["**在流程中的位置：**", "", strip(spec.SECTIONS, i).rstrip("\n"), ""]
        if s.get("steps"):
            out += ["**這段做了什麼：**", "", steps(s["steps"]).rstrip("\n"), ""]
        if s.get("body"):
            out += [s["body"].strip("\n"), ""]
        for a, b in s.get("code", []):
            covered |= set(range(a, b + 1))
            out += [excerpt(name, src_lines, a, b, main_line).rstrip("\n"), ""]
        for n in s.get("out", []):
            out += ["```text", outs[n], "```", ""]
        out += [f"- {p}" for p in s.get("points", [])]
        if s.get("points"):
            out.append("")
        if s.get("extra"):
            out += [s["extra"].strip("\n"), ""]
    if middle:
        out.append(middle.rstrip("\n") + "\n")
    if getattr(spec, "APPEND_MIDDLE", ""):
        out += [spec.APPEND_MIDDLE.strip("\n"), ""]
    missing = [i + 1 for i, l in enumerate(src_lines)
               if l.strip() and (i + 1) not in covered and l.strip() != MAIN and i >= _doc_end(src_lines)]
    if missing:
        raise SystemExit(f"{spec.LESSON}：Demo 第 {missing} 行沒有放進任何一段")
    printed = {n for s in spec.SECTIONS for n in s.get("out", [])}
    lost = sorted(set(outs) - printed)
    if lost:
        raise SystemExit(f"{spec.LESSON}：輸出段落 {lost} 沒有貼出")
    result = "\n".join(out) + "\n" + keep_after
    path.write_text(result, encoding="utf-8")
    print(f"{spec.LESSON}：{len(spec.SECTIONS)} 段，覆蓋 Demo {len(covered)} 行")


def _doc_end(lines):
    if not lines[0].startswith('"""'):
        return 0
    if lines[0].count('"""') >= 2:
        return 1
    return next(i for i, l in enumerate(lines[1:], 1) if '"""' in l) + 1


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(load_spec(p))
