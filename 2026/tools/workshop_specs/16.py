LESSON = '16-condense.md'
TITLE = '一個異常，能改寫幾行摘要？'
STARTER = '16_workshop_remove_burst.py'
CLASS = '假設有人在「清理」時把 W041 09-22 的 18 筆當離群值刪掉。執行起手式，和第四段的摘要逐行比較：哪幾行變了？如果交給 LLM 的是這份，它會怎麼描述最後一週？'
EXTENSION = "\n\n1. 對 Demo 的摘要每一行，用 `ev.query(key)` 查出來的筆數是不是等於 `n`？把某一列的 `key` 改錯（例如 `'W041'` 改成 `'W401'`），呼叫 `trace()`，看會發生什麼。\n2. 請 OpenCode 寫「把 events.jsonl 濃縮成給 LLM 的摘要」，檢查：有沒有以 `event_id` 去重？Top-K 第 1 名是不是空字串？有沒有用平均取代異常清單？任挑一個數字，你能不能找出是哪幾筆？"
ACCEPT = '- 指出至少三行變化：Top 人（W041 掉出前三）、Top 時段（14 點 → 13 點）、趨勢（看起來在改善）、異常列消失。\n- （延伸）`key` 改錯時 `trace()` 會報錯；AI 版本四項檢查都有結論。'
STARTER_CODE = '"""第 16 節 Workshop 課堂題：假設有人把 W041 09-22 的 18 筆當離群值刪掉，摘要會變成什麼樣？"""\n\nfrom importlib import import_module\n\ndemo = import_module("16_condense")   # 檔名以數字開頭，改用 import_module 匯入\n\nZONES = {"Z1": "出入口", "Z2": "鋼構組立", "Z3": "開挖區", "Z4": "施工架"}\n\nif __name__ == "__main__":\n    ev, audit = demo.clean(demo.read_events())\n    cut = ev.query("not (worker_id == \'W041\' and date == \'2026-09-22\' and is_violation)")\n    print(f"刪掉 {len(ev) - len(cut)} 筆")\n    print(demo.condense(cut, ZONES).drop(columns="key").to_string())\n'
