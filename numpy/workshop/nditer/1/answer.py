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

# 因為 np.nditer return 是一個 reference
# 所以如果 a 有意動，b 就會跟著異動
