import numpy as np

ori_arr = np.array([[[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]])

arr = np.array(ori_arr)
print("1. 原來的 ndarray 是:")
print(arr)

print("2. 原來的維度是:")
print(arr.ndim)

# 開始自訂維度為
arr = np.array(ori_arr, ndmin = 2)

print("3. 自訂維度後，新的 ndarray 為:")
print(arr)

print("4. 自訂維度後，新的 ndarray 維度為:")
print(arr.ndim)
