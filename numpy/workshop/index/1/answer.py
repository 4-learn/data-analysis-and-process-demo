import numpy as np 
 
x = np.array([[0, 1, 2], 
              [3, 4, 5], 
              [6, 7, 8], 
              [9, 10, 11]])

y = x[[0, 0, 3, 3], [0, 2, 0, 2]]

print(y)
