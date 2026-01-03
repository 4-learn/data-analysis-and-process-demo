import pandas as pd

data = {
    "event_id": [101, 102, 103],
    "confidence": [0.9, 0.6, 0.3]
}

df = pd.DataFrame(data)
print(df)
