#!/bin/bash
#SBATCH --job-name=rclone_upload
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --partition=generic

rclone copy /home/dsi/kadoshr5/dicom_project/Ordered_DICOM_Samples drive:Ordered_DICOM -P --transfers 8 --checkers 16
