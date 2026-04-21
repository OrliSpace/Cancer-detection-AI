import os
import shutil
from pathlib import Path
import dicom2nifti
import dicom2nifti.settings as settings
import nibabel as nib
import nilearn.image

FLAG_NAME = ".conversion_done"


def is_dicom_file(path: Path):
    if path.suffix.lower() == ".dcm":
        return True
    try:
        with open(path, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except:
        return False


def convert_dicom_folder(dicom_dir: Path, output_file: Path):
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        settings.disable_validate_slice_increment()
        settings.disable_validate_orthogonal()
        settings.disable_validate_slicecount()

        dicom2nifti.dicom_series_to_nifti(str(dicom_dir), str(output_file))
        print(f"  [SUCCESS] Saved: {output_file.name}")
        return True
    except Exception as e:
        # עכשיו אנחנו רק מדפיסים אזהרה ולא מכשילים את המטופל
        print(f"  [SKIPPED] Cannot convert {dicom_dir.name} (likely Dose Report/Localizer): {e}")
        return False


def resample_ct(ct_path: Path, pet_path: Path, out_path: Path):
    print(f"  [INFO] Resampling CT to PET space:\n    -> CT:  {ct_path.name}\n    -> PET: {pet_path.name}")
    try:
        ct = nib.load(str(ct_path))
        pet = nib.load(str(pet_path))

        ct_res = nilearn.image.resample_to_img(ct, pet, fill_value=-1024)
        nib.save(ct_res, str(out_path))

        print(f"  [SUCCESS] Saved resampled CT: {out_path.name}")
        return True
    except Exception as e:
        print(f"  [ERROR] Resampling failed for {ct_path.name}: {e}")
        return False


def pick_best_pet(pet_files):
    # מסננים החוצה סריקות ללא תיקון הנחתה (NAC)
    valid = [f for f in pet_files if "NAC" not in f.name.upper()]
    if not valid: 
        return None

    # עדיפות 1: ה-QC שהרופא ביקש
    qc = [f for f in valid if "QC" in f.name.upper()]
    if qc: return qc[0]

    # עדיפות 2: VPHD או HD
    hd = [f for f in valid if "VPHD" in f.name.upper() or "HD" in f.name.upper()]
    if hd: return hd[0]

    # עדיפות 3: כל מה שנשאר
    return valid[0]


def pick_best_ct(ct_files):
    # עדיפות ל-2.5 מ"מ
    best = [f for f in ct_files if "2.5" in f.name.upper()]
    if best: return best[0]
    return ct_files[0] if ct_files else None


def organize_and_resample_patient(patient_dir: Path):
    """
    ממיין את הנתונים, מעביר את המיותרים לארכיון, ועושה Resampling לרביעיית הזהב
    """
    all_niftis = list(patient_dir.glob("*.nii.gz"))
    if not all_niftis:
        return

    print(f"\n  [INFO] Organizing data for {patient_dir.name}...")

    # חלוקה ל"בריכות" של OB ו-WB לפי השם (כולל ONE_BED כי ראינו שזה מופיע ב-OB PET)
    ob_pool = [f for f in all_niftis if "OB" in f.name.upper() or "ONE_BED" in f.name.upper()]
    wb_pool = [f for f in all_niftis if f not in ob_pool]

    # הפרדה ל-CT ו-PET בכל בריכה
    ob_cts = [f for f in ob_pool if "CT" in f.name.upper() and "PT" not in f.name.upper() and "PET" not in f.name.upper()]
    ob_pets = [f for f in ob_pool if ("PT" in f.name.upper() or "PET" in f.name.upper())]
    
    wb_cts = [f for f in wb_pool if "CT" in f.name.upper() and "PT" not in f.name.upper() and "PET" not in f.name.upper()]
    wb_pets = [f for f in wb_pool if ("PT" in f.name.upper() or "PET" in f.name.upper())]

    # בחירת הכוכבים שלנו
    best_ob_ct = pick_best_ct(ob_cts)
    best_ob_pet = pick_best_pet(ob_pets)
    best_wb_ct = pick_best_ct(wb_cts)
    best_wb_pet = pick_best_pet(wb_pets)

    chosen_files = [f for f in [best_ob_ct, best_ob_pet, best_wb_ct, best_wb_pet] if f is not None]

    # יצירת ארכיון והעברת כל מה שלא נבחר
    archive_dir = patient_dir / "archive"
    
    for f in all_niftis:
        if f not in chosen_files:
            archive_dir.mkdir(exist_ok=True)
            shutil.move(str(f), str(archive_dir / f.name))
            print(f"    -> Moved to archive: {f.name}")

    # ביצוע ה-Resampling רק למי שנבחר להישאר (והחלפת המקור כדי לשמור על השם שאהבת)
    if best_wb_ct and best_wb_pet:
        temp_path = patient_dir / best_wb_ct.name.replace(".nii.gz", "_temp.nii.gz")
        if resample_ct(best_wb_ct, best_wb_pet, temp_path):
            best_wb_ct.unlink()
            temp_path.rename(best_wb_ct)

    if best_ob_ct and best_ob_pet:
        temp_path = patient_dir / best_ob_ct.name.replace(".nii.gz", "_temp.nii.gz")
        if resample_ct(best_ob_ct, best_ob_pet, temp_path):
            best_ob_ct.unlink()
            temp_path.rename(best_ob_ct)


def convert_tree(input_root, output_root):
    input_root = Path(input_root)
    output_root = Path(output_root)

    print("===== STARTING DICOM TO NIFTI CONVERSION =====")

    # 1. מיפוי מקדים
    patient_series_map = {}
    for dirpath, _, _ in os.walk(input_root):
        dirpath = Path(dirpath)
        dicom_files = [f for f in dirpath.iterdir() if f.is_file() and is_dicom_file(f)]
        if dicom_files:
            rel = dirpath.relative_to(input_root)
            patient_id = rel.parts[0]
            if patient_id not in patient_series_map:
                patient_series_map[patient_id] = []
            patient_series_map[patient_id].append(dirpath)

    # 2. המרה וניהול חכם של ה-Flag
    for patient_id, series_paths in patient_series_map.items():
        output_folder = output_root / patient_id
        flag_file = output_folder / FLAG_NAME
        
        if flag_file.exists():
            print(f"\n[SKIP] Patient already processed: {patient_id}")
            continue
            
        print(f"\n[INFO] Processing Patient: {patient_id} ({len(series_paths)} series found)")
        
        successful_series = [] # רשימה שתשמור רק את מה שהצליח
        
        for dirpath in series_paths:
            rel = dirpath.relative_to(input_root)
            folder_name = rel.name.replace("OB_ONE_BED", "OB").replace("ONE_BED", "OB")
            
            output_file = output_folder / f"{folder_name}.nii.gz"
            
            # בודקים אם הקובץ כבר הומר בעבר (כדי שאפשר יהיה להפסיק ולהמשיך)
            if output_file.exists():
                print(f"  [SKIP] Series already converted: {folder_name}")
                successful_series.append(folder_name)
                continue

            print(f"  -> Converting: {folder_name}")
            if convert_dicom_folder(dirpath, output_file):
                successful_series.append(folder_name)

        # כותבים לפלאג את כל מה שהצליח, גם אם ה-Dose Report נכשל!
        if successful_series:
            flag_file.write_text("\n".join(successful_series))
            print(f"✅ [DONE] Patient {patient_id} conversion finished. Logged {len(successful_series)} successfull series.")
            
            # קריאה לארגון הארכיון וה-Resampling רק אחרי שהמטופל סיים המרה
            organize_and_resample_patient(output_folder)

    print("\n[INFO] All data pipelines completed.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    convert_tree(args.input_dir, args.output_dir)