import numpy as np

a = np.arange(8).reshape(2,4)
print(a.flatten().reshape(2,4))
print(type(a))
a.flatten()[1] = 100
print(a)
 
b = np.arange(8).reshape(2,4)
print(b.ravel().reshape(2,4))
print(type(b))
b.ravel()[1] = 100
print(b)
