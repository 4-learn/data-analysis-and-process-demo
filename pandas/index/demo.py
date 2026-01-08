import pandas as pd

df = pd.DataFrame(
    [[2, 3], [5, 6], [8, 9]],
    index=["event_A", "event_B", "event_C"],
    columns=["confidence", "area"]
)

print(df)
