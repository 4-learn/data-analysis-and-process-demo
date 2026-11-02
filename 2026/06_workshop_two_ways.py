"""第 06 節 Workshop 課堂題：兩種寫法都算「前 500 筆 no_helmet 幾次」，比較結果與能不能 groupby。"""

from importlib import import_module

import pandas as pd

demo = import_module("06_event_row")       # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    records = demo.load_records(demo.EVENTS, 500)

    # 寫法 A：一個事件一個 DataFrame
    frames = [pd.DataFrame([r]) for r in records]
    n_a = sum(f["event_type"].iloc[0] == "no_helmet" for f in frames)

    # 寫法 B：一次建一張表
    df = demo.build_table(records)
    n_b = (df["event_type"] == "no_helmet").sum()

    print(f"寫法 A：{n_a}；寫法 B：{n_b}")
    print(f"寫法 A 有 {len(frames)} 張表；寫法 B 是一張 {df.shape} 的表")
