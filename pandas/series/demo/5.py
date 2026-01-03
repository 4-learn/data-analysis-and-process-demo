import pandas as pd

df = pd.DataFrame([[2, 3], [5, 6], [8, 9]],
    index=['cobra', 'viper', 'sidewinder'],
    columns=['max_speed', 'shield'])

print(type(df))
print(df)

print(type(df.to_string()))
print(df.to_string())
