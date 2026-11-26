"""
iqa_common.py - shared DICOM loading for the scan-level IQA tools (SNR, SI, MI, Rician).

The series is read ONCE and organised as volumes x slices, with the same rules as
NLmCED (src/nlmced.py), so every tool and dashboard agrees on what a volume is:

  * images are placed by their position along the slice direction
    (ImagePositionPatient . slice normal; fallback SliceLocation, then InstanceNumber)
  * images at the same position are the volumes of a 4D series, ordered by
    TemporalPositionIdentifier, then InstanceNumber
  * 3D series = 1 volume

For Bruker CEST (private tags 0x1061) the saturation offset of each volume, and for
DWI the b-value, is kept as the volume's coordinate (axis label).
"""
import json
import os
import re

import numpy as np
import pydicom

TOOL_VERSION = "1.1.0"


class IQAError(Exception):
    """Error with a message meant for the user."""


# ----------------------------------------------------------------------------
# Finding and grouping the DICOM files
# ----------------------------------------------------------------------------
def find_dicoms(input_dir):
    """[(path, header)] for every readable image DICOM under input_dir (any file name)."""
    found = []
    for dir_name, _, files in os.walk(input_dir):
        for fn in sorted(files):
            path = os.path.join(dir_name, fn)
            try:
                hdr = pydicom.dcmread(path, stop_before_pixels=True)
            except Exception:
                continue
            if "Rows" not in hdr or "Columns" not in hdr:
                continue
            found.append((path, hdr))
    return found


def _slice_position(hdr):
    ipp = hdr.get("ImagePositionPatient")
    iop = hdr.get("ImageOrientationPatient")
    if ipp is not None and iop is not None:
        row, col = np.array(iop[:3], float), np.array(iop[3:], float)
        return float(np.dot(np.cross(row, col), np.array(ipp, float)))
    if hdr.get("SliceLocation") is not None:
        return float(hdr.SliceLocation)
    return None


def _volume_key(hdr):
    tpi = hdr.get("TemporalPositionIdentifier")
    return (int(tpi) if tpi is not None else 0, int(hdr.get("InstanceNumber", 0)))


def organise(entries):
    """grid[v][z] = (path, header); v = volume, z = slice (ordered by position)."""
    if any(int(h.get("NumberOfFrames", 1)) > 1 for _, h in entries):
        raise IQAError("Enhanced multi-frame DICOM (NumberOfFrames > 1) is not supported. "
                       "Please export the series as one file per slice.")
    def in_acquisition_order(reason):
        # v1.0 behaviour: every image is one "slice", in acquisition order
        print(f"[WARN] {reason}: images are treated one by one in acquisition order "
              f"(InstanceNumber), as in v1.0")
        return [sorted(entries, key=lambda e: int(e[1].get("InstanceNumber", 0)))]

    positions = [_slice_position(h) for _, h in entries]
    if any(p is None for p in positions):
        return in_acquisition_order("No slice geometry in the headers")

    orientations = {tuple(round(float(x), 3) for x in h.ImageOrientationPatient)
                    for _, h in entries if h.get("ImageOrientationPatient") is not None}
    if len(orientations) > 1:
        return in_acquisition_order(f"Images with {len(orientations)} different orientations "
                                    f"(e.g. a 3-plane localizer), not a volume")

    by_pos = {}
    for entry, pos in zip(entries, positions):
        by_pos.setdefault(round(pos, 3), []).append(entry)
    sorted_pos = sorted(by_pos)
    counts = {len(by_pos[p]) for p in sorted_pos}
    if len(counts) != 1:
        return in_acquisition_order(f"Slice positions have different numbers of images "
                                    f"({sorted(counts)}), not a regular 3D/4D volume")
    n_vol = counts.pop()
    for p in sorted_pos:
        by_pos[p].sort(key=lambda e: _volume_key(e[1]))
    return [[by_pos[p][v] for p in sorted_pos] for v in range(n_vol)]


# ----------------------------------------------------------------------------
# Series description
# ----------------------------------------------------------------------------
def _text(hdr, tag):
    if tag not in hdr:
        return ""
    val = hdr[tag].value
    if isinstance(val, (list, tuple, pydicom.multival.MultiValue)):
        val = "\\".join(map(str, val))
    return str(val)


def _bruker_cest(hdr):
    for tag in ((0x1061, 0x1002), (0x1061, 0x1001)):
        if "cest" in _text(hdr, tag).lower():
            return True
    return False


def modality_label(hdr):
    """'CEST MRI', 'DWI MRI', 'DCE MRI', 'CT', 'PET' or 'MRI' (same labels as v1.0)."""
    modality = _text(hdr, (0x0008, 0x0060)).upper()
    if modality == "CT":
        return "CT"
    if modality in ("PT", "PET"):
        return "PET"
    protocol = (_text(hdr, (0x0018, 0x1030)) + " " + _text(hdr, (0x0008, 0x103E))).lower()
    if _bruker_cest(hdr) or "cest" in protocol:
        return "CEST MRI"
    if "diffusion" in protocol or "dwi" in protocol:
        return "DWI MRI"
    if "dce" in protocol:
        return "DCE MRI"
    return "MRI"


def safe_name(text):
    """Series description usable in a file name."""
    text = re.sub(r"[^A-Za-z0-9._+-]+", "_", text).strip("_")
    return text or "series"


class Series:
    """A DICOM series loaded once: data[v, z] = 2D pixel array."""

    def __init__(self, input_dir):
        entries = find_dicoms(input_dir)
        if not entries:
            listing = os.listdir(input_dir) if os.path.isdir(input_dir) else "folder not found"
            raise IQAError(f"No DICOM images found in {input_dir} (contents: {listing})")
        self.grid = organise(entries)
        self.n_vol, self.n_slices = len(self.grid), len(self.grid[0])
        self.is_4d = self.n_vol > 1

        first_hdr = self.grid[0][0][1]
        self.modality = modality_label(first_hdr)
        self.series_desc = _text(first_hdr, (0x0008, 0x103E)) or "Unknown series"
        self.file_tag = safe_name(self.series_desc)

        # Pixel data, read once
        arrays = [[pydicom.dcmread(p).pixel_array for p, _ in vol] for vol in self.grid]
        shape = arrays[0][0].shape
        for vol in arrays:
            for a in vol:
                if a.shape != shape:
                    raise IQAError(f"Image size mismatch ({a.shape} vs {shape}).")
        self.data = np.array(arrays)  # (V, Z, rows, cols), original pixel type

        self.axis_name, self.coords = self._volume_coordinates()
        print(f"[INFO] {self.modality} - {self.series_desc}: {self.n_slices} slices x "
              f"{self.n_vol} volume(s){' (4D)' if self.is_4d else ''}")

    def _volume_coordinates(self):
        """Axis name + one coordinate per volume (offset, b-value or volume number)."""
        if not self.is_4d:
            return "Slice number", [1.0]
        hdrs = [vol[0][1] for vol in self.grid]
        try:
            if _bruker_cest(hdrs[0]) and all((0x1061, 0x1015) in h for h in hdrs):
                vals = [float(h[0x1061, 0x1015].value) for h in hdrs]
                if len(set(vals)) > 1:
                    return "Offsets", vals
            if all((0x0018, 0x9087) in h for h in hdrs):
                vals = [float(h[0x0018, 0x9087].value) for h in hdrs]
                if len(set(vals)) > 1:
                    return "b-values", vals
        except (TypeError, ValueError):
            pass
        return "Volume", [float(v + 1) for v in range(self.n_vol)]

    def volume(self, v):
        """Volume v as (rows, cols, slices), like the v1.0 Rician code."""
        return np.ascontiguousarray(np.transpose(self.data[v], (1, 2, 0)))

    def reference_volume(self):
        """Index of the brightest volume (used for the 4D signal mask)."""
        return int(np.argmax(self.data.reshape(self.n_vol, -1).mean(axis=1)))


# ----------------------------------------------------------------------------
# Detailed outputs for the 4D dashboards (names must NOT start with SNR / SI /
# MutualInformation / RicianNoiseLevel: the plugin finds the Excel files by prefix)
# ----------------------------------------------------------------------------
VALUES_FILE = "IQA_values.csv"
META_FILE = "IQA_meta.json"


def append_values(output_dir, rows):
    """rows: dicts with metric, volume, slice, slice2, volume2, value (slice/volume 1-based)."""
    path = os.path.join(output_dir, VALUES_FILE)
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new:
            f.write("metric,volume,slice,volume2,slice2,value\n")
        for r in rows:
            f.write(f"{r['metric']},{r.get('volume', '')},{r.get('slice', '')},"
                    f"{r.get('volume2', '')},{r.get('slice2', '')},{float(r['value']):.6g}\n")


def write_meta(output_dir, series, metrics):
    meta = {
        "toolVersion": TOOL_VERSION,
        "modality": series.modality,
        "seriesDescription": series.series_desc,
        "numSlices": series.n_slices,
        "numVolumes": series.n_vol,
        "volumeAxis": series.axis_name if series.is_4d else None,
        "volumeCoords": series.coords if series.is_4d else None,
        "metrics": list(metrics),
    }
    with open(os.path.join(output_dir, META_FILE), "w") as f:
        json.dump(meta, f, indent=2)


def per_volume_rows(series, values_by_volume):
    """
    Rows for the legacy per-volume Excel/PNG (4D): one value per volume coordinate.
    Volumes with the same offset / b-value are averaged and sorted by coordinate,
    as in v1.0; with plain volume numbers, the acquisition order is kept.
    """
    if series.axis_name == "Volume":
        return list(series.coords), list(values_by_volume)
    groups = {}
    for c, val in zip(series.coords, values_by_volume):
        groups.setdefault(c, []).append(val)
    coords = sorted(groups)
    return coords, [float(np.mean(groups[c])) for c in coords]
