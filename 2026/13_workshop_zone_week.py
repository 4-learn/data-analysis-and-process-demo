"""第 13 節 Workshop 課堂題：區域 × 週的彙總表。已經算好事件數；請加上違規數與違規率兩欄。"""

from importlib import import_module

import pandas as pd

demo = import_module("13_groupby_denominator")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    raw, ev = demo.read_events()
    ev["is_violation"] = ev["event_type"].isin(demo.violation_types())
    t = pd.to_datetime(ev["event_time"], format="ISO8601").dt.tz_convert("Asia/Taipei")
    ev["week"] = t.dt.tz_localize(None).dt.to_period("W-SUN").astype(str)
    table = ev.groupby(["zone", "week"]).agg(事件數=("event_id", "size"))   # TODO：加上 違規數、違規率
    print(table.to_string())
    print(f"{len(table)} 列；事件數合計 {table['事件數'].sum()}")
