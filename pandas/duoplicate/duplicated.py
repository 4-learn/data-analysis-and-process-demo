import pandas as pd

df = pd.DataFrame({
    "timestamp": [
        "2025-01-01 10:00",
        "2025-01-01 10:00",
        "2025-01-01 10:05"
    ],
    "person": ["Alice", "Alice", "Bob"],
    "event": ["login", "login", "login"]
})

print(df[df.duplicated()])
