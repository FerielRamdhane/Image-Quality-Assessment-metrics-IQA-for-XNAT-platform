# Image Quality Assessment (IQA) metrics for XNAT and EUCAIM

Image quality metrics for MRI (and CT / PET), for 3D and 4D series, at two levels:

| Folder | Tool | Runs on | XNAT image | EUCAIM image |
| --- | --- | --- | --- | --- |
| [`scan/`](scan) | IQA scan level | one scan (one DICOM series) | `iqaxnat_scan:1.1.0-xnat` | `iqaxnat_scan:1.1.0` |
| [`subject/`](subject) | IQA subject level | every scan of a session, one summary per metric | `iqaxnat_subject:1.1.0-xnat` | `iqaxnat_subject:1.1.0` |

Metrics (one or more per run): `snr` (Signal-to-Noise Ratio), `si` (Sharpness Index), `mi` (Mutual Information), `riciannoiselevel` (Rician noise level, MRI only). `snrsi` runs `snr` and `si`, as in v1.0.

## Usage
```bash
# scan level
docker run --rm -v <scan folder>:/input -v <out>:/output iqaxnat_scan:1.1.0 snr si mi riciannoiselevel
# subject level
docker run --rm -v <session folder>:/input -v <out>:/output iqaxnat_subject:1.1.0 snr si mi riciannoiselevel --session <label>
```
The input and output folders can also be given as the first two arguments (EUCAIM `jobman`), e.g. `iqaxnat_scan:1.1.0 /data/in /data/out snr si`.

**3D series** give one value per slice; **4D series** (CEST, DCE, DWI, …) give one value per volume, and every value per volume × slice is saved in a CSV. See the README in each folder for details, outputs and the changelog.

## Building
Each folder builds its own two images, from that folder (EUCAIM: `iqaxnat_<level>:<version>`, XNAT: `iqaxnat_<level>:<version>-xnat`):
```bash
cd scan    && bash build.sh eucaim && bash build.sh xnat
cd subject && bash build.sh eucaim && bash build.sh xnat
```
(Windows: `.\build.ps1 eucaim` / `.\build.ps1 xnat`.) The EUCAIM images are self-contained; the XNAT images use the shared MATLAB Runtime base image of the XNAT server (`mcr-riciannoiselevel:r2024b`).

## Changelog
* **1.1.0**: 4D support, many bug fixes, scan and subject level rebuilt on shared code, self-contained EUCAIM images (see each folder's README).
* **1.0**: first release.

## Citation
Cite the code: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24566712.svg)](https://doi.org/10.5281/zenodo.24566712)

## Contact
preclinicaldata@eurobioimaging.eu
