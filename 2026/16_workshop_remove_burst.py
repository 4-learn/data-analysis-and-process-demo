"""第 16 節 Workshop 課堂題：假設有人把 W041 09-22 的 18 筆當離群值刪掉，摘要會變成什麼樣？"""

from importlib import import_module

demo = import_module("16_condense")   # 檔名以數字開頭，改用 import_module 匯入

ZONES = {"Z1": "出入口", "Z2": "鋼構組立", "Z3": "開挖區", "Z4": "施工架"}

if __name__ == "__main__":
    ev, audit = demo.clean(demo.read_events())
    cut = ev.query("not (worker_id == 'W041' and date == '2026-09-22' and is_violation)")
    print(f"刪掉 {len(ev) - len(cut)} 筆")
    print(demo.condense(cut, ZONES).drop(columns="key").to_string())
