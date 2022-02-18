import numpy as np
 
# 預設為浮點數
x = np.zeros(5) 
print(x)
 
# 設置類行為整數
y = np.zeros((5,), dtype = np.int_) 
print(y)
 
# 自定義類型
z = np.zeros((2,2), dtype = [('x', 'i4'), ('y', 'i4')])  
print(z)

