import numpy as np
 
a = np.arange(8)
print ('ndarray：')
print (a)
print ('\n')
 
b = a.reshape(4,2, order='F')
print ('new ndarray：')
print (b)
