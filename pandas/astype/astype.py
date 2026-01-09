import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": ["1", "1", "0"]
})

print(df)
print(df.dtypes)

print("\n\n\n")

df["value"] = df["value"].astype(int)
print(df.dtypes)
