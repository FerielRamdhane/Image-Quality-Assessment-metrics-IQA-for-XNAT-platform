"""
Created on Oct 10, 2023

@author: Aina Nasolo, modified by Feriel Ramdhane


"""
#------------------------- sharpness_index -------------------------
#
# available preprocessing modes are:
#
# pmode = 0             raw sharpness index of u
# pmode = 1             sharpness index of the periodic component of u
# pmode = 2             sharpness index of the 1/2,1/2-translated of u
# pmode = 3 (default)   sharpness index of the 1/2,1/2-translated
#                       of the periodic component of u
#
# Default mode (pmode = 3) should be used, unless you want to work on very

# dependencies: dequant, perdecomp, logerfc

import numpy as np
from perdecomp import perdecomp
from dequant import dequant
from logerfc import logerfc
from math import log10
import pydicom

def sharpness_index(u,pmode): 
    if (pmode == 1) or (pmode == 3):
        u = perdecomp(u)
    
    if pmode == 2:
        u = dequant(u)
    
    u =  np.array(u)
    ny,nx = np.shape(u)

    val = np.append(np.arange(1,nx),0)
    val2 = np.append(np.arange(1,ny),0)
   
   
    gx = u[:,val] - u[:,0:nx]
    fgx = np.fft.fft2(gx)

    gy = u[val2,:] - u[0:ny,:]
    fgy = np.fft.fft2(gy)

    tv = sum(sum(np.abs(gx) + np.abs(gy)))
    Gxx = np.real(np.fft.ifft2(np.multiply(fgx,np.conj(fgx))))
    Gyy = np.real(np.fft.ifft2(np.multiply(fgy,np.conj(fgy))))
    Gxy = np.real(np.fft.ifft2(np.multiply(fgx,np.conj(fgy))))

    oomega = lambda t = None: np.real(np.multiply(t,np.arcsin(t)) + np.sqrt(1 - t ** 2) - 1)
    var = 0
    axx = Gxx[0,0]
    if axx > 0:
        var = var + axx * sum(sum(oomega(Gxx / axx)))
    
    ayy = Gyy[0,0]
    if ayy > 0:
        var = var + ayy * sum(sum(oomega(Gyy / ayy)))
    
    axy = np.sqrt(axx * ayy)
    if axy > 0:
        var = var + 2 * axy * sum(sum(oomega(Gxy / axy)))
    
    var = var * 2 / np.pi
    if var > 0:
        # t = ( E(TV)-tv )/sqrt(var(TV))
        t = ((np.sqrt(axx) + np.sqrt(ayy)) * np.sqrt(2 * nx * ny / np.pi) - tv) / np.sqrt(var)
        # si = -log10(P(N(0,1)>t))
        si = - logerfc(t / np.sqrt(2.0)) / np.log(10.0) + log10(2.0)
    else:
        si = 0
    
    return si

if __name__ == "__main__" :
    u = pydicom.dcmread('./input/MRI150.dcm').pixel_array
    pmode = 3
    si = sharpness_index(u, pmode)
    print(si)