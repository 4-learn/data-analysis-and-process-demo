import numpy as np
import csv

csv_data = []
with open('product_quality.csv', 'r') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)
    for row in csv_reader:
        csv_data.append(row)

# 轉換 Python 列表為 NumPy 綻裂，設定 dtype 為float，ndim 為 2
data = np.array(csv_data, dtype=float, ndmin=2)

# print
print("NumPy 2D Array:")
print(data)
print("dtype:", data.dtype)
print("ndim:", data.ndim)
