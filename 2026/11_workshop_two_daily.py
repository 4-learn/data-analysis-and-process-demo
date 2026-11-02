"""第 11 節 Workshop 課堂題：依發生日、依到達日（台北）各數一次每日事件，並排看差在哪幾天。"""

from importlib import import_module

import pandas as pd

demo = import_module("11_event_vs_ingest")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    events = demo.dedupe(demo.load_events())
    table = pd.DataFrame({"依發生日": demo.daily(events, "event"), "依到達日": demo.daily(events, "ingest")})
    table["差"] = table["依到達日"] - table["依發生日"]
    print(f"{len(events)} 列，{len(table)} 天")
    print(table[table["差"] != 0].to_string())
