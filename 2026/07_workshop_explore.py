"""第 07 節 Workshop 課堂題：探索報告的起點。執行後會停在 >>> 提示字元，raw 已經讀好，接著自己下指令。
執行：python3 -i 07_workshop_explore.py"""

from importlib import import_module

demo = import_module("07_explore")   # 檔名以數字開頭，改用 import_module 匯入

raw = demo.read_raw(demo.EXPORT)
print(f"raw 已讀入：{raw.shape}；欄位 {raw.columns.tolist()}")
print("試試：raw['區域'].value_counts()、raw.groupby('區域')['攝影機'].nunique()、raw['發生時間'].min()")
