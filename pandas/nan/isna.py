import pandas as pd
import numpy as np

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "login", "logout"],
    "value": [1, 1, np.nan]
})


print(type(df.isna()))
print(df.isna())
