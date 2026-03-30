import os
import argparse
import pydicom
import SimpleITK as sitk

def calculate_translation_offset(fixed_dir, moving_dir):
    """מחשב את ההזזה המדויקת בין ה-WB ל-OB"""
    print(f"  [+] Calculating offset...")
    print(f"      Fixed (WB): {os.path.basename(fixed_dir)}")
    print(f"      Moving (OB): {os.path.basename(moving_dir)}")
    
    reader = sitk.ImageSeriesReader()
    
    fixed_series_names = reader.GetGDCMSeriesFileNames(fixed_dir)
    reader.SetFileNames(fixed_series_names)
    fixed_image = reader.Execute()

    moving_series_names = reader.GetGDCMSeriesFileNames(moving_dir)
    reader.SetFileNames(moving_series_names)
    moving_image = reader.Execute()

    fixed_image = sitk.Cast(fixed_image, sitk.sitkFloat32)
    moving_image = sitk.Cast(moving_image, sitk.sitkFloat32)

    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMeanSquares()
    
    # ==========================================
    # התיקון: חישוב מרכזים פיזיים ידנית במקום CenteredTransformInitializer
    # ==========================================
    fixed_size = fixed_image.GetSize()
    moving_size = moving_image.GetSize()

    # מציאת הנקודה הפיזית במרחב של אמצע כל סריקה
    fixed_center = fixed_image.TransformContinuousIndexToPhysicalPoint(
        [(sz - 1) / 2.0 for sz in fixed_size]
    )
    moving_center = moving_image.TransformContinuousIndexToPhysicalPoint(
        [(sz - 1) / 2.0 for sz in moving_size]
    )

    # וקטור ההזזה ההתחלתי: כמה צריך להזיז את מרכז ה-OB כדי שישב על מרכז ה-WB
    initial_offset = [fc - mc for fc, mc in zip(fixed_center, moving_center)]

    # הגדרת ההזזה ההתחלתית
    initial_transform = sitk.TranslationTransform(3)
    initial_transform.SetOffset(initial_offset)
    
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    # Multi-Resolution כדי לא למצוא התאמות שגויות (מינימום מקומי)
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    registration_method.SetOptimizerAsRegularStepGradientDescent(
        learningRate=2.0, minStep=0.01, numberOfIterations=200
    )
    registration_method.SetInterpolator(sitk.sitkLinear)

    # ביצוע הרגיסטרציה (פיין-טיונינג מהמרכז)
    final_transform = registration_method.Execute(fixed_image, moving_image)
    offset = final_transform.GetParameters()
    
    print(f"  [V] Offset found (X, Y, Z) in mm: {offset}")
    return offset


def apply_offset_to_dicom_folder(folder_path, offset):
    """מחיל את ההזזה על כל קבצי ה-DICOM בתיקייה (CT ו-PET)"""
    updated_count = 0
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        if not os.path.isfile(filepath):
            continue
        
        try:
            ds = pydicom.dcmread(filepath)
            if 'ImagePositionPatient' in ds:
                current_pos = ds.ImagePositionPatient
                
                # התיקון: חיסור ההזזה במקום חיבור כדי להזיז לכיוון ה-Fixed
                new_pos = [
                    float(current_pos[0]) - offset[0],
                    float(current_pos[1]) - offset[1],
                    float(current_pos[2]) - offset[2]
                ]
                ds.ImagePositionPatient = new_pos
                ds.save_as(filepath)
                updated_count += 1
        except Exception:
            pass

    print(f"  [V] Applied offset to {updated_count} files in {os.path.basename(folder_path)}")
 

def get_referenced_ct_folder(pet_folder, ct_root):
    """מוצא את תיקיית ה-CT שמשויכת ל-PET על בסיס ה-Reference שהוזרק בקוד הקודם"""
    pet_files = [f for f in os.listdir(pet_folder) if os.path.isfile(os.path.join(pet_folder, f))]
    if not pet_files:
        return None
        
    pet_ds = pydicom.dcmread(os.path.join(pet_folder, pet_files[0]))
    if 'ReferencedSeriesSequence' not in pet_ds:
        return None
        
    ref_ct_uid = pet_ds.ReferencedSeriesSequence[0].SeriesInstanceUID
    
    # חיפוש תיקיית ה-CT עם ה-UID הזה
    for ct_dir_name in os.listdir(ct_root):
        ct_dir_path = os.path.join(ct_root, ct_dir_name)
        if os.path.isdir(ct_dir_path):
            ct_files = [f for f in os.listdir(ct_dir_path) if os.path.isfile(os.path.join(ct_dir_path, f))]
            if ct_files:
                ct_ds = pydicom.dcmread(os.path.join(ct_dir_path, ct_files[0]))
                if ct_ds.SeriesInstanceUID == ref_ct_uid:
                    return ct_dir_path
    return None

def process_study(study_path):
    """מעבד Study בודד - מזהה WB ו-OB, מחשב ומחיל הזזות"""
    print(f"\n===== Processing {os.path.basename(study_path)} =====")
    
    pet_root = os.path.join(study_path, "PET")
    ct_root = os.path.join(study_path, "CT")
    
    if not os.path.exists(pet_root) or not os.path.exists(ct_root):
        print("  [!] Missing PET or CT directories. Skipping.")
        return

    wb_pet_dir = None
    ob_pet_dirs = []

    # סיווג תיקיות ה-PET ל-WB ול-OB לפי השם שהגדרת ב-friendly_name
    for pet_name in os.listdir(pet_root):
        full_path = os.path.join(pet_root, pet_name)
        if not os.path.isdir(full_path): continue
        
        name_upper = pet_name.upper()
        if "OB" in name_upper or "ONE_BED" in name_upper:
            ob_pet_dirs.append(full_path)
        else:
            # נניח שהראשון שאינו OB הוא ה-WB
            if wb_pet_dir is None:
                wb_pet_dir = full_path

    if not wb_pet_dir:
        print("  [!] Could not identify a WB PET series. Skipping.")
        return
        
    if not ob_pet_dirs:
        print("  [!] No OB series found in this study. Nothing to align.")
        return

    wb_ct_dir = get_referenced_ct_folder(wb_pet_dir, ct_root)
    if not wb_ct_dir:
        print("  [!] Could not find referenced WB CT. Skipping.")
        return

    # מעבר על כל סדרות ה-OB (במקרה שיש יותר מאחת)
    for ob_pet_dir in ob_pet_dirs:
        print(f"\n  Aligning OB pair: {os.path.basename(ob_pet_dir)}")
        ob_ct_dir = get_referenced_ct_folder(ob_pet_dir, ct_root)
        
        if not ob_ct_dir:
            print(f"  [!] Could not find referenced CT for {os.path.basename(ob_pet_dir)}. Skipping.")
            continue
            
        try:
            # 1. חישוב ההזזה על בסיס ה-CT
            offset = calculate_translation_offset(wb_ct_dir, ob_ct_dir)
            
            # 2. החלת ההזזה על ה-CT של ה-OB
            apply_offset_to_dicom_folder(ob_ct_dir, offset)
            
            # 3. החלת אותה ההזזה בדיוק על ה-PET של ה-OB
            apply_offset_to_dicom_folder(ob_pet_dir, offset)
            
        except Exception as e:
            print(f"  [ERROR] Failed to align {os.path.basename(ob_pet_dir)}: {e}")

def main(root_output_folder):
    """עובר על כל תיקיות ה-Study שנוצרו בסקריפט הקודם"""
    print(f"Starting automatic alignment in: {root_output_folder}")
    
    for item in os.listdir(root_output_folder):
        study_path = os.path.join(root_output_folder, item)
        if os.path.isdir(study_path) and item.startswith("Study_"):
            process_study(study_path)
            
    print("\n[DONE] All OB series have been spatially aligned to their respective WB series.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-align OB series to WB series based on sorted output.")
    parser.add_argument("sorted_folder", help="Path to the output folder generated by the sorting script")
    args = parser.parse_args()
    
    main(args.sorted_folder)