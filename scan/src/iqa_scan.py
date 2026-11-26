#!/usr/bin/env python3
"""
Scan-level Image Quality Assessment (IQA) - v1.1.0

Tools (one or more): snr, si, mi, riciannoiselevel  (snrsi = snr + si, as in v1.0)

Usage:
  XNAT:    iqa_scan.py snr si mi riciannoiselevel          (folders /input, /output)
  EUCAIM:  iqa_scan.py <input_dir> <output_dir> snr si ...
  Folders can also come from the INPUT_DIR / OUTPUT_DIR environment variables.

The series is read once and organised as volumes x slices (see iqa_common.py).

Outputs (the dashboard reads the Excel files by name prefix and fixed cells):
  SNR_Scan_<series>.xlsx/.png, SI_Scan_<series>.xlsx/.png,
  MutualInformation_Scan_<series>.xlsx/.png, RicianNoiseLevel_Scan_<series>.xlsx
    3D: one value per slice (as v1.0); MI = neighbouring slices
    4D: one value per volume (mean over slices; volumes with the same offset /
        b-value averaged); MI = each volume against the first; Rician = median
  IQA_values.csv  every value: per volume x slice (SNR, SI), neighbouring slices in
                  each volume (MI), each volume vs the first (MI), per volume (Rician)
  IQA_meta.json   numSlices, numVolumes, volume axis and coordinates, metrics, version
"""
import os
import sys
import timeit

import numpy as np
import matplotlib
matplotlib.use("Agg")

from iqa_common import (Series, IQAError, TOOL_VERSION, VALUES_FILE, append_values,
                        write_meta, per_volume_rows)

TOOLS = ("snr", "si", "mi", "riciannoiselevel")


# ----------------------------------------------------------------------------
# Arguments
# ----------------------------------------------------------------------------
def parse_args(argv):
    input_dir = os.environ.get("INPUT_DIR", "/input")
    output_dir = os.environ.get("OUTPUT_DIR", "/output")
    # XNAT "select-many" may pass "snr si" as one argument
    args = [a for arg in argv for a in arg.replace(",", " ").split()]
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
    return input_dir, output_dir, tools


# ----------------------------------------------------------------------------
# SNR and Sharpness Index
# ----------------------------------------------------------------------------
def run_snr_si(series, output_dir, want_snr, want_si):
    from snr_calculation import image_snr_si, maskCalc
    from file_management import SNRonlyToExcel, savefig_snr, SItoExcel, savefig_si

    V, Z = series.n_vol, series.n_slices
    snr = np.zeros((V, Z))
    si = np.zeros((V, Z))

    # 4D: signal mask per slice from the brightest volume, so low-signal volumes
    # (e.g. CEST near water saturation) are not segmented on their own.
    ref_masks = None
    if series.is_4d:
        ref = series.reference_volume()
        print(f"[INFO] Signal mask taken from volume {ref + 1} (brightest)")
        ref_masks = [maskCalc(series.data[ref, z])[0] for z in range(Z)]

    for v in range(V):
        for z in range(Z):
            mask = ref_masks[z] if ref_masks is not None else None
            snr[v, z], si[v, z] = image_snr_si(series.data[v, z], mask)

    rows = []
    for v in range(V):
        for z in range(Z):
            if want_snr:
                rows.append({"metric": "snr", "volume": v + 1, "slice": z + 1, "value": snr[v, z]})
            if want_si:
                rows.append({"metric": "si", "volume": v + 1, "slice": z + 1, "value": si[v, z]})
    append_values(output_dir, rows)

    if series.is_4d:
        axis_snr, snr_vals = per_volume_rows(series, snr.mean(axis=1))
        axis_si, si_vals = per_volume_rows(series, si.mean(axis=1))
        x_name = series.axis_name
    else:
        axis_snr = axis_si = [float(z + 1) for z in range(Z)]
        snr_vals, si_vals = list(snr[0]), list(si[0])
        x_name = "Slice number"

    if want_snr:
        savefig_snr(snr_vals, x_name, series.modality, axis_snr, series.series_desc, output_folder=output_dir)
        SNRonlyToExcel(snr_vals, axis_snr, series.modality, series.series_desc,
                       sheet_name='SNR_Metrics', output_folder=output_dir)
        print(f"[snr] mean {np.mean(snr):.3f} dB")
    if want_si:
        savefig_si(si_vals, x_name, series.modality, axis_si, series.series_desc, output_folder=output_dir)
        SItoExcel(si_vals, axis_si, series.modality, series.series_desc,
                  sheet_name='SI_Metrics', output_folder=output_dir)
        print(f"[si] mean {np.mean(si):.3f}")


# ----------------------------------------------------------------------------
# Mutual Information
# ----------------------------------------------------------------------------
def run_mi(series, output_dir):
    from mi_metric import mutualInfo3D
    from file_mgt import mi_to_excel, savefig_mi

    V, Z = series.n_vol, series.n_slices
    rows = []

    # (a) neighbouring slices, in every volume
    mi_slices = np.zeros((V, max(Z - 1, 0)))
    for v in range(V):
        for z in range(Z - 1):
            mi_slices[v, z] = mutualInfo3D(series.data[v, z], series.data[v, z + 1])
            rows.append({"metric": "mi_slices", "volume": v + 1, "slice": z + 1,
                         "slice2": z + 2, "value": mi_slices[v, z]})

    # (b) 4D: each volume against the first one (consistency / motion)
    mi_volumes = []
    if series.is_4d:
        for v in range(1, V):
            mi_volumes.append(mutualInfo3D(series.data[0], series.data[v]))
            rows.append({"metric": "mi_volumes", "volume": 1, "volume2": v + 1,
                         "value": mi_volumes[-1]})
    append_values(output_dir, rows)

    # Excel / PNG read by the dashboard
    if series.is_4d:
        c = series.coords
        labels = [f"{c[0]:.2f}/{c[v]:.2f}" for v in range(1, V)]
        values = mi_volumes
        x_name, first_header = f"{series.axis_name} (first vs each)", "Volume Pair "
    else:
        labels = [f"{z + 1:.2f}/{z + 2:.2f}" for z in range(Z - 1)]
        values = list(mi_slices[0])
        x_name, first_header = "Slice pair", "Slice Pair Number "

    if not values:
        print("[mi] only one slice / volume: nothing to compare")
        return
    mi_to_excel(values, labels, series.modality, series.series_desc, series.file_tag,
                output_folder=output_dir, first_header=first_header)
    savefig_mi(values, labels, x_name, series.modality, series.series_desc, series.file_tag,
               output_folder=output_dir)
    print(f"[mi] {len(values)} value(s), min {np.min(values):.3f}")


# ----------------------------------------------------------------------------
# Rician noise level (MATLAB package)
# ----------------------------------------------------------------------------
def run_rician(series, output_dir):
    """Returns False when skipped (non-MRI data)."""
    if series.modality in ("CT", "PET"):
        print(f"[riciannoiselevel] Rician noise level is only defined for MRI; "
              f"skipped for {series.modality}")
        return False

    import pandas as pd
    try:
        import RicianNoiseLevelPkg
        pkg = RicianNoiseLevelPkg.initialize()
    except Exception as e:
        raise IQAError(f"Error initializing RicianNoiseLevelPkg: {e}")

    levels = []
    for v in range(series.n_vol):
        vol = series.volume(v).astype(np.float64)
        vmax = vol.max()
        if vmax <= 0:
            raise IQAError(f"Volume {v + 1} is empty (max intensity <= 0).")
        # The MATLAB runtime only accepts contiguous arrays (the transposed volume is a view)
        levels.append(float(pkg.RicianSTD_NLMCED(np.ascontiguousarray(vol / vmax))) * 100)
        if series.is_4d:
            print(f"  volume {v + 1}/{series.n_vol}: {levels[-1]:.3f} %")
    try:
        pkg.terminate()
    except Exception:
        pass

    append_values(output_dir, [{"metric": "rician", "volume": v + 1, "value": lv}
                               for v, lv in enumerate(levels)])

    value = float(np.median(levels))  # 3D: the single value
    output_file = f"{output_dir}/RicianNoiseLevel_Scan_{series.file_tag}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Rician Noise Level (%)')
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
                                      'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 12})
    table_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
                                            'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    worksheet.set_column(0, 1, len('Rician Noise level Estimation (%)') + 2)
    worksheet.write(0, 0, "Modality:", header_fmt)
    worksheet.write(0, 1, series.modality, header_fmt)
    worksheet.write(1, 0, "Serie Description:", header_fmt)
    worksheet.write(1, 1, series.series_desc, header_fmt)
    title = 'Rician Noise level Estimation (%)' + (' - median over volumes' if series.is_4d else '')
    worksheet.write(3, 0, title, table_header_fmt)
    worksheet.write(4, 0, round(value, 3), cell_fmt)
    writer.close()
    print(f"[riciannoiselevel] {value:.3f} %" + (" (median over volumes)" if series.is_4d else ""))
    return True


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    start = timeit.default_timer()
    try:
        input_dir, output_dir, tools = parse_args(sys.argv[1:])
        print(f"IQA scan level v{TOOL_VERSION} - tools: {' '.join(tools)}")
        print(f"Input directory:  {input_dir}")
        print(f"Output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        stale = os.path.join(output_dir, VALUES_FILE)
        if os.path.exists(stale):
            os.remove(stale)  # one run = one values table

        series = Series(input_dir)
        done = []
        if "snr" in tools or "si" in tools:
            print("=== SNR / SI ===")
            run_snr_si(series, output_dir, "snr" in tools, "si" in tools)
            done += [t for t in ("snr", "si") if t in tools]
        if "mi" in tools:
            print("=== Mutual Information ===")
            run_mi(series, output_dir)
            done.append("mi")
        if "riciannoiselevel" in tools:
            print("=== Rician noise level ===")
            if run_rician(series, output_dir):
                done.append("rician")
        write_meta(output_dir, series, done)
    except IQAError as e:
        sys.exit(f"[ERROR] {e}")
    print(f"\nCalculation took {timeit.default_timer() - start:.1f} seconds.")


if __name__ == "__main__":
    main()
