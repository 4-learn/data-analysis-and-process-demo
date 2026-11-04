"""教師驗證：一般範例與兩個練習的實際輸出。"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).with_name("site_safety.py")
EXPECTED = """三天的事件數
0    0
1    2
2    1
dtype: int64
哪些天有事件？
0    False
1     True
2     True
dtype: bool
只留下有事件的天
1    2
2    1
dtype: int64
"""


class SiteSafetyTests(unittest.TestCase):
    def run_source(self, code):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "demo.py"
            script.write_text(code, encoding="utf-8")
            result = subprocess.run([sys.executable, str(script)], cwd=folder,
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stderr, "")
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ["demo.py"])
            return result.stdout

    def test_demo_output(self):
        self.assertEqual(self.run_source(SOURCE.read_text(encoding="utf-8")), EXPECTED)

    def test_class_exercise(self):
        code = SOURCE.read_text(encoding="utf-8").replace(
            "print(counts[counts > 0])", "print(counts[counts > 1])")
        expected = EXPECTED.replace("只留下有事件的天\n1    2\n2    1\n", "只留下有事件的天\n1    2\n")
        self.assertEqual(self.run_source(code), expected)

    def test_extension(self):
        code = SOURCE.read_text(encoding="utf-8").replace("[0, 2, 1]", "[1, 0, 3]").replace(
            "print(counts[counts > 0])", "print(counts[counts > 1])")
        self.assertEqual(self.run_source(code), """三天的事件數
0    1
1    0
2    3
dtype: int64
哪些天有事件？
0     True
1    False
2     True
dtype: bool
只留下有事件的天
2    3
dtype: int64
""")


if __name__ == "__main__":
    unittest.main()
