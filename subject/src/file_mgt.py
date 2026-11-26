"""
Created on Nov 14, 2023

@authors: Aina Nasolo 


"""

import pydicom
import os
from natsort import natsorted 
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def get_path(path):
    rootspath = []
    for root, dirnames, filenames in os.walk(path):
        indd = []
        indxx= []
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext in ['.dcm']:
                indd = 1
            break
        inddx = indd
        if inddx == 1:
            rootspath.append(root)
    return rootspath

def get_files(path):
    filesspath = []
    for root, dirnames, filenames in os.walk(path):
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext in ['.dcm']:
                filesspath.append(filename)
            
    return filesspath

def getVolumes(PathDicom):
    # Get the whole volume in the input folder

    # Using 'os.path.join' ensures that the path is constructed 
    #  correctly regardless of the operating system being used.
    # Create empty Dicom list
    lstFilesDCM = []
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            # check whether the file's DICOM
            if filename.lower().endswith('.dcm'):  
                # add the dicom file to the list
                lstFilesDCM.append(os.path.join(dirName, filename))
    
    return lstFilesDCM

def sortFiles(PathDicom):
    # Sort the files in increasing order
    fileNames = getVolumes(PathDicom)
    natsort_file_names = natsorted(fileNames)
    return natsort_file_names

def extractArrays(lstFilesDCM):
    # Extract the arrays from each image in the list
    arrays = []
    for file in lstFilesDCM:
        arrays.append(pydicom.dcmread(file).pixel_array)
    return arrays

def MItodf(MI_timepoints, x):
    col = [str("%.2f" % x[i])+"/"+str("%.2f" % x[i+1]) for i in range(np.shape(MI_timepoints)[0])]
    idx = ["Mutual Information"]

    MI_timepoints = np.array(MI_timepoints)[np.newaxis, :]

    df = pd.DataFrame(MI_timepoints , columns=col, index=idx)

    return df

def save_dfs(df_list, scan, sheets, scan_type, slice_name, spaces, output_folder="/output", session="SubjectLevel"):
    output_file = f"{output_folder}/MutualInformation_Metric_{session}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheets)
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


    cellformat = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 12
    })

    col = 0
    for df, scan_name, s_type, s_name in zip(df_list, scan, scan_type, slice_name):
        # Write metadata
        worksheet.write(0, col, "Modality:", header_format)
        worksheet.write(0, col + 1, s_type, header_format)
        worksheet.write(1, col, "Serie Description:", header_format)
        worksheet.write(1, col + 1, s_name, header_format)
        worksheet.write(2, col, "File Name:", header_format)
        worksheet.write(2, col + 1, scan_name, header_format)

        row_offset = 4
       
        # Write Slice Pair / Mutual Information header
        worksheet.write(row_offset, col, "Slice Pair Number", Tableheader_format)
        worksheet.write(row_offset, col + 1, "Mutual Information", Tableheader_format)

        # Write MI values in two columns
        mi_row_offset = row_offset + 1
        for i, col_name in enumerate(df.columns):
            # If df has multiple rows, sum them or handle separately
            mi_values = df.iloc[:, i] if df.shape[0] > 1 else df.iloc[0, i]
            if isinstance(mi_values, (np.ndarray, pd.Series, list)):
                for j, val in enumerate(mi_values):
                    worksheet.write(mi_row_offset, col, col_name, cellformat)
                    worksheet.write(mi_row_offset, col +1, round(val, 3), cellformat)
                    mi_row_offset += 1
            else:
                worksheet.write(mi_row_offset, col, col_name, cellformat)
                worksheet.write(mi_row_offset, col + 1, round(mi_values, 3), cellformat)
                mi_row_offset += 1

        # Update col for next dataset
        col = col + spaces + 2

    writer.close()
            
    
def savefig(MI_timepoints, axis, scan_name, scan_type, name_xvalue, file_name, output_folder="/output", session="SubjectLevel"):
    if len(MI_timepoints) == 0 or len(axis) == 0:
        print(f"Warning: Empty data for {scan_name}. Skipping savefig.")
        return
    

    fig = plt.figure(figsize=(17, 10))
    fig.suptitle(f"Modality: {scan_type}", fontweight="bold", fontsize=30)

    # Decide the width of the bars
    if len(axis) > 1:
        x_diff = np.diff(axis)
        mean = np.mean(x_diff)
        bar_width = 0.4 * mean
    else:
        bar_width = 0.4  # fallback if only one bar
    metric_color = "#1f77b4"   
    
    plt.bar(axis, MI_timepoints, width=bar_width, color=metric_color, edgecolor="black", linewidth=1.2, alpha=0.9)

    plt.grid(True, linestyle="--", alpha=0.4)
    plt.xlabel(name_xvalue, fontsize=18)
    plt.ylabel("Mutual Information (MI)", fontsize=18)

    # # Set y-limits safely
    # y_min = np.min(MI_timepoints) - 0.05
    # y_max = np.max(MI_timepoints) + 0.05
    # plt.ylim(y_min, y_max)

    plt.ylim(bottom=max(0, np.min(MI_timepoints) - 0.05))

    plt.tick_params(axis='both', labelsize=14)

    os.makedirs(output_folder, exist_ok=True)
    suffix = f"_{session}" if session and session != "SubjectLevel" else ""
    filename = f"{output_folder}/MutualInformation_Scan_{file_name}{suffix}.png"
    plt.savefig(filename)
    plt.close(fig)

def getDcmInfos(dcmFiles):
    dcmValues = []
    name_xvalue = ''

    first_dcm = pydicom.dcmread(dcmFiles[0])

    # We check if (0x1061, 0x1002) exists among the tags
    if (0x1061, 0x1002) in first_dcm :
        # If so, we check if it's a CEST acquisition
        if 'cest' in first_dcm[0x1061, 0x1002].value:
            # The offset in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = []
            for file in dcmFiles:
                dcm = pydicom.dcmread(file)
                dcmValues.append(dcm[0x1061, 0x1015].value)
            name_xvalue = "Offsets"
        
        # Decides if it's a CEST or a DCE-CEST, DCE-CEST only have one offset value acquired a certain amounts of times
        axis = makeAxis(dcmValues)
        if np.size(axis) == 1:
            # Take the acquisition order of each slice
            dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
            name_xvalue = "Time points"

    # In the case where (1061, 1002) isn't on the dicom file, we can check if there is (0x1061, 0x1001)
    elif (0x1061, 0x1001) in first_dcm :
        # We check if there is 'cest' in the name of the acquisition, and we do the same thing as the above
        if 'cest' in first_dcm[0x1061, 0x1001].value:
            # The offset in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = [pydicom.dcmread(file)[0x1061, 0x1015].value for file in dcmFiles]
            name_xvalue = "Offsets"
        
        axis = makeAxis(dcmValues)
        if np.size(axis) == 1:
            dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
            name_xvalue = "Time points"

    elif (0x0018, 0x9087) in first_dcm :
        # if there is a mention of diffusion in the protocol name
        if 'diffusion' in first_dcm[0x0018, 0x1030].value:
            # The b-value in our dicom files are at (1061, 1015) so we take this value for each file in the dcmFiles
            dcmValues = [pydicom.dcmread(file)[0x0018, 0x9087].value for file in dcmFiles]
            name_xvalue = "b-values"

    else :
        dcmValues = [pydicom.dcmread(file)[0x0020, 0x0013].value for file in dcmFiles]
        name_xvalue = "Slice number"


    if [0x0018, 0x1030] in first_dcm:
      if 'cest' in first_dcm[0x0018, 0x1030].value:
       slice_name = "CEST MRI"
      elif 'diffusion' in first_dcm[0x0018, 0x1030].value :
       slice_name = "DWI MRI"
      elif 'dce' in first_dcm[0x0018, 0x1030].value:
       slice_name = "DCE MRI"
      else :
       slice_name = "MRI"
    else: 
     slice_name = "MRI"
     
    if [0x0008, 0x103E] in first_dcm:
            SeriesDescription = first_dcm.SeriesDescription
    # Return a list with the desired information : 
    # for example, if it is meant to be offsets values, it should return something like that :
    # [-10, -10, -10, -9, -9, -9, -8, -8, -8, ...]
    # each value of this list belongs to a unique dicom file
    # Returns also the name of the x axis (offsets/b-value/time points) and the name of the slices
    scan_name = SeriesDescription         
    scan_type = slice_name
    return dcmValues, name_xvalue,  scan_type, scan_name

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
    # Preprocess the dcmList to read all files once and store the necessary information
    read_files = [pydicom.dcmread(file) for file in dcmList]
    
    # Take the dicom list and split the list into volumes belonging to their offset/time/b-value
    
    # listVolume will contains all the volumes sorted from their offset/time/b-value
    listVolume = []
    for idx in x_values:
        # Volume contains one volume and is reset every loop
        Volume = []
        for i, read_file in enumerate(read_files):
            # if the file has the same offset as the current index of x_value, 
            # then we add the file in the volume
            if (0x1061, 0x1002) in read_file or (0x1061, 0x1001) in read_file :
                if x_name == "Offsets" and read_file[0x1061, 0x1015].value == idx :
                    Volume.append(dcmList[i])

                if x_name == "Time points" and read_file[0x0020, 0x0013].value == idx :   
                    Volume.append(dcmList[i])

            elif (0x0018, 0x9087) in read_file:
                if x_name == "b-values" and read_file[0x0018, 0x9087].value == idx : 
                    Volume.append(dcmList[i])
            
            elif x_name == "Slice number" and read_file[0x0020, 0x0013].value == idx :   
                    Volume.append(dcmList[i])

        # Once we have our volume, we add il to listDcm and loop again
        listVolume.append(Volume)

    # Return of listVolume such as the following format : 
    # [[volume1],[volume2],[volume3],...]
    return listVolume

# ---------------------------------------------------------------------------
# v1.1.0: MI bar chart with explicit pair labels (bars at even positions, so
# repeated CEST offsets no longer overlap)
# ---------------------------------------------------------------------------

def savefig_mi(values, labels, x_name, modality, series_desc, png_label, output_folder="/output",
               session="SubjectLevel"):
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
    suffix = f"_{session}" if session and session != "SubjectLevel" else ""
    plt.savefig(f"{output_folder}/MutualInformation_Scan_{png_label}{suffix}.png")
    plt.close(fig)
