import numpy as np

a = np.array([[10, 11, 12],[13, 14, 15]])

print(np.argmax(a, axis=0))
print(np.argmax(a, axis=1))
