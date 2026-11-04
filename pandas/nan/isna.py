import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, None]
})


print(type(df.isna()))
print(df.isna())
