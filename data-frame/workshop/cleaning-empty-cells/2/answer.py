import pandas as pd

df = pd.read_csv('data.csv')
x = df["spec-x"].mean()

df.fillna(x, inplace = True)
print(df.to_string())
