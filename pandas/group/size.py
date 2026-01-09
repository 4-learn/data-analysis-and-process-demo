import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice", "Alice"],
    "event": ["login", "login", "logout", "login"]
})

result = df.groupby("person").size()
print(result)
