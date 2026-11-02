"""第 03 節 Workshop 課堂題：在 data/03-exports/ 放入第四份檔 extra.csv。
執行完，再跑一次 03_read_files.py，看會發生什麼。做完記得刪掉 extra.csv。"""

from pathlib import Path

import pandas as pd

EXPORTS = Path(__file__).resolve().parent / "data" / "03-exports"

if __name__ == "__main__":
    src = pd.read_csv(EXPORTS / "mass-layoff.csv", dtype=str, keep_default_na=False)
    extra = src.head(3)
    extra.to_csv(EXPORTS / "extra.csv", index=False)
    print(f"放入 data/03-exports/extra.csv：{len(extra)} 列（大量解僱法前三條）")
