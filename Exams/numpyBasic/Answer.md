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

#### 2. 建立 3 個 size 為 10 的 ndarray (內容：全為 0, 全為 1, 全為 5)

```python=
import numpy as np
array=np.zeros(10)
print("1. 全為 0")
print(array)

array=np.ones(10)
print("2. 全為 1:")
print(array)

array=np.ones(10)*5
print("3. 全為 5:")
print(array)
```

#### 3. 建立一個從 30 到 70 的整數 ndarray:
```python=
import numpy as np
array=np.arange(30,71)
print("1. Ndarray from 30 to 70")
print(array)
```

#### 4. 建立一個從 30 到 70 的偶數 ndarray:
```python=
import numpy as np
array=np.arange(30,71,2)
print("1. Ndarray (even) from 30 to 70")
print(array) 
```
