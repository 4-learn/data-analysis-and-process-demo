import numpy as np 
 
list = range(5)
it = iter(list)
 
x=np.fromiter(it, dtype=float)
print(x)
