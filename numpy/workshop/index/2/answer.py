import numpy as np 
 
x = np.array([

[  0,  1,  2],[  3,  4,  5],[  6,  7,  8],[  9,  10,  11],
[  12,  13,  14],[  15,  16,  17],[  18,  19,  20],[  21,  22,  23]

])
print ('數組：' )
print (x)
print ('\n')
rows = np.array([[0,0],[7,7]]) 
cols = np.array([[0,2],[0,2]])

y = x[rows,cols]
print  ('這個數組的四個角元素是：')
print (y)
