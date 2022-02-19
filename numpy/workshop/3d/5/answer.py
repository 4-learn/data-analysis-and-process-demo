import numpy as np

a1 = np.arange(1, 13).reshape(3, -1)  # 3_4
a2 = np.arange(13, 25).reshape(3, -1)  # 3_4

a3_0 = np.stack((a1, a2), axis=2)

print("--- axis = 2 ---")
a2d = a3_0[:,:,0]
print(a2d)
