import os
import logging
from pathlib import Path
from tqdm import tqdm
import datetime

# ייבוא הפונקציות מהקבצים הקיימים שלך
from dicom_to_nifti import convert_tree as run_conversion
from deform_reg import register_patient_data_deform

def setup_logging(output_root):
    """מגדיר שמירת לוגים לקובץ במקום רק למסך"""
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_run_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler() # משאיר הדפסה בסיסית גם למסך
        ]
    )
    return log_file

def run_full_pipeline(dicom_root, nifti_root, transforms_root):
    dicom_root = Path(dicom_root)
    nifti_root = Path(nifti_root)
    transforms_root = Path(transforms_root)
    
    # 1. הגדרת לוגים
    log_path = setup_logging(nifti_root.parent)
    logging.info(f"🚀 Starting Pipeline. Logs saved to: {log_path}")

    # 2. שלב ההמרה (DICOM -> NIfTI + Resampling + Archiving)
    # הפונקציה הזו כבר כוללת את הלוגיקה של סינון ה-Dose Reports וה-Flags
    logging.info("--- Phase 1: DICOM to NIfTI Conversion ---")
    try:
        run_conversion(dicom_root, nifti_root)
        logging.info("✅ Conversion and organization completed.")
    except Exception as e:
        logging.error(f"❌ Critical error during conversion: {e}")
        return

    # 3. שלב הרגיסטרציה (WB -> OB)
    logging.info("--- Phase 2: Batch Registration ---")
    
    # עוברים על התיקיות השטוחות שנוצרו ב-nifti_root
    patient_dirs = [d for d in nifti_root.iterdir() if d.is_dir()]
    
    for patient_dir in tqdm(patient_dirs, desc="Registration Progress"):
        patient_id = patient_dir.name
        
        # איתור הקבצים הנבחרים (אחרי שהארכיון כבר נוקה)
        nii_files = list(patient_dir.glob("*.nii.gz"))
        
        # זיהוי Fixed (WB CT) ו-Moving (OB CT) לפי השמות ששמרנו
        fixed_cts = [f for f in nii_files if "WB" in f.name.upper() and "CT" in f.name.upper()]
        moving_cts = [f for f in nii_files if "OB" in f.name.upper() and "CT" in f.name.upper()]
        
        if not fixed_cts or not moving_cts:
            logging.warning(f"⚠️ Skipping registration for {patient_id}: Missing WB_CT or OB_CT pairs.")
            continue
            
        fixed_path = fixed_cts[0]
        moving_path = moving_cts[0]
        
        # הגדרת תיקיית פלט לטרנספורמציות
        patient_transform_dir = transforms_root / patient_id
        patient_transform_dir.mkdir(parents=True, exist_ok=True)
        
        # בדיקה אם כבר יש טרנספורמציה מוכנה
        if (patient_transform_dir / "1Warp.nii.gz").exists():
            logging.info(f"⏭️ Transforms for {patient_id} already exist. Skipping.")
            continue

        logging.info(f"🧠 Running registration for {patient_id}...")
        try:
            # שימוש בפונקציה מהקוד הקיים שלך
            # שימי לב: עדכנתי כאן שהיא תקבל את הנתיבים הישירים לקבצים שמצאנו
            register_patient_data_deform(
                fixed_img_path=str(fixed_path), 
                moving_img_path=str(moving_path), 
                output_dir=str(patient_transform_dir),
                debug=False # ה-logging המרכזי מנהל את זה עכשיו
            )
            logging.info(f"🎯 Registration successful for {patient_id}")
            
        except Exception as e:
            logging.error(f"❌ Registration failed for {patient_id}: {e}")

    logging.info("🎉 Full Pipeline Execution Finished.")

if __name__ == "__main__":
    # הגדרת נתיבים מקומיים (תשני לפי הצורך)
    BASE = Path(r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\data")
    
    DICOM_IN = BASE / "dicom"
    NIFTI_OUT = BASE / "nifti"
    TRANSFORMS_OUT = BASE / "transforms"

    run_full_pipeline(DICOM_IN, NIFTI_OUT, TRANSFORMS_OUT)