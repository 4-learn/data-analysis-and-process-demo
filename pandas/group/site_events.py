"""彙總事件：兩天的工地事件表，全部都是教學用假資料。"""
import pandas as pd

# 一、建立事件表
df = pd.DataFrame({
    "timestamp": [
        "2026-03-02T08:55:00+08:00",
        "2026-03-02T09:03:00+08:00",
        "2026-03-02T09:10:00+08:00",
        "2026-03-02T09:20:00+08:00",
        "2026-03-02T10:05:00+08:00",
        "2026-03-02T10:30:00+08:00",
        "2026-03-02T11:00:00+08:00",
        "2026-03-03T09:15:00+08:00",
        "2026-03-03T09:40:00+08:00",
        "2026-03-03T10:00:00+08:00",
    ],
    "person": ["worker_A", "worker_A", "worker_B", "worker_B", "worker_C",
               "worker_A", "worker_A", "worker_C", "worker_B", "worker_C"],
    "zone": ["zone_1", "zone_1", "zone_1", "zone_1", "zone_2",
             "zone_1", "zone_1", "zone_2", "zone_2", "zone_2"],
    "event": ["enter_zone", "no_helmet", "enter_zone", "no_helmet", "enter_zone",
              "no_helmet", "leave_zone", "no_helmet", "no_helmet", "leave_zone"],
    "value": [0.95, 0.88, 0.93, 0.81, 0.97, 0.90, 0.91, 0.86, 0.83, 0.89],
})
df["timestamp"] = pd.to_datetime(df["timestamp"])

print("一、事件表")
print(df)

# 二、依人彙總
print("\n二、每位工人有幾筆事件")
print(df.groupby("person").size())

# 三、依事件彙總
print("\n三之一、每種事件出現幾次")
print(df["event"].value_counts())
print("\n三之二、最常見的前 2 種事件（Top-2）")
print(df["event"].value_counts().head(2))

# 四、依時間彙總
df["date"] = df["timestamp"].dt.date
print("\n四之一、每天有幾筆事件")
print(df.groupby("date").size())
print("\n四之二、每位工人每天有幾筆事件")
print(df.groupby(["person", "date"]).size())

# 五、依區域彙總
no_helmet = df[df["event"] == "no_helmet"]
print("\n五、每個區域有幾筆未戴安全帽")
print(no_helmet.groupby("zone").size())

# 六、比例
counts = df["event"].value_counts()
print("\n六、每種事件佔全部事件的比例")
print(counts / counts.sum())
