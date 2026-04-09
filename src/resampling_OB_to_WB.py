import os
import ants
from pathlib import Path
from tqdm import tqdm

def find_modality_file(folder_path: Path, keywords: list):
    """
    Finds a NIfTI file in the folder that matches one of the keywords (case-insensitive).
    """
    for file in folder_path.glob("*.nii.gz"):
        filename_upper = file.name.upper()
        if any(kw in filename_upper for kw in keywords):
            return file
    return None

def register_patient_data(wb_dir: Path, ob_dir: Path, output_dir: Path):
    """
    Performs elastic registration (SyN) from OB to WB for a single patient,
    and applies the transforms to the OB CT, PET, and Mask (if exists).
    """
    wb_ct_path = find_modality_file(wb_dir, ["CT"])
    ob_ct_path = find_modality_file(ob_dir, ["CT"])
    ob_pet_path = find_modality_file(ob_dir, ["PT", "PET"])
    
    ob_mask_path = find_modality_file(ob_dir, ["MASK", "LABEL", "SEG"])

    if not wb_ct_path or not ob_ct_path or not ob_pet_path:
        # ההדפסה כאן שונתה קצת כדי לא לקרוס אם המבנה עמוק
        print(f"\n[ERROR] Missing required CT/PET files in {wb_dir.name} or {ob_dir.name}. Skipping.")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        fixed_wb_ct = ants.image_read(str(wb_ct_path))
        moving_ob_ct = ants.image_read(str(ob_ct_path))
        moving_ob_pet = ants.image_read(str(ob_pet_path))

        registration = ants.registration(
            fixed=fixed_wb_ct, 
            moving=moving_ob_ct, 
            type_of_transform='SyN',
            verbose=False
        )
        transforms = registration['fwdtransforms']

        warped_ob_ct = ants.apply_transforms(
            fixed=fixed_wb_ct, 
            moving=moving_ob_ct, 
            transformlist=transforms, 
            interpolator='linear'
        )
        warped_ob_pet = ants.apply_transforms(
            fixed=fixed_wb_ct, 
            moving=moving_ob_pet, 
            transformlist=transforms, 
            interpolator='linear'
        )

        ants.image_write(warped_ob_ct, str(output_dir / "Warped_OB_CT.nii.gz"))
        ants.image_write(warped_ob_pet, str(output_dir / "Warped_OB_PET.nii.gz"))
        
        ants.image_write(fixed_wb_ct, str(output_dir / "Original_WB_CT.nii.gz"))
        wb_pet_path = find_modality_file(wb_dir, ["PT", "PET"])
        if wb_pet_path:
            fixed_wb_pet = ants.image_read(str(wb_pet_path))
            ants.image_write(fixed_wb_pet, str(output_dir / "Original_WB_PET.nii.gz"))

        if ob_mask_path:
            moving_ob_mask = ants.image_read(str(ob_mask_path))
            warped_ob_mask = ants.apply_transforms(
                fixed=fixed_wb_ct, 
                moving=moving_ob_mask, 
                transformlist=transforms, 
                interpolator='nearestNeighbor'
            )
            ants.image_write(warped_ob_mask, str(output_dir / "Warped_OB_Mask.nii.gz"))

        return True

    except Exception as e:
        print(f"\n[ERROR] Process failed for {wb_dir}: {e}")
        return False

def process_entire_dataset(input_root: Path, output_root: Path):
    """
    Iterates over the dataset folder structure with a progress bar,
    searching deeply (recursively) for WB and OB folders.
    """
    print("===== STARTING DATASET REGISTRATION =====")
    
    patient_dirs = [d for d in input_root.iterdir() if d.is_dir()]
    
    for patient_dir in tqdm(patient_dirs, desc="Processing Patients", unit="patient"):
        patient_id = patient_dir.name
        
        # --- השינוי כאן: rglob במקום iterdir ---
        # rglob("*") סורק כל תיקייה ותת-תיקייה בתוך המטופל
        wb_dirs = [d for d in patient_dir.rglob("*") if d.is_dir() and "WB" in d.name.upper()]
        ob_dirs = [d for d in patient_dir.rglob("*") if d.is_dir() and "OB" in d.name.upper()]
        
        if wb_dirs and ob_dirs:
            wb_dir = wb_dirs[0]
            ob_dir = ob_dirs[0]
            
            patient_output_dir = output_root / patient_id
            register_patient_data(wb_dir, ob_dir, patient_output_dir)
        else:
            tqdm.write(f"[WARNING] Skipping Patient {patient_id}: Missing OB or WB directory inside studies.")

    print("\n===== ALL DONE! =====")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Register and Resample OB NIfTI scans to WB scans")
    
    parser.add_argument("-i", "--input_dir", required=True, help="Root directory containing Patient folders")
    parser.add_argument("-o", "--output_dir", required=True, help="Target directory for the registered files")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)
    
    process_entire_dataset(input_path, output_path)