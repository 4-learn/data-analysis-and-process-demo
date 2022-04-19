## Numpy Basic

#### 1. 以 1, 7, 13, 105 為陣列，建立 1 個 ndaray，並計算出在記憶體中的使用量:
```python=
import numpy as np
X = np.array([1, 7, 13, 105])
print("1. 原始 ndarray:")
print(X)

print("2. Array 記憶體使用量:")
print("%d bytes" % (X.size * X.itemsize))
```
