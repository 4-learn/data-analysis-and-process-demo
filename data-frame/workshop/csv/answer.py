import pandas as pd

df = pd.read_csv('A17000000J-030266-pJX.csv')


val_max = 0
val_min = 100
for index in range(len(df["兩性差距（%）"])):
    if (df["兩性差距（%）"][index] > val_max):
        val_max = df["兩性差距（%）"][index]
    if (df["兩性差距（%）"][index] < val_min):
        val_min = df["兩性差距（%）"][index]

print("最大: " + str(val_max))
print("最小: " + str(val_min))
