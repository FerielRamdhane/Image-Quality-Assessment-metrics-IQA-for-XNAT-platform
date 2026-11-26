"""
Created on Nov 14, 2023

@authors: Aina Nasolo 


"""
import pydicom
import os
from natsort import natsorted 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

def getVolumes(PathDicom="/input"):
    # Get the whole volume in the input folder
    # Create empty Dicom list

    lstFilesDCM = []
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            # check whether the file's DICOM
            if filename.lower().endswith('.dcm'):  
                # add the dicom file to the list
                lstFilesDCM.append(os.path.join(dirName, filename))
    
    return lstFilesDCM

def sortFiles():
    # Sort the files in increasing order
    fileNames = getVolumes()
    natsort_file_names = natsorted(fileNames)
    return natsort_file_names

def extractArrays(lstFilesDCM):
    # Extract the arrays from each image in the list
    arrays = []
    for file in lstFilesDCM:
        arrays.append(pydicom.dcmread(file).pixel_array)
    return arrays

def toExcel(MI_timepoints, x, slice_name, scan_name, sheet_name, xname, output_folder="/output"):

    col = [str("%.2f" % x[i])+"/"+str("%.2f" % x[i+1]) for i in range(np.shape(MI_timepoints)[0])]
    idx = ["Mutual Information"]

    MI_timepoints = np.array(MI_timepoints)[np.newaxis, :]

    # df = pd.DataFrame(MI_timepoints , columns=col, index=idx)

    # Save to Excel with column width adjustment
    output_file = f"{output_folder}/MutualInformation_Scan_{scan_name}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    # df_SNR.to_excel(writer, index=False)
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheet_name)

    # Excel formatting options
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#488AC7',
        'font_color': '#FFFFFF',     # White text
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
        'font_size': 12
    })

    Tableheader_format = workbook.add_format({
        'bold': True,
        'bg_color': '#488AC7',
        'font_color': '#FFFFFF',     # White text
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 12
    })

    cell_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 12
    })
    column_width = len('Serie Description') + 4  # +2 for some padding
    worksheet.set_column(0, 2, column_width) 

    # Write slice name at the top of the sheet
    worksheet.write(0, 0, "Modality:", header_format)
    worksheet.write(0, 1, slice_name, header_format)

    # Write slice name at the top of the sheet
    worksheet.write(1, 0, "Serie Description:", header_format)
    worksheet.write(1, 1, scan_name, header_format)

    # Write Slices along information
    worksheet.write(3, 0, 'Slice Pair Number ', Tableheader_format)

    # Write Mutual Information header (Row 4)
    worksheet.write(3, 1, "Mutual Information", Tableheader_format)

    for i, value in enumerate(col):
        worksheet.write(i+4, 0, value, cell_format)

    # Write the Mutual Information values starting from row 5
    for i, val in enumerate(MI_timepoints[0]):
        worksheet.write(i+4, 1, round(val,3) , cell_format)

    # Close the writer and save the file
    writer.close()


def savefig(MI_timepoints, axis, slice_name, name_xvalue, scan_name, output_folder="/output"):
   
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.suptitle(f"Modality: {slice_name} - Serie: {scan_name}", fontweight="bold", fontsize=25)

    # --- Build pair labels like JS: "1.00/2.00", "2.00/3.00", ... ---
    pair_labels = [f"{axis[i]:.2f}/{axis[i+1]:.2f}" for i in range(len(axis) - 1)]
    x_positions = np.arange(len(pair_labels))

    # Bar width
    bar_width = 0.2

    metric_color = "#7F77DD"

    bars = ax.bar(
        x_positions, MI_timepoints[:len(pair_labels)],
        width=bar_width,
        color=metric_color,
        edgecolor="none",
        alpha=1.0,
        zorder=3,
    )

    # Simulate rounded tops
    y_range = max(MI_timepoints) - max(0, np.min(MI_timepoints) - 0.05)
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
        # ax.add_patch(ellipse)

    # --- Grid ---
    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='--', alpha=1, color='#e0e0e0')
    ax.grid(False, axis='x')

    # --- Spines ---
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#dde4ec')

    # --- X ticks with pair labels ---
    ax.set_xticks(x_positions)
    n = len(pair_labels)
    if n > 20:
        # Show every 5th label like JS
        visible_labels = [label if i % 5 == 0 else '' for i, label in enumerate(pair_labels)]
        ax.set_xticklabels(visible_labels, rotation=-35, ha='left', fontsize=12)
    elif n > 10:
        ax.set_xticklabels(pair_labels, rotation=-35, ha='left', fontsize=12)
    else:
        ax.set_xticklabels(pair_labels, rotation=0, ha='center', fontsize=12)

    # --- Axis labels ---
    ax.set_xlabel(name_xvalue, fontsize=16, labelpad=12)
    ax.set_ylabel("MI", fontsize=16, labelpad=12)
    ax.tick_params(axis='y', labelsize=14)

    # --- Y limits ---
    ax.set_ylim(bottom=max(0, np.min(MI_timepoints) - 0.05))
    fig.subplots_adjust(top=0.88, bottom=0.18, left=0.07, right=0.97)
    filename = f"{output_folder}/MutualInformation_Scan_{scan_name}.png"
    plt.savefig(filename)
    plt.close(fig)

def getDcmInfos(dcmFiles):
    dcmValues = []
    name_xvalue = ''
    first_dcm = pydicom.dcmread(dcmFiles[0])

    # We check if (0x1061, 0x1002) exists among the tags
    if (0x1061, 0x1002) in pydicom.dcmread(dcmFiles[0]) :
        # If so, we check if it's a CEST acquisition
        if 'cest' in pydicom.dcmread(dcmFiles[0])[0x1061, 0x1002].value.lower():
            # The offset in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = [pydicom.dcmread(file)[0x1061, 0x1015].value for file in dcmFiles]
            name_xvalue = "Offsets"
        
        # Decides if it's a CEST or a DCE-CEST, DCE-CEST only have one offset value acquired a certain amounts of times
        axis = makeAxis(dcmValues)
        if np.size(axis) == 1:
            # Take the acquisition order of each slice
            dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
            name_xvalue = "Time points"

    # In the case where (1061, 1002) isn't on the dicom file, we can check if there is (0x1061, 0x1001)
    elif (0x1061, 0x1001) in pydicom.dcmread(dcmFiles[0]) :
        # We check if there is 'cest' in the name of the acquisition, and we do the same thing as the above
        if 'cest' in pydicom.dcmread(dcmFiles[0])[0x1061, 0x1001].value.lower():
            # The offset in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = [pydicom.dcmread(file)[0x1061, 0x1015].value for file in dcmFiles]
            name_xvalue = "Offsets"
        
        axis = makeAxis(dcmValues)
        if np.size(axis) == 1:
            dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
            name_xvalue = "Time points"

    elif (0x0018, 0x9087) in pydicom.dcmread(dcmFiles[0]) :
        # if there is a mention of diffusion in the protocol name
        if 'diffusion' in pydicom.dcmread(dcmFiles[0])[0x0018, 0x1030].value.lower():
            # The b-value in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = [pydicom.dcmread(file)[0x0018, 0x9087].value for file in dcmFiles]
            name_xvalue = "b-values"

    else :
        dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
        name_xvalue = "Slice number"


    if [0x0018, 0x1030] in pydicom.dcmread(dcmFiles[0]):
        if 'cest' in pydicom.dcmread(dcmFiles[0])[0x0018, 0x1030].value :
            slice_name = "CEST MRI"
        elif 'diffusion' in pydicom.dcmread(dcmFiles[0])[0x0018, 0x1030].value:
            slice_name = "DWI MRI"
        elif 'dce' in pydicom.dcmread(dcmFiles[0])[0x0018, 0x1030].value:
            slice_name = "DCE MRI"
        else :
            slice_name = "MRI"
    else: 
        slice_name = "MRI"
    
    if [0x0008, 0x103E] in first_dcm:
       type_name = first_dcm.SeriesDescription

    # Return a list with the desired information : 
    # for example, if it is meant to be offsets values, it should return something like that :
    # [-10, -10, -10, -9, -9, -9, -8, -8, -8, ...]
    # each value of this list belongs to a unique dicom file
    # Returns also the name of the x axis (offsets/b-value/time points) and the name of the slices
    return dcmValues, name_xvalue, slice_name, type_name

def makeAxis(dcmValues):
    # Makes the x axis by taking each values of offset/time,... once
    # then sort the values
    x_values = np.unique(dcmValues)
    x_values = natsorted(x_values)

    # It should return a list with a unique value for each possible values in the 
    # dcmValues, for example if it is meant to be offsets values like that : 
    # [-10, -10, -10, -9, -9, -9, -8, -8, -8, ...]
    # it should return a list such as :
    # [-10, -9, -8, ...]
    # which will be our x values on our plot
    return x_values

def splitVolumes(dcmList, x_values, x_name):
    # Take the dicom list and split the list into volumes belonging to their offset/time/b-value
    
    # listVolume will contains all the volumes sorted from their offset/time/b-value
    listVolume = []
    for idx in x_values:
        # Volume contains one volume and is reset every loop
        Volume = []
        for file in dcmList:
            # if the file has the same offset as the current index of x_value, 
            # then we add the file in the volume
            if (0x1061, 0x1002) in pydicom.dcmread(file) or (0x1061, 0x1001) in pydicom.dcmread(file) :
                if x_name == "Offsets" and pydicom.dcmread(file)[0x1061, 0x1015].value == idx :
                    Volume.append(file)

                if x_name == "Time points" and pydicom.dcmread(file)[0x0020, 0x0013].value == idx :   
                    Volume.append(file)

            elif (0x0018, 0x9087) in pydicom.dcmread(file):
                if x_name == "b-values" and pydicom.dcmread(file)[0x0018, 0x9087].value == idx : 
                    Volume.append(file)
            
            elif x_name == "Slice number" and pydicom.dcmread(file)[0x0020, 0x0013].value == idx :   
                    Volume.append(file)

        # Once we have our volume, we add il to listDcm and loop again
        listVolume.append(Volume)

    # Return of listVolume such as the following format : 
    # [[volume1],[volume2],[volume3],...]
    return listVolume


# ---------------------------------------------------------------------------
# v1.1.0: writers with explicit pair labels (same Excel layout as toExcel, which
# the dashboard reads: row 0/1 modality + series, row 3 header, row 4+ label | MI)
# ---------------------------------------------------------------------------

def mi_to_excel(values, labels, modality, series_desc, file_tag, output_folder="/output",
                first_header="Slice Pair Number "):
    output_file = f"{output_folder}/MutualInformation_Scan_{file_tag}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet('Mutual Information')
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 12})
    table_header_format = workbook.add_format({
        'bold': True, 'bg_color': '#488AC7', 'font_color': '#FFFFFF',
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    cell_format = workbook.add_format({
        'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    worksheet.set_column(0, 2, len('Serie Description') + 4)

    worksheet.write(0, 0, "Modality:", header_format)
    worksheet.write(0, 1, modality, header_format)
    worksheet.write(1, 0, "Serie Description:", header_format)
    worksheet.write(1, 1, series_desc, header_format)
    worksheet.write(3, 0, first_header, table_header_format)
    worksheet.write(3, 1, "Mutual Information", table_header_format)
    for i, (label, val) in enumerate(zip(labels, values)):
        worksheet.write(i + 4, 0, label, cell_format)
        worksheet.write(i + 4, 1, round(float(val), 3), cell_format)
    writer.close()


def savefig_mi(values, labels, x_name, modality, series_desc, file_tag, output_folder="/output"):
    fig, ax = plt.subplots(figsize=(15, 8))
    fig.suptitle(f"Modality: {modality} - Serie: {series_desc}", fontweight="bold", fontsize=25)
    x_positions = np.arange(len(labels))
    ax.bar(x_positions, values, width=0.2, color="#7F77DD", edgecolor="none", zorder=3)

    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='--', alpha=1, color='#e0e0e0')
    ax.grid(False, axis='x')
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#dde4ec')

    ax.set_xticks(x_positions)
    n = len(labels)
    if n > 20:
        ax.set_xticklabels([l if i % 5 == 0 else '' for i, l in enumerate(labels)],
                           rotation=-35, ha='left', fontsize=12)
    elif n > 10:
        ax.set_xticklabels(labels, rotation=-35, ha='left', fontsize=12)
    else:
        ax.set_xticklabels(labels, rotation=0, ha='center', fontsize=12)

    ax.set_xlabel(x_name, fontsize=16, labelpad=12)
    ax.set_ylabel("MI", fontsize=16, labelpad=12)
    ax.tick_params(axis='y', labelsize=14)
    if len(values):
        ax.set_ylim(bottom=max(0, float(np.min(values)) - 0.05))
    fig.subplots_adjust(top=0.88, bottom=0.18, left=0.07, right=0.97)
    plt.savefig(f"{output_folder}/MutualInformation_Scan_{file_tag}.png")
    plt.close(fig)
