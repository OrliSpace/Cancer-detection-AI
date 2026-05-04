import nibabel as nib
import numpy as np
import os
from pathlib import Path

def create_monai_dataset(nifti_root: Path, monai_dataset_path: Path):
    """
    סורק את תיקיית הנתונים, מנקה את הת"ז,
    ושומר קבצי CT ו-PET בנפרד עם שמות תקינים.
    """
    monai_dataset_path.mkdir(parents=True, exist_ok=True)
    
    print(f"===== STARTING DATASET PACKAGING =====")
    print(f"Scanning {nifti_root} for patient data...\n")

    for patient_folder in nifti_root.iterdir():
        if not patient_folder.is_dir():
            continue
            
        original_patient_id = patient_folder.name

        # ניקוי מזהה המטופל
        clean_patient_id = original_patient_id.replace(" ", "").replace("+", "_")

        # חיפוש תיקיית OB
        ob_folders = list(patient_folder.rglob("OB"))
        if not ob_folders:
            print(f"[SKIP] No 'OB' folder found for patient {original_patient_id}")
            continue

        ob_folder = ob_folders[0]

        # איתור קבצי CT ו-PET
        ct_files = [f for f in ob_folder.glob("*.nii.gz") if "CT" in f.name.upper()]
        pet_files = [f for f in ob_folder.glob("*.nii.gz") if "PT" in f.name.upper() or "PET" in f.name.upper()]

        if len(ct_files) == 1 and len(pet_files) == 1:
            print(f"[INFO] Processing Patient: {original_patient_id} -> {clean_patient_id}")

            try:
                # טעינה
                ct_img = nib.load(str(ct_files[0]))
                pet_img = nib.load(str(pet_files[0]))

                # שמירה בנפרד
                ct_output = monai_dataset_path / f"{clean_patient_id}_CT.nii.gz"
                pet_output = monai_dataset_path / f"{clean_patient_id}_PET.nii.gz"

                nib.save(ct_img, str(ct_output))
                nib.save(pet_img, str(pet_output))

                print(f"[SUCCESS] Saved CT -> {ct_output.name}")
                print(f"[SUCCESS] Saved PET -> {pet_output.name}")

            except Exception as e:
                print(f"[ERROR] Failed to process patient {original_patient_id}: {e}")

        elif len(ct_files) > 1 or len(pet_files) > 1:
            print(f"[WARNING] Multiple CTs or PETs found for patient {original_patient_id}. Skipping.")
        else:
            print(f"[WARNING] Missing CT or PET for patient {original_patient_id}. Skipping.")

    print("\n===== PACKAGING COMPLETED =====")


if __name__ == "__main__":
    INPUT_ROOT = Path(r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\data\nifti")
    OUTPUT_DATASET = Path(r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\monai_server\dataset")
    
    create_monai_dataset(INPUT_ROOT, OUTPUT_DATASET)
