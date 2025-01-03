import numpy as np 

arr = np.array([[[1, 2, 3], 
                 [4, 5, 6]], 
                [[7, 8, 9], 
                 [10, 11, 12]]])

indices = np.array([[0, 0, 1],  # 對應第一個維度
                    [0, 0, 0],  # 對應第二個維度
                    [0, 1, 0]]) # 對應第三個維度

values = arr[indices[0], indices[1], indices[2]]

print(values)
