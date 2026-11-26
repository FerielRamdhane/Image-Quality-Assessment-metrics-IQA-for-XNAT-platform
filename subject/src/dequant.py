#--------------------------------- DEQUANT ---------------------------------
#
# author: Lionel Moisan
#
# Image dequantization using a (1/2,1/2) translation in Fourier domain
#
# reference: A. Desolneux, S. Ladjal, L. Moisan, J.-M. Morel,
# "Dequantizing image orientation", IEEE Transactions on Image Processing,
# vol. 11(10), pp. 1129-1140, 2002.
#
# usage:   v = dequant(u)
#
# input: a 2D array (Matlab matrix)
# output: a 2D array (same size as u)
#
# v1.0 (02/2014): initial version

import numpy as np
    
def dequant(u): 
    ny,nx = np.shape(u)
    mx = int(np.floor(nx / 2))
    my = int(np.floor(ny / 2))
    Tx = np.exp(- 1j * np.pi / nx * (np.mod(np.arange(mx,mx + nx - 1+1),nx) - mx))
    Ty = np.exp(- 1j * np.pi / ny * (np.mod(np.arange(my,my + ny - 1+1),ny) - my))
    v = np.real(np.fft.ifft2(np.multiply(np.fft.fft2(u),(np.transpose(Ty) * Tx))))
    return v