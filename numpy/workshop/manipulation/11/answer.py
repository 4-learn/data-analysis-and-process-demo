import numpy as np
a = np.arange(3072).reshape(3,32,32)
print("before:")
print(a)
print("after:")
print(np.rollaxis(a, 0, 3))
