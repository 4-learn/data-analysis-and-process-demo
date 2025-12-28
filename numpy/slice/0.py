import numpy as np
 
a = np.arange(10)
# 從索引 2 開始到索引 7，間隔 2
s = slice(2,7,2)
print (a[s])
