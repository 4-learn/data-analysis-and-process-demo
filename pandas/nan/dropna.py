import pandas as pd
import numpy as np

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, np.nan]
})

clean_df = df.dropna()
print(df)
print(clean_df)
