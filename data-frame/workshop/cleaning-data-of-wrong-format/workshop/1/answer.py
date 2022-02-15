import pandas as pd

df = pd.read_csv('data.csv')
df.dropna(inplace = True)

df['Calories'] = pd.to_numeric(df['Calories']).astype(int)


print(df['Calories'].to_string())

