import pandas as pd

data = {
  "calories": [420, 380, 390],
  "duration": [50, 40, 45]
}

#load data into a DataFrame object:
df = pd.DataFrame(data)


# 顯示資料結構
print("目前的資料為:")
print(df)

# 請輸入你要顯示的 index 個數
counts_index = int(input("請輸入你要顯示的 index 個數: "))

print(df.loc[ 0:counts_index-1 ])
