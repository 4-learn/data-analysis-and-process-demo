import pandas as pd

df = pd.read_csv('data.csv')

sum_math = 0
counts_math = 0

sum_english = 0
counts_english = 0
for x in df.index:
    if df.loc[x, "Math"] > 60:
        counts_math += 1
        sum_math += df.loc[x, "Math"]

    if df.loc[x, "English"] > 60:
        counts_english += 1
        sum_english += df.loc[x, "English"]

avg_math = sum_math/counts_math
avg_english = sum_english/counts_english

for x in df.index:
    if df.loc[x, "Math"] < 60:
        df.loc[x, "Math"] = avg_math

    if df.loc[x, "English"] < 60:
        df.loc[x, "English"] = avg_english

print(df)
