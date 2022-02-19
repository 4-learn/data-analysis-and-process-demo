import numpy as np

a1 = np.arange(1, 13).reshape(3, -1)  # 3_4
a2 = np.arange(13, 25).reshape(3, -1)  # 3_4

a3_0 = np.stack((a1, a2))
print("original:")
print(a3_0)

print("---")
a3_1 = np.stack((a1, a2), axis=1)
print("shape: " + str(a3_1.shape))
print(a3_1)

print("---")
a3_2 = np.stack((a1, a2), axis=2)
print("shape: " + str(a3_2.shape))
print(a3_2)
