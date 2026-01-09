import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Alice"],
    "event": ["login", "Login", "LOGIN"]
})

print(df)

print("\n\n")

df["event"] = df["event"].str.lower()
print(df)
