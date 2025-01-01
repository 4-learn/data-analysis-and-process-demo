import numpy as np 
 
# 陣列的 dtype 為 int8（1 個 bytes）  
x = np.array([1,2,3,4,5], dtype = np.int8)  
print (x.itemsize)
 
# 陣列的 dtype 為  float64（8 個 bytes） 
y = np.array([1,2,3,4,5], dtype = np.float64)  
print (y.itemsize)

