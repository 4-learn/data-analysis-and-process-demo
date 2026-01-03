import pandas as pd

df = pd.read_csv('data.csv')

print(type(df["Duration"]))
print(df["Duration"][0])
