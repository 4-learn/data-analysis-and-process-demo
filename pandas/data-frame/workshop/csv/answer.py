import pandas as pd

# 讀取資料
df = pd.read_csv('A17000000J-030266-pJX.csv')

# 使用 Pandas 的 max 和 min 方法計算最大值和最小值
val_max = df["兩性差距（%）"].max()
val_min = df["兩性差距（%）"].min()

print("最大: " + str(val_max))
print("最小: " + str(val_min))
