"""
Created on Dec 18, 2024

@authors: Aina Nasolo, modified by Feriel Ramdhane

"""
import pydicom
import os
from natsort import natsorted 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd


def get_path(path):
    rootspath = []
    for root, dirnames, filenames in os.walk(path):
        indd = []
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext in ['.dcm']:
                indd = 1
            break
        if indd == 1:
            rootspath.append(root)
    return rootspath

def getVolumes(PathDicom):
    lstFilesDCM = []
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            if filename.lower().endswith('.dcm'):  
                lstFilesDCM.append(os.path.join(dirName, filename))
    return lstFilesDCM

def sortFiles(folder):
    fileNames = getVolumes(folder)
    return natsorted(fileNames)

def extractArrays(lstFilesDCM):
    arrays = []
    for file in lstFilesDCM:
        arrays.append(pydicom.dcmread(file).pixel_array)
    return arrays


# ---------------------------------------------------------------------------
# Dataframe builders — SNR and SI built separately
# ---------------------------------------------------------------------------

def SNRtodf(listSNR, Axis, x_name):
    """Build a dataframe containing only SNR values."""
    arr = np.transpose([Axis, listSNR])
    return pd.DataFrame(arr, columns=[x_name, 'SNR value(dB)'])


def SItodf(listSI, Axis, x_name):
    """Build a dataframe containing only Sharpness Index values."""
    arr = np.transpose([Axis, listSI])
    return pd.DataFrame(arr, columns=[x_name, 'Sharpness Index'])


# ---------------------------------------------------------------------------
# Shared Excel writer
# ---------------------------------------------------------------------------

def _write_metric_excel(df_list, scan, sheets, scan_type, slice_name, spaces,
                         output_file, value_column, header_labels_col0):
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Sheet1')
    col = 0

    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 12
    })
    TableHead_format = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12
    })

    for dataframe, num_scan, type_, name in zip(df_list, scan, scan_type, slice_name):
        if dataframe is None or dataframe.empty:
            print(f"Skipping empty dataframe for {num_scan}")
            continue

        header_labels_col1 = [str(type_), str(name), str(num_scan)]
        means = []
        medians = []
        stds = []

        for column in dataframe:
            df_width = max(dataframe[column].astype(str).map(len).max(), len(column))
            col_idx = dataframe.columns.get_loc(column)
            if col_idx == 0:
                header_width = max(len(h) for h in header_labels_col0)
            else:
                header_width = max(len(h) for h in header_labels_col1)
            final_width = max(df_width, header_width)
            worksheet.set_column(col_idx + col, col_idx + col, final_width)
            means.append(pd.to_numeric(dataframe[column], errors='coerce').mean())
            medians.append(pd.to_numeric(dataframe[column], errors='coerce').median())
            stds.append(pd.to_numeric(dataframe[column], errors='coerce').std())

        worksheet.write(0, col, "Modality:", header_format)
        worksheet.write(0, col + 1, type_, header_format)
        worksheet.write(1, col, "Serie Description:", header_format)
        worksheet.write(1, col + 1, name, header_format)
        worksheet.write(2, col, "File Name:", header_format)
        worksheet.write(2, col + 1, str(num_scan), header_format)

        df_start_row = 4
        dataframe.to_excel(writer, sheet_name='Sheet1', startrow=df_start_row, startcol=col, index=False)
        for col_num, column_name in enumerate(dataframe.columns):
            worksheet.write(df_start_row, col + col_num, column_name, TableHead_format)

        base_row = df_start_row + len(dataframe.index) + 1
        worksheet.write(base_row,     col, 'Means',   header_format)
        worksheet.write(base_row,     col + 1, means[1])
        worksheet.write(base_row + 1, col, 'Medians', header_format)
        worksheet.write(base_row + 1, col + 1, medians[1])
        worksheet.write(base_row + 2, col, 'Stds',    header_format)
        worksheet.write(base_row + 2, col + 1, stds[1])

        col = col + dataframe.shape[1] + spaces + 1

    writer.close()


# ---------------------------------------------------------------------------
# Excel writers — separate SNR and SI, with session label in filename
# ---------------------------------------------------------------------------

def save_snr_dfs(df_list, scan, scan_type, slice_name, spaces,
                 output_folder="/output", session="SubjectLevel"):
    """Write the subject-level SNR summary Excel file."""
    header_labels_col0 = ["Modality:", "Serie Description:", "File Name:",
                           "Slice number", "Means", "Medians", "Stds"]
    output_file = f"{output_folder}/SNR_Metric_{session}.xlsx"
    _write_metric_excel(df_list, scan, None, scan_type, slice_name, spaces,
                         output_file, 'SNR value(dB)', header_labels_col0)


def save_si_dfs(df_list, scan, scan_type, slice_name, spaces,
                output_folder="/output", session="SubjectLevel"):
    """Write the subject-level SI summary Excel file."""
    header_labels_col0 = ["Modality:", "Serie Description:", "File Name:",
                           "Slice number", "Means", "Medians", "Stds"]
    output_file = f"{output_folder}/SI_Metric_{session}.xlsx"
    _write_metric_excel(df_list, scan, None, scan_type, slice_name, spaces,
                         output_file, 'Sharpness Index', header_labels_col0)


def save_dfs(df_list, scan, sheets, scan_type, slice_name, spaces,
             output_folder="/output", session="SubjectLevel"):
    """Backward-compatible wrapper: split combined SNR/SI into two files."""
    snr_dfs = []
    si_dfs  = []
    for df in df_list:
        if df is None or df.empty:
            snr_dfs.append(df)
            si_dfs.append(df)
            continue
        x_name = df.columns[0]
        snr_dfs.append(df[[x_name, 'SNR value(dB)']].copy())
        si_dfs.append(df[[x_name, 'Sharpness Index']].copy())
    save_snr_dfs(snr_dfs, scan, scan_type, slice_name, spaces, output_folder, session)
    save_si_dfs(si_dfs,  scan, scan_type, slice_name, spaces, output_folder, session)


# ---------------------------------------------------------------------------
# Shared bar-plot builder (dashboard style)
# ---------------------------------------------------------------------------

def _bar_plot(values, axis, x_name, y_label, metric_color, output_path,
              title, ylim_padding_ratio=None, mean_line=True):
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.suptitle(title, fontweight="bold", fontsize=25)

    x_positions = np.arange(len(axis))
    bar_width = 0.4

    bars = ax.bar(x_positions, values, width=bar_width,
                  color=metric_color, edgecolor="none", alpha=1.0, zorder=3)

    vmax, vmin = max(values), min(values)
    y_range = vmax - max(0, vmin - 1)
    if y_range <= 0:
        y_range = max(vmax, 1)
    for bar in bars:
        x = bar.get_x() + bar.get_width() / 2
        y = bar.get_height()
        ellipse = mpatches.Ellipse((x, y), width=bar.get_width(),
                                    height=0.012 * y_range,
                                    color=metric_color, zorder=4)
        ax.add_patch(ellipse)

    if mean_line:
        mean_val = np.mean(values)
        ax.axhline(y=mean_val, color='#E24B4A', linestyle='--', linewidth=1.5)
        ax.text(len(axis) - 0.5, mean_val, f'mean {mean_val:.1f}',
                color='#E24B4A', fontsize=11, va='bottom', ha='right')

    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.grid(False, axis='x')
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#dde4ec')

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels([str(a) for a in axis], fontsize=11)
    ax.set_xlabel(x_name, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.tick_params(axis='y', labelsize=11)

    if ylim_padding_ratio is not None:
        ax.set_ylim(bottom=0, top=vmax * (1 + ylim_padding_ratio))
    else:
        ax.set_ylim(bottom=max(0, vmin - 1), top=vmax + 1)

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.97)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Plotting — separate SNR and SI plots per scan, with session suffix
# ---------------------------------------------------------------------------

def savefig_snr(SNR, x_name, scan_type, scan_name, axis,
                output_folder="/output", session="SubjectLevel"):
    """Save SNR bar chart: SNR_Scan_{scan_name}_{session}.png"""
    metric_color = "#488AC7"
    title = f"Modality: {scan_type}"
    suffix = f"_{session}" if session and session != "SubjectLevel" else ""
    filename = f"{output_folder}/SNR_Scan_{scan_name}{suffix}.png"
    _bar_plot(SNR, axis, x_name, "SNR (dB)", metric_color, filename, title,
              ylim_padding_ratio=None, mean_line=True)


def savefig_si(SI, x_name, scan_type, scan_name, axis,
               output_folder="/output", session="SubjectLevel"):
    """Save SI bar chart: SI_Scan_{scan_name}_{session}.png"""
    metric_color = "#61BDF2"
    title = f"Modality: {scan_type}"
    suffix = f"_{session}" if session and session != "SubjectLevel" else ""
    filename = f"{output_folder}/SI_Scan_{scan_name}{suffix}.png"
    _bar_plot(SI, axis, x_name, "Sharpness Index", metric_color, filename, title,
              ylim_padding_ratio=0.1, mean_line=True)


def savefig(sharp_idx, x_name, scan_name, SNR, axis, scan_type, file_name,
            output_folder="/output", session="SubjectLevel"):
    """Backward-compatible: produce both SNR and SI plots."""
    savefig_snr(SNR,      x_name, scan_type, file_name, axis, output_folder, session)
    savefig_si(sharp_idx, x_name, scan_type, file_name, axis, output_folder, session)