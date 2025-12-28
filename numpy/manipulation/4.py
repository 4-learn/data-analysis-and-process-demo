import numpy as np
 
a = np.arange(8).reshape(2, 4)

print('原始 array：')
print(a)
print('\n')

# 使用 ravel 並修改返回的視圖
raveled = a.ravel()
raveled[0] = 999  # 修改 ravel 返回的第一個元素

print('修改後的 ravel 視圖：')
print(raveled)
print('\n')

print('原始 array (檢查是否被影響)：')
print(a)
