# Image Quality Assessment (IQA), scan level

Computes image quality metrics for one DICOM series (scan), for 3D and 4D data:

| Tool | Metric | 3D | 4D (e.g. CEST, DCE, DWI) |
| --- | --- | --- | --- |
| `snr` | Signal-to-Noise Ratio (dB) | per slice | per volume × slice |
| `si` | Sharpness Index | per slice | per volume × slice |
| `mi` | Mutual Information | neighbouring slices | neighbouring slices in each volume, and each volume against the first |
| `riciannoiselevel` | Rician noise level (%), MRI only (skipped for CT and PET) | one value | one value per volume |

## Usage
EUCAIM:
```bash
jobman submit -i iqaxnat_scan -- <input_dir> <output_dir> snr si mi riciannoiselevel
```
Docker:
```bash
docker run --rm -v <in>:/data/in -v <out>:/data/out iqaxnat_scan:1.1.0 /data/in /data/out snr si mi riciannoiselevel
```
One or more tools can be given. The series is read once for all tools.

## Input data
* One DICOM series, one file per slice (any file names).
* **3D series**: the slices are ordered by their position.
* **4D series**: images at the same slice position are the volumes, ordered by acquisition. For Bruker CEST the saturation offset, and for DWI the b-value, is used as the volume's label.
* For 4D series, the signal mask for SNR is taken from the brightest volume, so low-signal volumes (e.g. CEST near water saturation) are not segmented on their own.
* Enhanced multi-frame DICOM is not supported.

## Outputs
* `SNR_Scan_<series>.xlsx/.png`, `SI_Scan_<series>.xlsx/.png`, `MutualInformation_Scan_<series>.xlsx/.png`, `RicianNoiseLevel_Scan_<series>.xlsx`: 3D = per slice; 4D = per volume (mean over slices), MI = each volume against the first, Rician = median over volumes.
* `IQA_values.csv`: every value (`metric, volume, slice, volume2, slice2, value`).
* `IQA_meta.json`: number of slices and volumes, volume axis and labels, metrics, tool version.

## Repository layout
```
src/       the IQA code and the compiled Rician MATLAB package, shared by both images
eucaim/    self-contained image (minimal MATLAB Runtime installed in the build)
xnat/      XNAT image on the shared MATLAB Runtime base, command.json
```
Build: `bash build.sh eucaim` / `bash build.sh xnat` (Linux) or `.\build.ps1 eucaim` / `.\build.ps1 xnat` (Windows).

## Changelog
* **1.1.0**: 4D support (volumes × slices); series read once for all tools; MI between neighbouring slices (as described) plus volume-to-first for 4D; Rician per volume, skipped with a message for CT and PET (Rician noise only applies to MRI); fixed: signal mask for CEST/DCE/DWI, CT/PET detection, crashes with missing header fields or InstanceNumber not starting at 1, DICOM files without the .dcm extension, very slow reading of 4D data; self-contained EUCAIM image.
* **1.0**: first release.
