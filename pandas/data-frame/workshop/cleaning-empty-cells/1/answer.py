import pandas as pd

data = {
  "hight": [112, 112, 124, 125, 140]
}

df =  pd.DataFrame(data)
x = df["hight"].mean()
y = df["hight"].median()
z = df["hight"].mode()

print(x, y, z)
