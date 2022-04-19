import numpy as np

x = [1, 2, 3, 4, 5, True]
arr_x = np.array(x)

print(arr_x)
print(arr_x.dtype)

y = [1, 2, 3, 4, 5, "hello"]
arr_y = np.array(y)
print(arr_y.dtype)
