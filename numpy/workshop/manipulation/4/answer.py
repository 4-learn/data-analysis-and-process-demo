import numpy as np

a = np.arange(8).reshape(2,4)
a.flatten()[1] = 100
print(a)

"""output
[[0 1 2 3]
 [4 5 6 7]]
"""

b = np.arange(8).reshape(2,4)
b.ravel()[1] = 100
print(b)

"""output
[[  0 100   2   3]
 [  4   5   6   7]]
"""

## 解說
"""
flatten : return array copy
revel : return array (mutable)
因此， revel 所 return 的陣列，是會被改變的。
"""
