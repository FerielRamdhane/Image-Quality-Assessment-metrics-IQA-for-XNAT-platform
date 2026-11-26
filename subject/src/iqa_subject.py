#!/usr/bin/env python3
"""
Subject-level (session) Image Quality Assessment (IQA) - v1.1.0

Runs the IQA metrics on EVERY scan of a session and writes one summary Excel file
per metric, with one block of columns per scan (the layout the subject dashboard reads).

Tools (one or more): snr, si, mi, riciannoiselevel  (snrsi = snr + si, as in v1.0)

Usage:
  XNAT:    iqa_subject.py snr si mi riciannoiselevel --session <label>   (folders /input, /output)
  EUCAIM:  iqa_subject.py <input_dir> <output_dir> snr si ... [--session <label>]
  Results go to <output_dir>/<session>/.

Scans: every folder holding DICOM images (XNAT: SCANS/<id>/DICOM). The scan ID is the
name of the folder above "DICOM" (XNAT), otherwise the folder's own name. Each scan is
organised as volumes x slices like the scan-level tool (iqa_common.py). A scan that fails
is reported and skipped; the others are still processed.

Outputs in <output_dir>/<session>/ (the dashboard finds them by these prefixes):
  SNR_Metric_<session>.xlsx, SI_Metric_<session>.xlsx         blocks of 4 columns per scan
  MutualInformation_Metric_<session>.xlsx                       blocks of 5 columns per scan
  RicianNoiseLevel_Metric_<session>.xlsx                        blocks of 3 columns per scan
  SNR_Scan_<id>-<series>.png, SI_Scan_..., MutualInformation_Scan_...   one per scan
    3D scan: per slice; 4D scan: per volume (as the scan level); Rician: median over volumes
  IQA_subject_values.csv   every value, with the scan ID
  IQA_subject_meta.json    per scan: series, modality, slices, volumes, volume axis
"""
import json
import multiprocessing
import os
import sys
import timeit
import traceback

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from iqa_common import Series, IQAError, TOOL_VERSION, find_dicoms, per_volume_rows, safe_name

TOOLS = ("snr", "si", "mi", "riciannoiselevel")
VALUES_FILE = "IQA_subject_values.csv"
META_FILE = "IQA_subject_meta.json"


# ----------------------------------------------------------------------------
# Arguments
# ----------------------------------------------------------------------------
def parse_args(argv):
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    session = "SubjectLevel"
    args = []
    it = iter(argv)
    for a in it:
        if a == "--session":
            session = next(it, session) or session
        else:
            args += a.replace(",", " ").split()
    if len(args) >= 2 and args[0].lower() not in TOOLS + ("snrsi",) and args[1].lower() not in TOOLS + ("snrsi",):
        input_dir, output_dir, args = args[0], args[1], args[2:]
    # "snrsi" (v1.0 name, still in the published usage) = snr + si
    args = [x for a in args for x in (["snr", "si"] if a.lower() == "snrsi" else [a])]
    tools = []
    for a in args:
        t = a.lower()
        if t not in TOOLS:
            raise IQAError(f"Unknown tool: {a}. Available tools: {', '.join(TOOLS)}")
        if t not in tools:
            tools.append(t)
    if not tools:
        raise IQAError(f"No tool given. Available tools: {', '.join(TOOLS)}")
    return input_dir, output_dir, tools, safe_name(session)


# ----------------------------------------------------------------------------
# Finding the scans
# ----------------------------------------------------------------------------
def find_scan_folders(input_dir):
    """[(scan_id, folder)] for every folder holding DICOM images."""
    dicom_dirs = []
    for dir_name, _, files in os.walk(input_dir):
        if os.path.basename(dir_name).upper() == "DICOM" and files:
            dicom_dirs.append(dir_name)
    if not dicom_dirs:  # not an XNAT session layout: any folder with DICOM images
        for dir_name, _, files in os.walk(input_dir):
            if files and find_dicoms_in(dir_name, first_only=True):
                dicom_dirs.append(dir_name)

    scans = []
    for d in sorted(dicom_dirs):
        if os.path.basename(d).upper() == "DICOM":
            scan_id = os.path.basename(os.path.dirname(d))
        else:
            scan_id = os.path.basename(d)
        scans.append((scan_id, d))

    def sort_key(s):  # scan IDs like 1, 2, 10, 3-MR1 in natural order
        head = s[0].split("-")[0]
        return (int(head) if head.isdigit() else 10 ** 9, s[0])
    return sorted(scans, key=sort_key)


def find_dicoms_in(folder, first_only=False):
    """DICOM images directly in folder (not in sub-folders)."""
    import pydicom
    found = []
    for fn in sorted(os.listdir(folder)):
        path = os.path.join(folder, fn)
        if not os.path.isfile(path):
            continue
        try:
            hdr = pydicom.dcmread(path, stop_before_pixels=True)
        except Exception:
            continue
        if "Rows" in hdr and "Columns" in hdr:
            found.append(path)
            if first_only:
                break
    return found


# ----------------------------------------------------------------------------
# Per-scan computation (Python metrics; run in parallel over scans)
# ----------------------------------------------------------------------------
def compute_python_metrics(job):
    """job = (scan_id, folder, tools). Returns a dict, or {'error': ...}."""
    scan_id, folder, tools = job
    try:
        series = Series(folder)
        out = {"scan_id": scan_id, "series": series}
        V, Z = series.n_vol, series.n_slices

        if "snr" in tools or "si" in tools:
            from snr_calculation import image_snr_si, maskCalc
            snr = np.zeros((V, Z))
            si = np.zeros((V, Z))
            ref_masks = None
            if series.is_4d:
                ref = series.reference_volume()
                ref_masks = [maskCalc(series.data[ref, z])[0] for z in range(Z)]
            for v in range(V):
                for z in range(Z):
                    mask = ref_masks[z] if ref_masks is not None else None
                    snr[v, z], si[v, z] = image_snr_si(series.data[v, z], mask)
            out["snr"], out["si"] = snr, si

        if "mi" in tools:
            from mi_metric import mutualInfo3D
            mi_slices = np.zeros((V, max(Z - 1, 0)))
            for v in range(V):
                for z in range(Z - 1):
                    mi_slices[v, z] = mutualInfo3D(series.data[v, z], series.data[v, z + 1])
            mi_volumes = [mutualInfo3D(series.data[0], series.data[v]) for v in range(1, V)]
            out["mi_slices"], out["mi_volumes"] = mi_slices, mi_volumes

        # drop the pixel data before sending the result back to the main process
        # (Rician reloads it scan by scan)
        series.data = None
        return out
    except Exception as e:
        if not isinstance(e, IQAError):
            traceback.print_exc()
        return {"scan_id": scan_id, "error": str(e)}


def compute_rician(folder, pkg):
    """Rician noise level (%) per volume, or None for CT / PET."""
    series = Series(folder)
    if series.modality in ("CT", "PET"):
        print(f"  Rician noise level is only defined for MRI; skipped for {series.modality}")
        return None
    levels = []
    for v in range(series.n_vol):
        vol = series.volume(v).astype(np.float64)
        vmax = vol.max()
        if vmax <= 0:
            raise IQAError(f"Volume {v + 1} is empty (max intensity <= 0).")
        levels.append(float(pkg.RicianSTD_NLMCED(np.ascontiguousarray(vol / vmax))) * 100)
    return levels


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    start = timeit.default_timer()
    try:
        input_dir, output_dir, tools, session = parse_args(sys.argv[1:])
    except IQAError as e:
        sys.exit(f"[ERROR] {e}")

    out_dir = os.path.join(output_dir, session)
    os.makedirs(out_dir, exist_ok=True)
    print(f"IQA subject level v{TOOL_VERSION} - tools: {' '.join(tools)}")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {out_dir}")

    scans = find_scan_folders(input_dir)
    if not scans:
        sys.exit(f"[ERROR] No DICOM images found under {input_dir}")
    print(f"[INFO] {len(scans)} scan(s): {', '.join(s for s, _ in scans)}")

    values_rows = []
    meta_scans = []
    failed = []

    # --- Python metrics (SNR, SI, MI), several scans at a time -------------------
    results = {}
    py_tools = [t for t in tools if t in ("snr", "si", "mi")]
    if py_tools:
        jobs = [(sid, folder, py_tools) for sid, folder in scans]
        n_proc = max(1, min(len(jobs), multiprocessing.cpu_count(), 4))
        with multiprocessing.Pool(n_proc) as pool:
            for res in pool.imap(compute_python_metrics, jobs):
                sid = res["scan_id"]
                if "error" in res:
                    print(f"[WARN] Scan {sid} skipped: {res['error']}")
                    failed.append(sid)
                else:
                    s = res["series"]
                    print(f"[INFO] Scan {sid}: {s.modality} - {s.series_desc} - "
                          f"{s.n_slices} slices x {s.n_vol} volume(s)")
                    results[sid] = res

    # --- Rician (MATLAB), one scan at a time ------------------------------------
    rician = {}
    if "riciannoiselevel" in tools:
        try:
            import RicianNoiseLevelPkg
            pkg = RicianNoiseLevelPkg.initialize()
        except Exception as e:
            sys.exit(f"[ERROR] Error initializing RicianNoiseLevelPkg: {e}")
        for sid, folder in scans:
            if sid in failed:
                continue
            print(f"[INFO] Rician noise level, scan {sid}")
            try:
                levels = compute_rician(folder, pkg)
                if levels is not None:
                    rician[sid] = levels
            except Exception as e:
                print(f"[WARN] Rician skipped for scan {sid}: {e}")
        try:
            pkg.terminate()
        except Exception:
            pass

    # --- Write the outputs ------------------------------------------------------
    from file_management import SNRtodf, SItodf, save_snr_dfs, save_si_dfs, savefig_snr, savefig_si
    from file_mgt import save_dfs as save_mi_dfs, savefig_mi
    from file_management_riciannoise import save_dfs as save_rician_dfs

    snr_dfs, si_dfs, mi_dfs, ric_dfs = [], [], [], []
    ids, types, names = [], [], []
    ric_ids, ric_types, ric_names = [], [], []
    series_by_id = {}

    for sid, _ in scans:
        res = results.get(sid)
        s = res["series"] if res else None
        if s is None and sid in rician:  # only Rician was requested
            s = Series(dict(scans)[sid]); s.data = None
        if s is None:
            continue
        series_by_id[sid] = s
        png_label = f"{sid}-{s.file_tag}"
        meta_scans.append({"scanId": sid, "seriesDescription": s.series_desc, "modality": s.modality,
                           "numSlices": s.n_slices, "numVolumes": s.n_vol,
                           "volumeAxis": s.axis_name if s.is_4d else None,
                           "volumeCoords": s.coords if s.is_4d else None})

        if res and "snr" in res:
            snr, si = res["snr"], res["si"]
            if s.is_4d:
                axis, snr_v = per_volume_rows(s, snr.mean(axis=1))
                _, si_v = per_volume_rows(s, si.mean(axis=1))
                x_name = s.axis_name
            else:
                axis = [float(z + 1) for z in range(s.n_slices)]
                snr_v, si_v, x_name = list(snr[0]), list(si[0]), "Slice number"
            for v in range(s.n_vol):
                for z in range(s.n_slices):
                    if "snr" in tools:
                        values_rows.append((sid, "snr", v + 1, z + 1, "", "", snr[v, z]))
                    if "si" in tools:
                        values_rows.append((sid, "si", v + 1, z + 1, "", "", si[v, z]))
            snr_dfs.append(SNRtodf(snr_v, axis, x_name))
            si_dfs.append(SItodf(si_v, axis, x_name))
            if "snr" in tools:
                savefig_snr(snr_v, x_name, s.modality, png_label, axis, output_folder=out_dir, session=session)
            if "si" in tools:
                savefig_si(si_v, x_name, s.modality, png_label, axis, output_folder=out_dir, session=session)

        if res and "mi_slices" in res:
            mi_slices, mi_volumes = res["mi_slices"], res["mi_volumes"]
            for v in range(s.n_vol):
                for z in range(s.n_slices - 1):
                    values_rows.append((sid, "mi_slices", v + 1, z + 1, "", z + 2, mi_slices[v, z]))
            for v, val in enumerate(mi_volumes, start=2):
                values_rows.append((sid, "mi_volumes", 1, "", v, "", val))
            if s.is_4d:
                c = s.coords
                labels = [f"{c[0]:.2f}/{c[v]:.2f}" for v in range(1, s.n_vol)]
                vals, x_name = list(mi_volumes), f"{s.axis_name} (first vs each)"
            else:
                labels = [f"{z + 1:.2f}/{z + 2:.2f}" for z in range(s.n_slices - 1)]
                vals, x_name = list(mi_slices[0]), "Slice pair"
            if vals:
                mi_dfs.append(pd.DataFrame([vals], columns=labels, index=["Mutual Information"]))
                savefig_mi(vals, labels, x_name, s.modality, s.series_desc, png_label,
                           output_folder=out_dir, session=session)
            else:
                mi_dfs.append(pd.DataFrame())

        ids.append(sid); types.append(s.modality); names.append(s.series_desc)

        if sid in rician:
            levels = rician[sid]
            for v, lv in enumerate(levels, start=1):
                values_rows.append((sid, "rician", v, "", "", "", lv))
            ric_dfs.append(pd.DataFrame([float(np.median(levels))], columns=['Rician Noise Level (%)']))
            ric_ids.append(sid); ric_types.append(s.modality); ric_names.append(s.series_desc)

    # Summary Excel files (only the requested metrics, only scans with results)
    def keep(dfs, *lists):
        idx = [i for i, d in enumerate(dfs) if d is not None and not d.empty]
        return [[lst[i] for i in idx] for lst in (dfs,) + lists]

    if "snr" in tools and snr_dfs:
        d, i, t, n = keep(snr_dfs, ids, types, names)
        save_snr_dfs(d, i, t, n, spaces=1, output_folder=out_dir, session=session)
    if "si" in tools and si_dfs:
        d, i, t, n = keep(si_dfs, ids, types, names)
        save_si_dfs(d, i, t, n, spaces=1, output_folder=out_dir, session=session)
    if "mi" in tools and mi_dfs:
        d, i, t, n = keep(mi_dfs, ids, types, names)
        if d:
            save_mi_dfs(d, i, 'MutualInformation_Metric', t, n, spaces=3, output_folder=out_dir, session=session)
    if ric_dfs:
        save_rician_dfs(ric_dfs, ric_ids, 'Rician_Noise_Level_Metric', ric_types, ric_names,
                        spaces=1, output_folder=out_dir, session=session)

    with open(os.path.join(out_dir, VALUES_FILE), "w") as f:
        f.write("scan,metric,volume,slice,volume2,slice2,value\n")
        for sid, m, v, z, v2, z2, val in values_rows:
            f.write(f"{sid},{m},{v},{z},{v2},{z2},{float(val):.6g}\n")
    with open(os.path.join(out_dir, META_FILE), "w") as f:
        json.dump({"toolVersion": TOOL_VERSION, "session": session, "metrics": tools,
                   "scans": meta_scans, "failedScans": failed}, f, indent=2)

    print(f"\n[INFO] Done: {len(series_by_id)} scan(s) processed"
          + (f", {len(failed)} skipped ({', '.join(failed)})" if failed else ""))
    print(f"Calculation took {timeit.default_timer() - start:.1f} seconds.")
    for fn in sorted(os.listdir(out_dir)):
        print("  ", fn)


if __name__ == "__main__":
    main()
