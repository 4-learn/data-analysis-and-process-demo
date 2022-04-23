from tensorflow.keras.utils import to_categorical

arr = [0, 1, 2, 3]
a = to_categorical(arr, num_classes = 6)

print(a)


""" Output 
[[1. 0. 0. 0. 0. 0.] ==> 剛好是 num_classes 的數量 6
 [0. 1. 0. 0. 0. 0.]
 [0. 0. 1. 0. 0. 0.]
 [0. 0. 0. 1. 0. 0.]]

子 array 共 4 個，剛好代表 0, 1, 2, 3
"""
