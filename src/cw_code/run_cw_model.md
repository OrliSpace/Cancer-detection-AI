```markdown
# Setup & Execution Guide: PET/CT Preprocessing Pipeline for nnUNet 🚀

This document outlines how to use the pipeline script to process medical scans (DICOM or NIfTI) and prepare them for training with the nnUNet framework.

## 📌 Pipeline Overview
The main script automatically performs the following steps:
1. **Conversion (Conditional):** Detects DICOM files and converts them to NIfTI format. If NIfTI files are already present, this step is skipped.
2. **Normalization:** Normalizes pixel intensities for both CT and PET scans.
3. **Smart ID Extraction & nnUNet Structuring:** Deeply scans the directory tree to find CT/PET pairs. It smartly extracts the patient ID and scan type (e.g., `OB`, `WB`) to prevent data overwriting, renaming the files with the required nnUNet suffixes (`_0000` for CT and `_0001` for PET).
4. **MHA Conversion:** Converts the structured NIfTI files into `.mha` format, placing them in the final `imagesTr` directory while automatically fixing any double extensions (like `.nii.mha`).
5. **Cleanup:** Deletes intermediate temporary NIfTI folders to save substantial disk space.

---

## 📂 Required Input Data Structure
The code is designed to recursively search for scans, but **each patient must have their own top-level folder**.
The path you provide to the script (`input_root`) should be the main directory containing these patient folders:

```text
data/sorted/              <-- This is your input_root
├── 3129058/              <-- Patient ID folder
│   ├── Study_1.2.3.../   <-- (This intermediate folder name is ignored by the script)
│   │   ├── OB/           <-- Scan Type (Extracted for the final filename)
│   │   │   ├── CT/       <-- Contains CT DICOM/NIfTI files
│   │   │   └── PET/      <-- Contains PET DICOM/NIfTI files
│   │   └── WB/
│   │       ├── CT/
│   │       └── PET/
```

---

## 💻 How to Run (Local Machine)

Open your terminal or command prompt, activate your Python virtual environment, and run the following command. 
*Note: Replace the paths with your actual local paths.*

```bash
python .\src\preper_data_CW.py data\nifti data\model
```
---

## 📦 Final Output Structure
Once the pipeline finishes successfully, a new folder will be created at your specified `output_root`. 
All scans are now perfectly formatted and ready for nnUNet training:

```text
data/model/
├── pipeline_log_20260412_104500.txt  <-- Detailed execution log
└── mha_output/
    └── imagesTr/                     <-- Target folder for nnUNet
        ├── 3129058_OB_0000.mha       <-- OB scan: CT
        ├── 3129058_OB_0001.mha       <-- OB scan: PET
        ├── 3129058_WB_0000.mha       <-- WB scan: CT
        └── 3129058_WB_0001.mha       <-- WB scan: PET
```
```