import pandas as pd

confidence = pd.Series([0.92, "0.76", 0.45])

confidence_numeric = pd.to_numeric(confidence, errors="coerce")

print(confidence_numeric)
print(confidence_numeric.dtype)

