import numpy as np 
 
a = np.arange(0,60,5) 
a = a.reshape(3,4)  
print ('原始：')
print (a)
print ('\n')
print ('C order：')
for x in np.nditer(a, order =  'C'):  
    print (x, end=", " )
print ('\n')
print ('F style：')
for x in np.nditer(a, order =  'F'):  
    print (x, end=", " )
