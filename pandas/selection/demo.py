import pandas as pd

df = pd.DataFrame({
    "timestamp": ["2025-01-01", "2025-01-01", "2025-01-02"],
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, 0]
})

print("原始資料：")
print(df)
print("----")

print("只看 event 欄位：")
print(df["event"])
print("----")

print("前兩筆資料：")
print(df.iloc[0:2])
print("----")

print("只留下 login 事件：")
print(df[df["event"] == "login"])

