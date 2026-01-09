import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Charlie"],
    "fail_count": [2, 0, 5]
})

print(df)

print("/n/n")

df["risk_score"] = df["fail_count"]
print(df)
