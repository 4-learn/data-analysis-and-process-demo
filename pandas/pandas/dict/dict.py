import pandas as pd

data = {
    "event_id": [101, 102, 103],
    "confidence": [0.92, 0.76, 0.45],
    "area": [800, 300, 600]
}

print("1. 原始資料型態：")
print(type(data))
print("---\n")

print("2. 將 Dict 轉為 DataFrame（事件表）")
df = pd.DataFrame(data)

print(type(df))
print(df)
print("---\n")

print("3. DataFrame 的一列，本質上是一個 Series（單一事件）")
print(type(df.iloc[0]))
print(df.iloc[0])

