import numpy as np

a = np.array([[1], [2], [3], [4], [5]]).flat
b = np.array([[[[[1, 2, 3, 4, 5]]]]]).flat
c = np.array([1, 2, 3, 4, 5]).flat

for obj in a:
    print(obj)
for obj in b:
    print(obj)
for obj in c:
    print(obj)
