"""把每一節的 Workshop 改成「課堂題＋延伸題」，並把起手式改成可以直接執行的檔案。

    python3 tools/workshop.py tools/workshop_specs/NN.py ...

規格檔（tools/workshop_specs/NN.py）定義：
- LESSON：講義檔名
- TITLE：Workshop 標題（不含「Workshop：」）
- STARTER：起手式檔名（例如 "03_workshop_fourth_file.py"），None 表示沒有
- STARTER_CODE：起手式完整內容
- CLASS：課堂題（Markdown，約 10 分鐘，多半是執行起手式、改一點）
- RUN：(指令, 說明)；用來產生「預期輸出」的實際執行，指令只能是起手式本身
- EXTENSION：延伸題（Markdown）
- EXT_ANSWER：延伸題的預期結果（Markdown，可空；數字一律教師實測）
- ACCEPT：驗收（Markdown 條列）
原講義的「參考判讀」整段保留（收合給教師看）。總驗收節（19）也照同樣格式，但標明「整段都是驗收」。
"""
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = re.compile(r"<!-- demo: ([\w.]+) -->\n```python\n(.*?)\n```", re.S)


def load(path):
    spec = importlib.util.spec_from_file_location("ws", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_starter(spec):
    """在暫存資料夾放好 data、所有 Demo 與起手式，實際執行，回傳標準輸出。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copytree(ROOT / "data", tmp / "data")
        for md in ROOT.glob("[0-1][0-9]-*.md"):
            (name, code), = DEMO.findall(md.read_text(encoding="utf-8"))
            (tmp / name).write_text(code + "\n", encoding="utf-8")
        (tmp / spec.STARTER).write_text(spec.STARTER_CODE.strip("\n") + "\n", encoding="utf-8")
        if spec.STARTER.startswith("test_"):
            cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", spec.STARTER]
        else:
            cmd = [sys.executable, spec.STARTER]
        r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise SystemExit(f"{spec.STARTER} 執行失敗：\n{r.stdout}\n{r.stderr}")
        out = r.stdout.rstrip("\n")
        if spec.STARTER.startswith("test_"):
            out = re.sub(r" in [\d.]+s", "", out.splitlines()[-1])
        return out


def build(spec):
    path = ROOT / spec.LESSON
    text = path.read_text(encoding="utf-8")
    a = text.index("## Workshop")
    b = text.index("## 附錄：完整程式")
    old = text[a:b]
    ref = ""
    m = re.search(r"### 參考判讀\n.*?(?=\n### 驗收|\Z)", old, re.S)
    if m:
        ref = m.group(0).strip("\n") + "\n\n"
    elif ":::spoiler 參考判讀" in old:
        m = re.search(r":::spoiler 參考判讀[^\n]*\n.*?\n:::\n", old, re.S)
        ref = "### 參考判讀\n\n" + m.group(0).replace(":::spoiler 參考判讀（教師用）", ":::spoiler 教師用（點開）") + "\n"
    lines = [f"## Workshop：{spec.TITLE}", ""]
    if getattr(spec, "NOTE", ""):
        lines += [spec.NOTE.strip("\n"), ""]
    cls = spec.CLASS.strip("\n")
    lines += ["### 題目", "", "**課堂題**（約 10 分鐘）：" + cls, ""]
    if spec.STARTER:
        url = f"https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/{spec.STARTER}"
        lines += [f"起手式 [`{spec.STARTER}`]({url})（在 `2026/` 資料夾執行）：", "",
                  f"<!-- workshop: {spec.STARTER} -->", "```python", spec.STARTER_CODE.strip("\n"), "```", ""]
    ext = spec.EXTENSION.strip("\n")
    sep = "\n\n" if re.match(r"\d+\. |\|", ext) else ""
    lines += ["**延伸題**（做完課堂題再做）：" + sep + ext, "", "### 預期輸出", ""]
    if spec.STARTER:
        cmd = f"python3 -m pytest -q {spec.STARTER}" if spec.STARTER.startswith("test_") else f"python3 {spec.STARTER}"
        lines += ["課堂題：", "", f"<sub>📄 來源：執行 `{cmd}` 的輸出{getattr(spec, 'RUN_NOTE', '')}</sub>", "",
                  "```text", run_starter(spec), "```", ""]
    if getattr(spec, "CLASS_ANSWER", ""):
        lines += [spec.CLASS_ANSWER.strip("\n"), ""]
    if getattr(spec, "EXT_ANSWER", ""):
        lines += ["延伸題：", "", spec.EXT_ANSWER.strip("\n"), ""]
    lines += [ref.rstrip("\n"), "", "### 驗收", "", spec.ACCEPT.strip("\n"), "", ""]
    body = "\n".join(lines)
    parts = re.split(r"(```.*?```)", body, flags=re.S)        # 只在程式區塊外合併多餘空行
    body = "".join(p if i % 2 else re.sub(r"\n{3,}", "\n\n", p) for i, p in enumerate(parts))
    text = text[:a] + body + text[b:]
    path.write_text(text, encoding="utf-8")
    print(f"{spec.LESSON}：Workshop 已改寫（起手式 {spec.STARTER or '無'}）")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        build(load(p))
