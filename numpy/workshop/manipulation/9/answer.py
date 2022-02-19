import numpy as np
 
a = np.arange(9).reshape(3,3) 
b = a.flat

print(type(b))
a[0,0] = 100

print ('ndarray：')
for row in a:
    print (row)
 
print ('迭代後：')
for element in b:
    print (element)

# output
"""
<class 'numpy.flatiter'>
ndarray：
[100   1   2]
[3 4 5]
[6 7 8]
迭代後：
100
1
2
3
4
5
6
7
8
"""

# 因為迭代器是 call by reference
# 所以 a 異動，b 也異動
