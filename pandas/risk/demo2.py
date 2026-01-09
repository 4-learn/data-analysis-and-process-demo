import pandas as pd

df = pd.DataFrame({
    "person": ["Alice", "Bob", "Charlie"],
    "fail_count": [2, 0, 5]
})

print(df)

print("/n/n")

def risk_level(score):
    if score >= 4:
        return "high"
    elif score >= 1:
        return "medium"
    else:
        return "low"

df["risk_score"] = df["fail_count"]
df["risk_level"] = df["risk_score"].apply(risk_level)
print(df)
