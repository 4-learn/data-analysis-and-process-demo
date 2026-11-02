"""第 12 節 Workshop 課堂題：施工日 × 區域的違規數表（沒有違規的格子是 0）。"""

from importlib import import_module

demo = import_module("12_datetime_resample")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    events = demo.load_events()
    print(f"ts 的型別：{events['ts'].dtype}")
    days = events.set_index("ts").resample("D").size().index
    workdays = days[days.dayofweek != 6]                       # 週日停工
    table = demo.daily_zone(events, workdays)
    print(f"{table.shape[0]} 天 × {table.shape[1]} 區；09-01 的 Z4：{table.loc['2026-09-01', 'Z4']}")
    print(table.sum().to_string())
