import numpy as np
 
a = np.ones([10,10], dtype = int)
b = np.ones([10,10], dtype = int)
b.fill(2)

c = a * b 
print (c)
