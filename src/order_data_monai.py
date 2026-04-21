import shutil
from pathlib import Path

def prepare_monai_dataset():
    # הגדרת הנתיבים שלך (מבוסס על מבנה התיקיות שראינו)
    base_dir = Path(r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI")
    src_dir = base_dir / "data" / "nifti"
    dest_dir = base_dir / "monai_server" / "dataset"

    # יצירת תיקיית היעד בשרת אם היא לא קיימת
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching for patients in: {src_dir}\n" + "-"*40)

    # מעבר על כל התיקיות בתוך התיקייה הראשית (כל תיקייה היא מטופל)
    for patient_folder in src_dir.iterdir():
        if patient_folder.is_dir():
            patient_id = patient_folder.name
            print(f"Processing patient ID: {patient_id}")

            # rglob מחפש את הקבצים בכל תתי-התיקיות פנימה (מושלם לתיקיות ה-Study העמוקות)
            ct_files = list(patient_folder.rglob("CT_*.nii.gz"))
            pet_files = list(patient_folder.rglob("PT_*.nii.gz"))

            # מציאה והעתקה של סריקת ה-CT
            if ct_files:
                ct_source = ct_files[0]
                ct_dest = dest_dir / f"patient_{patient_id}_ct.nii.gz"
                shutil.copy2(ct_source, ct_dest)
                print(f"  [V] Copied CT -> {ct_dest.name}")
            else:
                print("  [X] Warning: No CT scan found for this patient.")

            # מציאה והעתקה של סריקת ה-PET
            if pet_files:
                pet_source = pet_files[0]
                pet_dest = dest_dir / f"patient_{patient_id}_pet.nii.gz"
                shutil.copy2(pet_source, pet_dest)
                print(f"  [V] Copied PET -> {pet_dest.name}")
            else:
                print("  [X] Warning: No PET scan found for this patient.")
            
            print("-" * 40)

    print("\nDataset preparation completed successfully!")

if __name__ == "__main__":
    prepare_monai_dataset()