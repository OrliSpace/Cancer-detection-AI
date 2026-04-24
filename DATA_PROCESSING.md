# **1. Raw Data Overview and Folder Structure**

The raw imaging data is stored under the **DICOM** directory in Google Drive.  
This directory contains two main datasets:

```
DICOM/
├── 00003946/          # Two patient samples; no context.xml files
└── Bladder 13.11.25/  # 66 patient samples
```

Each patient folder inside *Bladder 13.11.25* follows a Sectra IDS7 export structure, containing DICOM files and metadata.

---

## **1.1 Patient-Level Folder Structure**

A typical patient folder (e.g., *3129058*) contains:

```
PatientFolder/
├── DICOM/
├── SECTRA/
├── DICOMDIR
└── README.TXT
```

### **Component Summary**

| Item | Purpose |
|------|---------|
| **DICOM/** | Raw imaging files (DICOM format) |
| **SECTRA/** | Sectra-specific metadata, including CONTENT.xml |
| **DICOMDIR** | DICOM index file for viewers |
| **README.TXT** | Documentation of the export structure |

This export is a **DICOM‑only export**, meaning no web viewer or Windows viewer components are included.

---

## **1.2 Series-Level Structure Inside the DICOM Directory**

Inside each patient’s `DICOM/` directory, the data is further organized into nested folders representing the study hierarchy.

Example (from patient *30977820*):

```
DICOM/
└── 0000F605/
    └── AA4CCF18/
        └── AAC3864B/
            ├── 00000E64/
            ├── 000015BC/
            ├── 0000420E/
            ├── 00004A9B/
            ├── 000063CA/
            ├── 000069A9/
            ├── 00006FEC/
            ├── 000074B9/
            ├── 000075A6/
            ├── 00007722/
            ├── 00007ED3/
            ├── 00008B0B/
            ├── 0000981A/
            └── 0000FFDD/
```

Each leaf folder (e.g., `0000420E/`, `00006FEC/`) contains:

- A **single imaging series**
- A set of `.dcm` files belonging to that series
- No metadata files inside the folder itself

The folder names are **not informative** on their own — their meaning comes from the metadata.

---

## **1.3 SECTRA/CONTENT.xml — Metadata Mapping**

Inside the `SECTRA/` directory, the file **CONTENT.xml** provides a complete metadata map of the study.

It includes:

- **Session information**  
  e.g., `<date>13/11/2025</date>`
- **Patient metadata**  
  e.g., `<name>Anonymous</name>`
- **Study details**  
  e.g., `<body_part>FDG PET imaging</body_part>`
- **Series metadata**  
  (modality, series number, description)
- **Image entries**, each with timestamps and a file path  
  e.g.,  
  `../DICOM\000022DA\AA914B80\AAED8CA9\000042BA\EEE93CAA`

### **Purpose of CONTENT.xml**

CONTENT.xml allows us to:

- Identify the **modality** of each series (CT, PT, etc.)
- Retrieve the **series description** (e.g., “CT 2.5 mm”)
- Map each folder (e.g., `0000420E/`) to its correct series
- Validate dataset completeness
- Generate **informative filenames** during reorganization

In short:

> **The DICOM folder contains the raw files; CONTENT.xml explains what each folder represents.**

---

## **1.4 Final Summary**

The raw dataset consists of:

- **DICOM/** — the actual imaging data  
- **SECTRA/CONTENT.xml** — the metadata needed to interpret and reorganize the data  
- **DICOMDIR** — optional viewer index  
- **README.TXT** — export documentation  

This structure provides all the information required for the reorganization script described in Chapter 2.

---

# **2. DICOM Reorganization Workflow**

This chapter describes the processing pipeline used to reorganize the raw Sectra DICOM exports into a clean, structured, analysis‑ready format.  
The workflow is implemented using a custom Python script that parses Sectra metadata, identifies imaging series, matches PET and CT acquisitions, and rewrites DICOM metadata to produce a standardized output.

---

## **2.1 Overview of the Sorting Script**

The script (`DICOM PET/CT Sorting and Filtering Tool`) performs the following tasks:

1. **Locate and parse the Sectra `CONTENT.xml` file**  
   - Extracts metadata for each series: modality, description, series number, timestamps, and file paths.

2. **Build a complete map of all imaging series**  
   - Each series is represented by:  
     `{modality, number, description, time, files[]}`

3. **Match PET ↔ CT series**  
   - Identifies the best PET series (OB and WB)  
   - Matches each PET series to the closest CT series in time  
   - Tags matched pairs with `OB` or `WB`

4. **Generate informative, standardized series names**  
   - Using modality, description, series number, and match tag  
   - Example: `CT_WB_2.5_MM_S405`

5. **Rewrite DICOM metadata for consistency**  
   - New StudyInstanceUID  
   - New SeriesInstanceUID  
   - Updated SeriesDescription and ProtocolName  
   - Adds PET↔CT reference links

6. **Save all processed files into a clean output structure**  
   - Organized by study → modality → series

7. **Produce a log file**  
   - Summarizes all processed slices and matched series

---

## **2.2 Input and Output Structure**

### **Input (raw Sectra export)**

Example patient folder before processing:

```
30977820/
├── DICOM/
├── SECTRA/
├── DICOMDIR
└── README.TXT
```

### **Output (after running the script)**

After processing, the script creates a new study folder:

```
30977820/
└── Study_1.2.826.0.1.3680043.8.498.12319408040025917840117516826266744972/
    ├── CT/
    ├── PT/
    ├── OB/
    ├── WB/
    └── OT/
```

A log file is also generated:

```
sort_log_123628.txt
```

---

## **2.3 Meaning of the Output Folders**

Each top‑level folder inside the `Study_*` directory corresponds to a modality or matched PET/CT pair:

| Folder | Meaning |
|--------|---------|
| **CT/** | All CT series not part of OB/WB matching |
| **PT/** | All PET series not part of OB/WB matching |
| **OB/** | PET/CT matched “One Bed” pairs |
| **WB/** | PET/CT matched “Whole Body” pairs |
| **OT/** | Other modalities (e.g., fusion, dose reports) |

---

## **2.4 Example: Series Organization for Patient 30977820**

Based on the `ls` output you provided, the script produced the following series:

### **CT/**
Contains CT series such as:
```
CT_CTAC_3.75_THICK_S311/
CT_DOSE_REPORT_S1/
CT_WB_STANDARD_S311/
CT_WB_2.5_MM_S405/
```

### **PT/**
Contains PET series that were not matched:
```
PT_WB_NAC_S311/
PT_ONE_BED_NAC_S79/
```

### **OB/**
Contains matched One‑Bed PET/CT pairs:
```
PT_OB_ONE_BED_HD_S79/
CT_OB_2.5_MM_S102/
```

### **WB/**
Contains matched Whole‑Body PET/CT pairs:
```
PT_WB_QC_350_S311/
PT_WB_VPHD-S_MAC_S311/
```

### **OT/**
Contains additional series such as fusion images:
```
OT_FUSION_S311/
OT_FUSION_-_ONE_BED_S79/
```

These names are generated automatically by the script using the `friendly_name()` function, which cleans and standardizes the series descriptions.

---

## **2.5 How the Script Uses CONTENT.xml**

The `CONTENT.xml` file is essential for:

- Identifying each series  
- Mapping each DICOM file to its correct series  
- Extracting timestamps for PET↔CT matching  
- Determining modality and description  
- Ensuring no series is missed  

Example (from the XML):

> `<body_part>FDG PET imaging</body_part>`  
> `<modality>CT</modality>`  
> `<description>CT 2.5 mm</description>`  
> `<src>../DICOM\000022DA\AA914B80\AAED8CA9\000042BA\EEE93CAA</src>`

This metadata allows the script to reconstruct the full study hierarchy and assign meaningful names.

---

## **2.6 Final Output Structure**

After processing, each series is stored in its own folder with:

- Updated DICOM metadata  
- Consistent UIDs  
- Informative folder names  
- PET series containing references to their matched CT series  

Example:

```
Study_.../
└── OB/
    ├── PT_OB_ONE_BED_HD_S79/
    └── CT_OB_2.5_MM_S102/
```

---

## **2.7 Summary**

The sorting script transforms the raw Sectra export into a clean, structured dataset by:

- Parsing metadata  
- Matching PET and CT series  
- Standardizing names  
- Rewriting DICOM headers  
- Organizing files into modality‑based folders  

This structure is optimized for downstream analysis, machine learning pipelines, and reproducible research.

---
