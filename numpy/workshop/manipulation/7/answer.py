import numpy as np
a = np.arange(8).reshape(2,2,2)
print(a)
print("---")
print(np.rollaxis(a, 1, 0))
