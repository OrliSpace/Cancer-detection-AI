# **📁 Drive Folder Map**

A structured overview of the directory hierarchy in the shared drive, including raw DICOM data, processed outputs, code, documentation, and project management files.

```
/Sandler_and_Kaminka/
│
├── DICOM/
│   ├── 00003946/
│   │   ├── <Patient_1>/
│   │   └── <Patient_2>/
│   │
│   └── Bladder 13.11.25/
│       ├── 30977820/
│       │   ├── DICOM/
│       │   ├── SECTRA/
│       │   │   └── CONTENT.xml
│       │   ├── DICOMDIR
│       │   ├── README.TXT
│       │   └── sort_log_*.txt
│       │
│       ├── 30984433/
│       │   ├── DICOM/
│       │   ├── SECTRA/
│       │   ├── DICOMDIR
│       │   ├── README.TXT
│       │   └── sort_log_*.txt
│       │
│       └── ... (64 additional patient folders)
│
│
├── Ordered_DICOM/
│   └── Bladder 13.11.25/
│       ├── 30977820/
│       │   └── Study_<UID>/
│       │       ├── CT/
│       │       ├── PT/
│       │       ├── OB/
│       │       ├── WB/
│       │       └── OT/
│       │
│       ├── 30984433/
│       │   └── Study_<UID>/
│       │       ├── CT/
│       │       ├── PT/
│       │       ├── OB/
│       │       ├── WB/
│       │       └── OT/
│       │
│       └── ... (processed folders for all patients)
│
│
├── Introductory Materials for CS/
│   └── Deep learning techniques in PET/CT imaging.pdf
│       # A review paper used as background material for the project
│
├── monai_server/
│   # A mock MONAI server used for testing Active Learning workflows
│   # Intended for future OB labeling automation
│
├── code/
│   # Local scripts executed via Google Colab
│   # Includes utilities for scanning, validating, and testing DICOM folders
│
├── 0README/
│   # Contains links to Git repositories and specific files in GitHub
│
├── מושגים של CT_PET/
│   # Glossary of CT/PET terminology
│
├── שאלות לישראל/
│   # Questions prepared for Israel regarding the project
│
├── GRAND TASK LIST/
│   # Shared task list maintained by Gal and Israel
│
└── TODO FILE/
    # Task list for Orly and Roee
```

---

# **📌 Short Explanations of the New Folders**

### **Introductory Materials for CS/**
Contains background reading materials.  
Currently includes the PDF:  
*“Deep learning techniques in PET/CT imaging: A comprehensive review — from sinogram to image space.”*

### **monai_server/**
A mock MONAI server used for experimenting with **Active Learning** workflows for OB labeling.

### **code/**
Local Python scripts used in Colab to test, validate, and inspect DICOM directories.

### **0README/**
A collection of links to GitHub repositories and specific project files.

### **מושגים של CT_PET/**
A glossary of CT/PET terminology.

### **שאלות לישראל/**
A folder containing questions prepared for Israel regarding the project.

### **GRAND TASK LIST/**
A shared task list maintained by Gal and Israel.

### **TODO FILE/**
A task list specifically for Orly and Roee.

---
