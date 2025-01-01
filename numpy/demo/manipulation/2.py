import numpy as np
 
a = np.arange(9).reshape(3,3) 
print ('ndarray：')
for row in a:
    print (row)
 
print ('迭代後：')
for element in a.flat:
    print (element)

