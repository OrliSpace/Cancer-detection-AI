# Cancer-detection-AI
Graduation project for detecting bladder cancer from CT/PET data using AI


## running the sort function on one study :

python src/sort_dicom.py path_to_dir_in path_to_out

## usage examples

Sort all DICOM series from a Sectra export folder:

python src/sort_sectra.py c:\path\to\input\patient_folder c:\path\to\output\folder

Sort and filter high-quality PET/CT pairs only:

python src/filter_OB_WB.py c:\path\to\input\patient_folder c:\path\to\output\folder

Use `--debug` to write a detailed log and print debug messages:

python src/filter_OB_WB.py c:\path\to\input\patient_folder c:\path\to\output\folder --debug
