# Cancer-detection-AI
Graduation project for detecting bladder cancer from CT/PET data using AI  
---
--- 

## Importent Links:
* data drive:  https://drive.google.com/drive/folders/0ADGtNOeBdU23Uk9PVA

---

## Project Structure

```
Cancer-detection-AI/
│
├── models/                 # AI models
│   └── petct-model/        # PET-CT detection model
│       └── CW-nnU-Net-for-PET-CT/
│
├── monai_server/           # MONAI server for medical imaging
│   ├── apps/              # Radiology applications
│   └── dataset/           # Dataset configuration
│       ├── datastore_v2.json
│       └── labels/        # Label definitions
│
├── src/                    # Source code
│   ├── sort_sectra.py     # Main sorting script for DICOM data
│   ├── warper.py          # Batch processing wrapper
│   ├── dicom_to_nifti.py  # DICOM to NIfTI conversion
│   ├── filter_OB_WB.py    # Filter OB/WB images
│   ├── viewer.py          # Medical image viewer
│   └── viewer_photo_save.py
│
├── Dockerfile              # Docker container configuration
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

---

## Directory Descriptions

| Directory | Description |
|-----------|-------------|
| `data/` | |
| `logs/` | Application logs, including download logs and processing logs. |
| `models/` | Trained AI models for cancer detection. Contains PET-CT specific models. |
| `monai_server/` | MONAI infrastructure for serving medical imaging AI models. |
| `src/` | Core Python source code for the project - sorting, conversion, and viewing utilities. |

---

## Quick Start

## running the sort function on one study :

```bash
python src/sort_sectra.py path_to_dir_in path_to_out
```

Use `--debug` to write a detailed log and print debug messages:

## Batch Processing (Warper)
To run the sorting process on multiple patient folders sequentially, use the warper.py CLI tool. It iterates over all patient directories in the input folder and generates a centralized master_log.txt.

Run on all folders:

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py
```

Run a test on a limited number of folders (e.g., 3 folders):

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py -n 3
```

Run with debug logs enabled:

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py --debug
```


## Running on an HPC Cluster (Slurm)
For processing large datasets on university/academic clusters, use the provided submit_sorter.sh bash script to queue the batch job via Slurm.

1. Submit the job to the cluster:
```bash
sbatch submit_sorter.sh
```

2. Check your job status in the queue:
``` bash
squeue -u $USER
```
(Look for R for Running, or PD for Pending).

3. Monitor logs in real-time:
The output will be written to a file named sorter_log_<job_id>.out in your current directory.

```bash
tail -f sorter_log_<job_id>.out
```
4. Cancel a running job (if needed):
```bash
scancel <job_id>
````
