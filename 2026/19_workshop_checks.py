"""第 19 節 Workshop：加兩道你自己的檢查。把兩個 TODO 補完，再執行一次。
原始檔的指紋不能變；Z9 和週日要被擋下。"""

import json
from importlib import import_module

demo = import_module("19_end_to_end")   # 檔名以數字開頭，改用 import_module 匯入

ZONES = set(json.loads((demo.DATA / "MANIFEST.json").read_text(encoding="utf-8"))["zones"])


def known_zone(ev):
    pass   # TODO：zone 不在 ZONES 就 raise demo.PipelineError(...)


def not_sunday(ev):
    pass   # TODO：工地週日停工；ev["date"] 是台北時間的 'YYYY-MM-DD'


if __name__ == "__main__":
    lines = (demo.DATA / "events.jsonl").read_text(encoding="utf-8").splitlines()
    print("原始檔指紋：", demo.fingerprint(demo.run(demo.DATA / "events.jsonl", checks=[known_zone, not_sunday])[0]))
    for label, src in [("Z9", demo.broken(lines, 5, zone="Z9")),
                       ("週日", demo.broken(lines, 5, event_time="2026-09-06T07:30:00+08:00")),
                       ("worker W999", demo.broken(lines, 5, worker_id="W999"))]:
        try:
            demo.run(src, checks=[known_zone, not_sunday])
            print(label, "沒擋下")
        except demo.PipelineError as e:
            print(label, "擋下：", e)
