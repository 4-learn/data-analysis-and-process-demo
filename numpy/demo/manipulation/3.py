import numpy as np

# 建立原始陣列
a = np.arange(8).reshape(2, 4)

print('原始 ndarray：')
print(a)
print('\n')

# 使用 flatten()，並修改返回的副本
flattened = a.flatten()
flattened[0] = 999  # 修改副本中的第一個元素

print('修改後的 flattened 副本：')
print(flattened)
print('\n')

print('原始 ndarray (檢查是否被影響)：')
print(a)
