import numpy as np
y = np.array([[[1,2],[3,4]],[[5,6],[7,8]]])
print(np.swapaxes(y,1,2))
print(np.swapaxes(y,0,2))
