import numpy as np
 
a = np.arange(12).reshape(3,4)
 
print ('ndarray：')
print (a )
print ('\n')
 
print ('after：')
print (np.transpose(a))
