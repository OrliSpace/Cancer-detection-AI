#!/bin/bash

#SBATCH --job-name=dicom_sort
#SBATCH --output=sorter_log_%j.out
#SBATCH --error=sorter_error_%j.err
#SBATCH --time=24:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --partition=main

# טעינת סביבה (יש לוודא שהגרסה מתאימה למה שמותקן אצלכם)
module load python/3.10
source ~/dicom_project/env/bin/activate

# הגדרת נתיבים
INPUT_DIR="$HOME/dicom_project/input"
OUTPUT_DIR="$HOME/dicom_project/output"
SCRIPT_PATH="$HOME/dicom_project/code/filter_OB_WB.py" # הסקריפט שממיין
BATCH_RUNNER="$HOME/dicom_project/code/warper.py"      # הסקריפט שעוטף הכל

echo "Starting DICOM sorting job at $(date)"

# הרצת ה-warper.py
python3 "$BATCH_RUNNER" \
    -i "$INPUT_DIR" \
    -o "$OUTPUT_DIR" \
    -s "$SCRIPT_PATH"

echo "Job finished at $(date)"