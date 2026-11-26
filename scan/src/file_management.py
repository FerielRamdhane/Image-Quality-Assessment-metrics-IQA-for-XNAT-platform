"""
Created on Dec 18, 2024

@authors: Feriel Ramdhane 

Changelog:
  2026-05-12 - Separated SNR and SI into independent tools.
  2026-11-25 - v1.1.0: file names made safe (series descriptions with / or spaces).
"""

import pydicom
import os
from natsort import natsorted
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from iqa_common import safe_name


# ---------------------------------------------------------------------------
# DICOM helpers
# ---------------------------------------------------------------------------

def getVolumes(PathDicom="/input"):
    """Walk PathDicom and return a list of all .dcm file paths."""
    lstFilesDCM = []
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            if filename.lower().endswith('.dcm'):
                lstFilesDCM.append(os.path.join(dirName, filename))
    return lstFilesDCM


def sortFiles(PathDicom="/input"):
    """Return naturally-sorted list of .dcm file paths."""
    return natsorted(getVolumes(PathDicom))


def extractArrays(lstFilesDCM):
    """Return list of pixel arrays for each DICOM file."""
    arrays = []
    for file in lstFilesDCM:
        arrays.append(pydicom.dcmread(file).pixel_array)
    return arrays


# ---------------------------------------------------------------------------
# Shared Excel format helper
# ---------------------------------------------------------------------------

def _make_workbook_formats(workbook):
    """Return (header_fmt, table_header_fmt, cell_fmt) for a workbook."""
    header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 12,
    })
    table_header_fmt = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12,
    })
    cell_fmt = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12,
    })
    return header_fmt, table_header_fmt, cell_fmt


# ---------------------------------------------------------------------------
# SNR only  (snr tool)
# ---------------------------------------------------------------------------

def SNRonlyToExcel(listSNR, Axis, scan_type, slice_name, sheet_name,
                   output_folder="/output"):
    """Write SNR-only table to SNR_Metric_ScanLevel.xlsx"""
    list_data = np.transpose([Axis, listSNR])
    df = pd.DataFrame(list_data, columns=['Slice Number', 'SNR value (dB)'])

    stats = pd.DataFrame({
        'Mean':   df[['SNR value (dB)']].mean(),
        'Median': df[['SNR value (dB)']].median(),
        'Std':    df[['SNR value (dB)']].std(),
    })

    output_file = f"{output_folder}/SNR_Scan_{safe_name(slice_name)}.xlsx"
    writer    = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    header_fmt, table_header_fmt, cell_fmt = _make_workbook_formats(workbook)

    worksheet.write(0, 0, "Modality:",          header_fmt)
    worksheet.write(0, 1, scan_type,            header_fmt)
    worksheet.write(1, 0, "Serie Description:", header_fmt)
    worksheet.write(1, 1, slice_name,           header_fmt)

    for col_num, col_name in enumerate(df.columns):
        worksheet.write(4, col_num, col_name, table_header_fmt)

    for row_num, row in df.iterrows():
        rounded = [round(x, 3) if isinstance(x, (int, float)) else x for x in row]
        for col_num, value in enumerate(rounded):
            worksheet.write(row_num + 5, col_num, value, cell_fmt)

    worksheet.set_column(1, 1, 12, workbook.add_format({'num_format': '0.0'}))

    row_stat = len(df) + 6
    worksheet.write(row_stat,     0, "Mean",   header_fmt)
    worksheet.write(row_stat,     1, round(float(stats['Mean']['SNR value (dB)']), 3), cell_fmt)
    worksheet.write(row_stat + 1, 0, "Median", header_fmt)
    worksheet.write(row_stat + 1, 1, round(float(stats['Median']['SNR value (dB)']), 3), cell_fmt)
    worksheet.write(row_stat + 2, 0, "Std",    header_fmt)
    worksheet.write(row_stat + 2, 1, round(float(stats['Std']['SNR value (dB)']), 3), cell_fmt)

    col_width = len('Serie Description:') + 4
    worksheet.set_column(0, 1, col_width)
    writer.close()


def savefig_snr(SNR, x_name, slice_name, axis, scan_name, output_folder="/output"):
    """Save SNR bar chart matching the dashboard style"""
    import matplotlib.patches as mpatches
    
    metric_color = "#488AC7"  # Same blue as dashboard
    
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.suptitle(f"Modality: {slice_name} - Series: {scan_name}", fontweight="bold", fontsize=20)

    x_positions = range(len(axis))
    bar_width = 0.2

    bars = ax.bar(
        x_positions, SNR,
        width=bar_width,
        color=metric_color,
        edgecolor="none",
        alpha=1.0,
        zorder=3,
    )

    # Rounded tops
    y_range = max(SNR) - (min(SNR) - 1)
    for bar in bars:
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        ellipse = mpatches.Ellipse(
            (x, y),
            width=bar.get_width(),
            height=0.012 * y_range,
            color=metric_color,
            zorder=4,
        )
       

    # # Mean reference line
    # mean_val = np.mean(SNR)
    # ax.axhline(y=mean_val, color='#E24B4A', linestyle='--', linewidth=1.5,
    #            label=f'mean {mean_val:.1f}')
    # ax.text(len(axis) - 0.5, mean_val, f'mean {mean_val:.1f}',
    #         color='#E24B4A', fontsize=11, va='bottom', ha='right')

    # Grid
    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7, color='#e0e0e0')
    ax.grid(False, axis='x')

    # # Spines
    # for spine in ['top', 'right']:
    #     ax.spines[spine].set_visible(False)
    # for spine in ['left', 'bottom']:
    #     ax.spines[spine].set_color('#dde4ec')

    # X ticks
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels([str(a) for a in axis], fontsize=12)

    # Axis labels
    ax.set_xlabel(x_name, fontsize=16, labelpad=12)
    ax.set_ylabel("SNR (dB)", fontsize=16, labelpad=12)
    ax.tick_params(axis='y', labelsize=14)

    # Y limits
    ax.set_ylim(bottom=max(0, min(SNR) - 1), top=max(SNR) + 1)

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.07, right=0.97)
    filename = f"{output_folder}/SNR_Scan_{safe_name(scan_name)}.png"
    plt.savefig(filename, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# SI only  (si tool)
# ---------------------------------------------------------------------------

def SItoExcel(Sh_idx, Axis, scan_type, slice_name, sheet_name,
              output_folder="/output"):
    """Write Sharpness Index-only table to SI_Metric_ScanLevel.xlsx"""
    list_data = np.transpose([Axis, Sh_idx])
    df = pd.DataFrame(list_data, columns=['Slice Number', 'Sharpness Index value'])

    stats = pd.DataFrame({
        'Mean':   df[['Sharpness Index value']].mean(),
        'Median': df[['Sharpness Index value']].median(),
        'Std':    df[['Sharpness Index value']].std(),
    })

    output_file = f"{output_folder}/SI_Scan_{safe_name(slice_name)}.xlsx"
    writer    = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet(sheet_name)
    header_fmt, table_header_fmt, cell_fmt = _make_workbook_formats(workbook)

    worksheet.write(0, 0, "Modality:",          header_fmt)
    worksheet.write(0, 1, scan_type,            header_fmt)
    worksheet.write(1, 0, "Serie Description:", header_fmt)
    worksheet.write(1, 1, slice_name,           header_fmt)

    for col_num, col_name in enumerate(df.columns):
        worksheet.write(4, col_num, col_name, table_header_fmt)

    for row_num, row in df.iterrows():
        rounded = [round(x, 3) if isinstance(x, (int, float)) else x for x in row]
        for col_num, value in enumerate(rounded):
            worksheet.write(row_num + 5, col_num, value, cell_fmt)

    row_stat = len(df) + 6
    worksheet.write(row_stat,     0, "Mean",   header_fmt)
    worksheet.write(row_stat,     1, round(float(stats['Mean']['Sharpness Index value']), 3), cell_fmt)
    worksheet.write(row_stat + 1, 0, "Median", header_fmt)
    worksheet.write(row_stat + 1, 1, round(float(stats['Median']['Sharpness Index value']), 3), cell_fmt)
    worksheet.write(row_stat + 2, 0, "Std",    header_fmt)
    worksheet.write(row_stat + 2, 1, round(float(stats['Std']['Sharpness Index value']), 3), cell_fmt)

    col_width = len('Sharpness Index value') + 4
    worksheet.set_column(0, 1, col_width)
    writer.close()


def savefig_si(SI, x_name, slice_name, axis, scan_name, output_folder="/output"):
    """Save SI bar chart matching the dashboard style"""
    import matplotlib.patches as mpatches

    metric_color = "#61BDF2"  # Same blue as SI panel in dashboard

    fig, ax = plt.subplots(figsize=(15, 8))
    fig.suptitle(f"Modality: {slice_name} - Series: {scan_name} ", fontweight="bold", fontsize=20)

    x_positions = range(len(axis))
    bar_width = 0.4

    bars = ax.bar(
        x_positions, SI,
        width=bar_width,
        color=metric_color,
        edgecolor="none",
        alpha=1.0,
        zorder=3,
    )

    # Rounded tops
    y_range = max(SI) - max(0, min(SI) - 1)
    for bar in bars:
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        ellipse = mpatches.Ellipse(
            (x, y),
            width=bar.get_width(),
            height=0.012 * y_range,
            color=metric_color,
            zorder=4,
        )
       

    # # Mean reference line
    # mean_val = np.mean(SI)
    # ax.axhline(y=mean_val, color='#E24B4A', linestyle='--', linewidth=1.5)
    # ax.text(len(axis) - 0.5, mean_val, f'mean {mean_val:.1f}',
    #         color='#E24B4A', fontsize=11, va='bottom', ha='right')

    # Grid
    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7, color='#e0e0e0')
    ax.grid(True, axis='x', linestyle='--', alpha=0.7, color='#e0e0e0')

    # # Spines
    # for spine in ['top', 'right']:
    #     ax.spines[spine].set_visible(False)
    # for spine in ['left', 'bottom']:
    #     ax.spines[spine].set_color('#dde4ec')

    # X ticks
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels([str(a) for a in axis], fontsize=12)

    # Axis labels
    ax.set_xlabel(x_name, fontsize=16, labelpad=12)
    ax.set_ylabel("Sharpness Index", fontsize=16, labelpad=12)
    ax.tick_params(axis='y', labelsize=14)

    # Y limits
    ax.set_ylim(bottom=0, top=max(SI) * 1.1)

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.97)
    filename = f"{output_folder}/SI_Scan_{safe_name(scan_name)}.png"
    plt.savefig(filename, dpi=150)
    plt.close(fig)
