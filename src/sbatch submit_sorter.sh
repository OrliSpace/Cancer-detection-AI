#!/bin/bash

#SBATCH --job-name=dicom_sort
#SBATCH --output=sorter_log_%j.out
#SBATCH --error=sorter_error_%j.err

#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --partition=generic

# טעינת סביבה (יש לוודא שהגרסה מתאימה למה שמותקן אצלכם)
module load python
source /home/dsi/kadoshr5/venvs/nnunet_v1_legacy/bin/activate
# הגדרת נתיבים
INPUT_DIR="/home/dsi/kadoshr5/NIFTI_FINAL_After_Bulk/Bladder 13.11.25"
OUTPUT_DIR="$HOME/dicom_project/Ordered_DICOM_Samples"
SCRIPT_PATH="$HOME/order_wraper/sort_sectra.py" # הסקריפט שממיין
BATCH_RUNNER="$HOME/order_wraper/warper.py"      # הסקריפט שעוטף הכל

echo "Starting DICOM sorting job at $(date)"

# הרצת ה-warper.py
python3 "$BATCH_RUNNER" \
    -i "$INPUT_DIR" \
    -o "$OUTPUT_DIR" \
    -s "$SCRIPT_PATH"

echo "Job finished at $(date)"
