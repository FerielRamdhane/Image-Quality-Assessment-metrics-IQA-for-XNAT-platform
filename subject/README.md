# Image Quality Assessment (IQA), subject (session) level

Runs the IQA metrics on **every scan of a session** and writes one summary per metric, with one block per scan, plus one chart per scan. Works for 3D and 4D scans.

| Tool | Metric | 3D scan | 4D scan (e.g. CEST, DCE, DWI) |
| --- | --- | --- | --- |
| `snr` | Signal-to-Noise Ratio (dB) | per slice | per volume (mean over slices) |
| `si` | Sharpness Index | per slice | per volume (mean over slices) |
| `mi` | Mutual Information | neighbouring slices | each volume against the first |
| `riciannoiselevel` | Rician noise level (%), MRI only (skipped for CT and PET) | one value | median over volumes |

All values, per volume × slice, are also written to `IQA_subject_values.csv`.

## Usage
EUCAIM:
```bash
jobman submit -i iqaxnat_subject -- <input_dir> <output_dir> snr si mi riciannoiselevel --session <label>
```
Docker:
```bash
docker run --rm -v <session folder>:/data/in -v <out>:/data/out iqaxnat_subject:1.1.0 /data/in /data/out snr si mi riciannoiselevel --session MySession
```
Results go to `<output_dir>/<label>/`.

## Input data
* A session folder. Scans are the folders holding DICOM images (XNAT layout: `SCANS/<id>/DICOM`; the scan ID is the folder above `DICOM`).
* Each scan is organised as volumes × slices, exactly like the scan-level tool.
* A scan that cannot be processed is reported in the log and skipped; the other scans are still processed (`failedScans` in `IQA_subject_meta.json`).

## Outputs
* `SNR_Metric_<label>.xlsx`, `SI_Metric_<label>.xlsx`, `MutualInformation_Metric_<label>.xlsx`, `RicianNoiseLevel_Metric_<label>.xlsx`: one block of columns per scan (scan ID in "File Name:").
* `SNR_Scan_<id>-<series>_<label>.png`, `SI_Scan_…`, `MutualInformation_Scan_…`: one chart per scan.
* `IQA_subject_values.csv` (`scan, metric, volume, slice, volume2, slice2, value`) and `IQA_subject_meta.json` (per scan: series, modality, slices, volumes, volume axis).

## Repository layout
```
src/       the IQA code (shared modules identical to the scan-level tool) and the Rician MATLAB package
eucaim/    self-contained image (minimal MATLAB Runtime)
xnat/      XNAT image on the shared MATLAB Runtime base, command.json
```
Build: `bash build.sh eucaim` / `bash build.sh xnat` (Linux) or `.\build.ps1 eucaim` / `.\build.ps1 xnat` (Windows).

## Changelog
* **1.1.0**: 4D scans (volumes × slices, same rules as the scan level); every scan processed independently (one failing scan no longer stops a metric for all scans); scans found even when the DICOM folder also holds other files (e.g. XNAT catalog .xml) or files without the .dcm extension; MI between neighbouring slices, and each volume against the first for 4D; Rician skipped for CT and PET; CT/PET detection fixed; self-contained EUCAIM image.
* **1.0**: first release.
