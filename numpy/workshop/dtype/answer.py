import numpy as np
import csv

csv_data = []

with open('product_quality.csv', 'r') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)  # 跳過標題行
    for row in csv_reader:
        csv_data.append(row)

# 將Python列表轉換為NumPy陣列，設定dtype為混合類型，ndim為2
data = np.array(csv_data, dtype=np.dtype(dtype=np.float64), ndmin=2)

# 印出結果
print("NumPy 2D Array:")
print(data)
print("dtype:", data.dtype)
print("ndim:", data.ndim)
