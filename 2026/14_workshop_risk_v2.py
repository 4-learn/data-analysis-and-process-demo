"""第 14 節 Workshop 課堂題：發布 risk-v2（2 次以上為中、4 次以上為高），比較與 v1 的差異。"""

from importlib import import_module

import pandas as pd

demo = import_module("14_derived_rules")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    table, types, period = demo.weekly_counts()
    table["v1"] = demo.risk_level(table["violations"])
    v2 = dict(demo.RULE, version="risk-v2", levels=[("低", 0, 2), ("中", 2, 4), ("高", 4, None)])
    table["v2"] = demo.risk_level(table["violations"], v2)
    print(pd.crosstab(table["v1"], table["v2"]).to_string())
    print(f"等級改變的列數：{int((table['v1'] != table['v2']).sum())}")
