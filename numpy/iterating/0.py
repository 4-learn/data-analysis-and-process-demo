import numpy as np
 
a = np.arange(6).reshape(2,3)
print ('原始陣列：')
print (a)
print ('\n')
print ('迭代輸出：')
for x in np.nditer(a):
    print (x, end=", " )
print ('\n')
