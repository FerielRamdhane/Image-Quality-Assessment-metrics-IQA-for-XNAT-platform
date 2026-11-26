#--------------------------------- LOGERFC ---------------------------------
#
# author: Lionel Moisan
#
# Compute the logarithm of the complementary error function for any x
#
# usage:   y = logerfc(x)
#
# for x<=20, logerfc(x) = log(erfc(x))
# for x>20, a direct asymptotic formula is used to avoid machine underflow
#
# note: x can also be a vector or a matrix
#
# v1.0 (02/2014): initial version
# v1.1 (02/2014): extension to x vector or matrix

import numpy as np
import math
    
def logerfc(x): 
    y = np.float64(x)
    if x>20.0: 
     T= x[x > 20.0]
     T = np.float64(T)
    else: 
       T = 0.0
    if T > 0.0:
        X = np.float64(T)
        z = X ** (- 2.0)
        s = 1
        for k in np.arange(8,1+- 1,- 1).reshape(-1):
            s = 1 - np.multiply((k - 0.5) * z,s)

        y = - 0.5 * np.log(np.pi) - X ** 2 + np.log((s / X))
    else: 
       y = np.log(math.erfc(x))



    return y
    
