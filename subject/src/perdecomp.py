#------------------------------ PERDECOMP ------------------------------

#       Periodic plus Smooth Image Decomposition
#
#               author: Lionel Moisan
#
#   This program is freely available on the web page
#
#   http://www.mi.parisdescartes.fr/~moisan/p+s
#
#   I hope that you will find it useful.
#   If you use it for a publication, please mention
#   this web page and the paper it makes reference to.
#   If you modify this program, please indicate in the
#   code that you did so and leave this message.
#   You can also report bugs or suggestions to
#   lionel.moisan [AT] parisdescartes.fr
#
# This function computes the periodic (p) and smooth (s) components
# of an image (2D array) u
#
# usage:    p = perdecomp(u)    or    [p,s] = perdecomp(u)
#
# note: this function also works for 1D signals (line or column vectors)
#
# v1.0 (01/2014): initial Matlab version from perdecomp.sci v1.2

import numpy as np
import numpy.matlib as matlib
    
def perdecomp(u = None): 
    ny,nx = np.shape(u)

    X = np.arange(1,nx+1)
    Y = np.arange(1,ny+1)
    v = np.zeros((ny,nx))

    v[0,:] = u[0,:] - u[ny-1,:]
    v[ny-1,:] = - v[0,:]
    v[:,0] = v[:,0] + u[:,0] - u[:,nx-1]
    v[:,nx-1] = v[:,nx-1] - u[:,0] + u[:,nx-1]
    
    fx = matlib.repmat(np.cos(2.0 * np.pi * (X - 1) / nx),ny,1)


                  
    fy = matlib.repmat(np.cos(2.0 * np.pi * (np.transpose(Y) - 1) / ny),nx,1)
    fy = np.transpose(fy)
    fx[0,0] = 0.0

    s0 = np.fft.fft2(v)
    s01 = (2.0 - fx - fy)
    s02 = np.fft.ifft2(s0 * 0.5 / s01)
    s = np.real(s02)
    p = u - s

    return p