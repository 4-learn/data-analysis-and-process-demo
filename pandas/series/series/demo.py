import pandas as pd

df = pd.DataFrame({
    "event_id": [101, 102, 103],
    "confidence": [0.92, 0.76, 0.45],
    "area": [800, 300, 600]
})

confidence_series = df["confidence"]

print(confidence_series)

