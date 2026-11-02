"""第 08 節 Workshop 課堂題：出入口（Z1）2026-09-15～09-17 有幾筆未戴安全帽？信心度高於 0.8 的有幾筆？"""

from importlib import import_module

demo = import_module("08_select_filter")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    df = demo.load_events()
    hit = demo.subset(df, "Z1", "2026-09-15T00:00:00+08:00", "2026-09-18T00:00:00+08:00", "no_helmet")
    c = hit["confidence"]
    print(f"Z1 09-15～09-17 no_helmet：{len(hit)} 筆；信心度 > 0.8：{int((c > 0.8).sum())} 筆")
    print(hit["camera_id"].value_counts().to_string())
