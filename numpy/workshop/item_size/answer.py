import numpy as np

# 創建一個具有 str 資料類型的 NumPy ndarray
arr = np.array(["apple", "banana", "cherry"], dtype=str)

# 獲取資料類型和 itemsize
dtype = arr.dtype
itemsize = dtype.itemsize

# 打印 itemsize
print("每個元素的 itemsize 是 {} 位元組".format(itemsize))

