"""
SNR and Sharpness Index of one 2D image.

v1.1.0: one function per image (image_snr_si). The formulas are unchanged from v1.0.
Fixed: the mask given for CEST/DCE/DWI was the whole tuple returned by maskCalc()
instead of the mask itself.
"""
import numpy as np
import cv2

from sharpness_index import sharpness_index


def image_snr_si(image, mask=None, eps=1e-3):
    """
    SNR (dB) and Sharpness Index of one 2D image.

    mask : boolean signal mask; None = computed from this image (Otsu), as v1.0 did
           for 3D scans. For 4D series the caller passes the mask of the reference
           (brightest) volume, so low-signal volumes are not segmented on their own.
    """
    image = np.asarray(image, dtype=np.float64)
    image_norm = (image - image.min()) / max(image.max() - image.min(), eps)

    if mask is None:
        mask, _, _ = maskCalc(image)

    img_sig = image_norm[mask]
    signal_mean = np.mean(img_sig) if img_sig.size > 0 else eps
    noise_std = max(calculate_noise(image_norm[~mask]), eps)

    snr = max(10 * np.log10((signal_mean + eps) / noise_std), eps)

    si = float(np.mean(sharpness_index(image_norm, 3)))  # may come back as a 1-element array
    if np.isnan(si) or np.isinf(si):
        si = -100.0
    return float(snr), si


def maskCalc(image):
    """
    Compute a binary mask of the object in the image using Otsu thresholding.
    Returns (mask, contrast-enhanced image, denoised image).
    """
    image = np.asarray(image, dtype=np.float64)
    image_int = ((image - image.min()) / max(image.max() - image.min(), 1e-6) * 255).astype(np.uint8)

    alpha = 10
    beta = 0
    image_ct = cv2.convertScaleAbs(image_int, alpha=alpha, beta=beta)

    image_denoised = cv2.fastNlMeansDenoising(image_ct, h=81, templateWindowSize=7, searchWindowSize=21)

    _, im_otsu = cv2.threshold(image_denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    element = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(im_otsu, cv2.MORPH_CLOSE, element)
    mask = cv2.erode(mask, element, iterations=1)

    return mask.astype(bool), image_ct, image_denoised


def calculate_noise(img_bg):
    """Noise standard deviation from background pixels."""
    if img_bg.size == 0:
        return 1e-3
    return np.std(img_bg)
