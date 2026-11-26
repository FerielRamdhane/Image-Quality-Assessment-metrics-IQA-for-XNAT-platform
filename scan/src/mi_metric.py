"""
Mutual Information between two images or volumes (unchanged from v1.0 mi.py).
@authors: Feriel Ramdhane and Aina Nasolo
"""
import numpy as np
import SimpleITK as sitk


def mutualInfo2D(Im1, Im2):
    hist_2d, _, _ = np.histogram2d(Im1.ravel(), Im2.ravel(), bins=20)
    pxy = hist_2d / float(np.sum(hist_2d))
    px = np.sum(pxy, axis=1)
    py = np.sum(pxy, axis=0)
    px_py = px[:, None] * py[None, :]
    nzs = pxy > 0
    return np.sum(pxy[nzs] * np.log(pxy[nzs] / px_py[nzs]))


def mutualInfo3D(Im1, Im2):
    img1 = sitk.Cast(sitk.GetImageFromArray(np.asarray(Im1)), sitk.sitkFloat32)
    img2 = sitk.Cast(sitk.GetImageFromArray(np.asarray(Im2)), sitk.sitkFloat32)
    try:
        registration_method = sitk.ImageRegistrationMethod()
        registration_method.SetMetricAsMattesMutualInformation()
        metric_value = registration_method.MetricEvaluate(img1, img2)
    except Exception:
        metric_value = mutualInfo2D(np.asarray(Im1), np.asarray(Im2))
    return float(np.abs(metric_value))
