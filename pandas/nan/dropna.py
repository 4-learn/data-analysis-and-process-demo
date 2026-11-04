import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, None]
})

clean_df = df.dropna()
print(df)
print(clean_df)
