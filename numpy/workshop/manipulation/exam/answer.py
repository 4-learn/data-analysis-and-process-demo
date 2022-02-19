import numpy as np

a1 = np.arange(1, 13)

# Q1. reshape to 3x4
a1_2d = a1.reshape(3, 4)
print("Q1. reshape to 3x4")
print(a1_2d)


# Q2. reshape to 3x-1
a1_2d_1 = a1.reshape(3, -1)
print("Q2. reshape to 3x-1")
print(a1_2d_1)

# Q3. reshape to 3x4, row by row
print("Q3. reshape to 3x4, row by row")
print(a1.reshape(3, 4, order='C'))

# Q4. reshape to 3x4, column by column
print("Q4. reshape to 3x4, column by column")
print(a1.reshape(3, 4, order='F'))

# Q5. What is the shape for a1 : a1.reshape(1, -1) ?
print("Q5. What is the shape for a1 : a1.reshape(1, -1)?")
print(a1.reshape(1, -1).shape)

# Q6. ravel the 3x4 array
print("Q6. ravel the 3x4 array")
print(a1_2d.ravel())

# Q7. ravel the 3x4 array column by column
print("Q7. ravel the 3x4 array")
print(a1_2d.ravel(order='F'))

# Q8. create a new array and stack to a1
# new_array =  p.arange(1, 13)
print("Q8. create a new array and stack to a1")
new_array = np.arange(1, 13)
stack0 = np.stack((a1, new_array))
print(stack0)

# Q9. create a new array and hstack to a1
# new_array =  p.arange(1, 13)
print("Q9. create a new array and hstack to a1")
new_array = np.arange(1, 13)
stack0 = np.hstack((a1, new_array))
print(stack0)
