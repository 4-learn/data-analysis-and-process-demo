import pandas as pd

data = {
  "calories": [420, 380, 390],
  "duration": [50, 40, 45]
}

print("1.資料來源: Dict")
print(type(data))
print("---\n")

print("2.將 Dict 轉為 DataFrame")
df = pd.DataFrame(data)

print(type(df))
print(df) 
print("---\n")

print("3.DataFrame 其實就是 Series 的集合 (iloc 後面會講)")
print(type(df.iloc[0]))
print(df.iloc[0]) 
print("---\n")

