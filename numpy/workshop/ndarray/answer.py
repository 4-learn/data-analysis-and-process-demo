import numpy as np

# 原始資料以及其 type
x = [1, 2, 3, 4, 5, True]
arr_x = np.array(x)

print(arr_x)
print(arr_x.dtype)

"""output (只支援一種資料型態，所以 True 被轉成 1
[1 2 3 4 5 1]
int64
"""

# asarray
as_arr_x = np.asarray(x)
print(as_arr_x)

"""output
[1 2 3 4 5 1]
"""

# 原始資料以及其 type
y = [1, 2, 3, 4, 5, "hello"]
arr_y = np.array(y)
print(arr_y.dtype)

"""output (unicode)
<U21
"""

# asarray
as_arr_y = np.asarray(y)
print(as_arr_y)

"""output (只支援一種資料型態，所以元素全部被轉成 string
['1' '2' '3' '4' '5' 'hello']
"""
