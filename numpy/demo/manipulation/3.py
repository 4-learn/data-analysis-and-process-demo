import numpy as np
 
a = np.arange(8).reshape(2,4)
 
print ('ndarray：')
print (a)
print ('\n')
 
print ('flatten：')
print (a.flatten())
print ('\n')
 
print ('F style：')
print (a.flatten(order = 'F'))

