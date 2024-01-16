import numpy as np 
 
a = np.arange(0,60,5) 
a = a.reshape(3,4)
b = np.nditer(a)
a[0] = 100

print(type(b))
print("---")

print(a[0])

print("---")
for x in b:  
    print (x)

# 原因
# a 為 ndarray ( mutable object )
# 當 mutable 物件被傳遞到 b class 屬性時，
# 所以如果 a 有異動，b 就會跟著異動
