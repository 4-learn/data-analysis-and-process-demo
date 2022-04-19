import pandas as pd

data = {
  "calories": [420, 380, 390],
  "duration": [50, 40, 45]
}

print("1.資料來源: Dict")
print(type(data))
print("---\n")

print("2.將 Dict 轉為 Series")
df = pd.Series(data)

print(type(df))
print(df) 
print("---\n")

print("3. Series 轉 DataFrame")
df = pd.DataFrame(data)
print(type(df))
print(df) 
print("---\n")
