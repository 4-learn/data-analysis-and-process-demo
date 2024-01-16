import numpy as np

print("題目:"
np.random.seed(1234)
arr = np.arange(9)
print(arr)

np.random.shuffle(arr)
arr = np.arange(9)
np.random.shuffle(arr)
print(arr)

print("答案")
print("亂數種子需要每次都定義")
for index in range(3):
    # np.random.seed(1234)
    arr = np.arange(9)
    np.random.shuffle(arr)
    print(arr)
