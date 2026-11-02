"""第 17 節 Workshop 課堂題：第一個被丟掉的條文（職業安全衛生法第 6 條）寫了什麼？"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"

if __name__ == "__main__":
    df = pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    print(df.query("pcode == 'N0060001' and slug == '6'")["content"].iloc[0])
