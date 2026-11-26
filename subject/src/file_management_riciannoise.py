from natsort import natsorted 
import pydicom
import numpy as np
import os
from itertools import repeat
import pandas as pd

def get_path(path):
    # Get all the paths of the dicom files and list them 
    rootspath = []
    for root, dirnames, filenames in os.walk(path):
        has_dcm = 0
        for filename in filenames:
            _, ext = os.path.splitext(filename)
            if ext == '.dcm':
                has_dcm = 1
                break  # found one -- no need to check the rest of this folder's files
        if has_dcm == 1:
            rootspath.append(root)
    return rootspath

def getVolumes(PathDicom):
    lstFilesDCM = []
    for dirName, subdirList, fileList in os.walk(PathDicom):
        for filename in fileList:
            # check whether the file's DICOM
            if filename.lower().endswith('.dcm'):  
                # add the dicom file to the list
                lstFilesDCM.append(os.path.join(dirName, filename))

    return lstFilesDCM

def extractArrays(lstFilesDCM):
    # Initialize an empty list to store the 2D arrays (slices)
    slices = []
    
    # Loop through each file in lstFilesDCM and extract the pixel_array
    for file in lstFilesDCM:
        dicom_data = pydicom.dcmread(file)
        slices.append(dicom_data.pixel_array)
    
    # Stack the 2D slices into a 3D array (volume)
    volume = np.stack(slices, axis=0)
    
    return volume

def sortFiles(folder):
    # Sort the files in increasing order
    fileNames = getVolumes(folder)
    natsort_file_names = natsorted(fileNames)
    return natsort_file_names

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
        atrib_0018_1030 = ''.join(pydicom.dcmread(dcmFiles[0])[0x0018, 0x1030].value) 
        if 'cest' in atrib_0018_1030: 
            slice_name = "CEST MRI"
        elif 'diffusion' in atrib_0018_1030:
            slice_name = "DWI MRI"
        elif 'dce' in atrib_0018_1030:
            slice_name = "DCE MRI"
        else :
            slice_name = "MRI"
            
    elif [0x0008, 0x0060] in pydicom.dcmread(dcmFiles[0]):
        if 'CT' in pydicom.dcmread(dcmFiles[0])[0x0008, 0x0060].value.lower() :
           slice_name = "CT"
        elif 'PT' in pydicom.dcmread(dcmFiles[0])[0x0008, 0x0060].value.lower() :
            slice_name = "PET"
        else :
            slice_name = "MRI"
            
    if [0x0008, 0x103E] in first_dcm:
       type_name = first_dcm.SeriesDescription
            
    scan_type = slice_name 
    scan_name = type_name

    # Return a list with the desired information : 
    # for example, if it is meant to be offsets values, it should return something like that :
    # [-10, -10, -10, -9, -9, -9, -8, -8, -8, ...]
    # each value of this list belongs to a unique dicom file
    # Returns also the name of the x axis (offsets/b-value/time points) and the name of the slices
    return dcmValues, name_xvalue,  scan_type,  scan_name

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

def save_dfs(df_list, scan, sheets, scan_type, slice_name, spaces, output_folder="/output", session="SubjectLevel"):
    output_file = f"{output_folder}/RicianNoiseLevel_Metric_{session}.xlsx"
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet(sheets)
    col = 0  
    
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

    TableHead_format = workbook.add_format({
        'bold': True,
        'bg_color': '#488AC7',
        'font_color': '#FFFFFF',     # White text
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'font_size': 12
    })

    # Predefine the header labels for column 0 and 1 for width calculation
    header_labels_col0 = [
        "Modality:", 
        "Serie Description:", 
        "File Name:", 
        "Means", 
        "Medians", 
        "Stds"
    ]

# Excel layout configuration
    for dataframe, num_scan, type, name, in zip(df_list, scan, scan_type, slice_name):
        if dataframe is None or dataframe.empty:
            print(f"Skipping empty dataframe for {num_scan}")
            continue
             # Write slice type at the top of the sheet
        
        

        header_labels_col1 = [
            str(type),
            str(name),
            str(num_scan)
        ]

        for column in dataframe:
            df_width = max(dataframe[column].astype(str).map(len).max(), len(column))
            col_idx = dataframe.columns.get_loc(column) 

            if col_idx == 0:
                header_width = max(len(h) for h in header_labels_col0)
            else:
                header_width = max(len(h) for h in header_labels_col1)

            final_width = max(df_width, header_width)

            worksheet.set_column(col_idx + col, col_idx + col, final_width)
            
            
        worksheet.write(0, col, "Modality:", header_format)
        worksheet.write(0, col+1, type, header_format)

        # Write slice name at the top of the sheet
        worksheet.write(1, col, "Serie Description:", header_format)
        worksheet.write(1, col+1, name, header_format)

        worksheet.write(2, col , "File Name:", header_format) 
        worksheet.write(2, col+1 , str(num_scan), header_format)  

        # ================ WRITE DATAFRAME ================
        df_start_row = 4
        dataframe.to_excel(writer, sheet_name=sheets, startrow=df_start_row, startcol=col, index=False)

        # ========== APPLY HEADER FORMAT USING base_row ==========
        header_row = df_start_row   # THIS IS base_row FOR HEADERS

        for col_num, column_name in enumerate(dataframe.columns):
            worksheet.write(header_row, col + col_num, column_name, TableHead_format )

       

        # move to next block
        col = col + dataframe.shape[1] + spaces + 1

    writer.close()