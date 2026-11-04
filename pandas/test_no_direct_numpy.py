"""教師回歸檢查：pandas 範例不直接操作陣列套件。"""
import ast
from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import runpy
import unittest

ROOT = Path(__file__).resolve().parent


class MainlineTests(unittest.TestCase):
    def test_no_direct_dependency(self):
        for path in ROOT.rglob("*.py"):
            if path.name.startswith("test_"):
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"numpy|\bnp\.|ndarray|to_numpy|\.values\b", text, re.I), str(path))
            ast.parse(text)

    def test_missing_value_examples_unchanged(self):
        for name in ["isna", "fillna", "dropna"]:
            with redirect_stdout(io.StringIO()):
                namespace = runpy.run_path(str(ROOT / "nan" / f"{name}.py"))
            df = namespace["df"]
            if name == "fillna":
                self.assertEqual(df["value"].tolist(), [1.0, 1.0, 0.0])
            else:
                self.assertEqual(df["value"].isna().tolist(), [False, False, True])
            if name == "dropna":
                self.assertEqual(namespace["clean_df"].index.tolist(), [0, 1])
                self.assertEqual(namespace["clean_df"]["value"].tolist(), [1.0, 1.0])

    def test_install_check(self):
        import pandas as pd
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            runpy.run_path(str(ROOT / "pandas" / "check_install.py"))
        self.assertEqual(buffer.getvalue(), f"pandas 安裝成功\n版本： {pd.__version__}\n")


if __name__ == "__main__":
    unittest.main()
