import numpy as np

mu = 0
sigma = 0.1 # mean and standard deviation
size = 1000
s = np.random.normal(mu, sigma, size)
print(str(s.size))
