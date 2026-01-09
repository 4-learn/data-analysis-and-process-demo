import pandas as pd
import numpy as np

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, np.nan]
})

df["value"] = df["value"].fillna(0)
print(df)
