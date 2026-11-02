"""第 15 節 Workshop 課堂題：每個承攬商的違規率。已經算好事件數；請加上違規數與違規率。"""

from importlib import import_module

demo = import_module("15_merge_fanout")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    ev = demo.read_events()
    ev["violation"] = ev["event_type"].isin(demo.VIOLATIONS)
    staff = demo.attach_roster(ev, demo.read_csv("workers.csv"))
    known = staff[staff["worker_id"] != ""]
    table = known.groupby("contractor").agg(事件數=("event_id", "size"))   # TODO：加上 違規數、違規率
    print(table.to_string())
    print(f"事件數合計 {table['事件數'].sum()}（應等於已辨識事件數 {len(known)}）")
