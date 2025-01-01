import numpy as np
 
#  3x3 的二维陣列
arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
 
# 建立一個與 arr 形狀相同的，所有元素都為 0 的陣列
zeros_arr = np.zeros_like(arr)
print(zeros_arr)

