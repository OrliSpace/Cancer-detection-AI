import os
from pathlib import Path
from tqdm import tqdm
import affine_reg
import deform_reg

def process_all_patients(input_root, output_root):
    input_root = Path(input_root)
    output_root = Path(output_root)
    
    # 1. מציאת כל תיקיות המטופלים (אלו ששמם הוא מספר/מזהה)
    patient_dirs = [d for d in input_root.iterdir() if d.is_dir()]
    print(f"📂 Found {len(patient_dirs)} patients in {input_root}")

    for patient_dir in tqdm(patient_dirs, desc="Overall Progress"):
        patient_id = patient_dir.name
        
        # 2. חיפוש תיקיית ה-Study (יכולה להיות יותר מאחת, אז נעבור על כולן)
        study_dirs = [d for d in patient_dir.glob("Study_*") if d.is_dir()]
        
        for study_dir in study_dirs:
            study_id = study_dir.name
            
            # הגדרת נתיבי WB ו-OB
            wb_dir = study_dir / "WB"
            ob_dir = study_dir / "OB"
            
            # בדיקה ששני המצבים קיימים לפני שרצים
            if not (wb_dir.exists() and ob_dir.exists()):
                print(f"⚠️ Skipping {patient_id}/{study_id}: Missing WB or OB folder.")
                continue

            # יצירת תיקיית פלט ספציפית למטופל ולמחקר
            current_output_dir = output_root / patient_id / study_id
            current_output_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n[PROCESSING] Patient: {patient_id} | Study: {study_id}")

            try:
                # # הרצת Affine
                # affine_reg.register_patient_data_affine(
                #     wb_dir=wb_dir, 
                #     ob_dir=ob_dir, 
                #     output_dir=current_output_dir, 
                #     debug=True
                # )

                # הרצת Deformable (SyNRA)
                deform_reg.register_patient_data_deform(
                    wb_dir=wb_dir, 
                    ob_dir=ob_dir, 
                    output_dir=current_output_dir, 
                    debug=True
                )
                
            except Exception as e:
                print(f"❌ Error processing {patient_id}: {e}")

if __name__ == "__main__":
    # נתיבי בסיס (לפי המבנה שלך)
    INPUT_PATH = r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\data\nifti"
    OUTPUT_PATH = r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\data\results"

    process_all_patients(INPUT_PATH, OUTPUT_PATH)