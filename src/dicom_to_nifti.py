import os
from pathlib import Path
import dicom2nifti
import dicom2nifti.settings as settings
import nibabel as nib
import nilearn.image

def is_dicom_file(path: Path):
    """Check if file is a DICOM by suffix or DICM header."""
    if path.suffix.lower() == ".dcm":
        return True
    try:
        with open(path, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except:
        return False

def convert_dicom_folder(dicom_dir: Path, output_file: Path):
    """
    Convert a DICOM series folder into a single NIfTI file.
    Output file name = folder name + .nii.gz
    """
    try:
        # Create parent folder if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Recommended settings (same as original code)
        settings.disable_validate_slice_increment()
        settings.disable_validate_orthogonal()
        settings.disable_validate_slicecount()

        dicom2nifti.dicom_series_to_nifti(
            str(dicom_dir),
            str(output_file)
        )

        print(f"[SUCCESS] Saved: {output_file}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed converting {dicom_dir}: {e}")
        return False

def resample_ct(ct_path: Path, pet_path: Path, out_path: Path):
    """Resample CT NIfTI to match PET space and dimensions."""
    print(f"[INFO] Resampling CT to PET space:\n  -> CT:  {ct_path.name}\n  -> PET: {pet_path.name}")
    try:
        ct = nib.load(str(ct_path))
        pet = nib.load(str(pet_path))
        
        # Resample with -1024 fill value (standard for CT air outside FOV)
        ct_res = nilearn.image.resample_to_img(ct, pet, fill_value=-1024)
        nib.save(ct_res, str(out_path))
        
        print(f"[SUCCESS] Saved resampled CT: {out_path.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Resampling failed for {ct_path.name}: {e}")
        return False

def post_process_resampling(output_root: Path):
    """
    Scan the output directory for matching CT/PET pairs in the same folder 
    and perform resampling. Replaces the original CT with the resampled one.
    """
    print("\n===== STARTING CT->PET RESAMPLING =====")

    # Group NIfTI files by their parent directory
    folder_groups = {}
    for nii_file in output_root.rglob("*.nii.gz"):
        parent = nii_file.parent
        if parent not in folder_groups:
            folder_groups[parent] = []
        folder_groups[parent].append(nii_file)

    for folder, files in folder_groups.items():
        # Identify CT and PET files based on standard naming conventions
        cts = [f for f in files if "CT" in f.name.upper() and "PT" not in f.name.upper() and "PET" not in f.name.upper()]
        pets = [f for f in files if "PT" in f.name.upper() or "PET" in f.name.upper()]

        # Only resample if exactly 1 CT and 1 PET are found in the same folder
        if len(cts) == 1 and len(pets) == 1:
            ct_file = cts[0]
            pet_file = pets[0]
            
            # Create a temporary path for the resampled file
            temp_resampled_path = folder / ct_file.name.replace(".nii.gz", "_temp_resampled.nii.gz")
            
            # Attempt resampling
            success = resample_ct(ct_file, pet_file, temp_resampled_path)
            
            # If successful, delete the original and rename the temp file to the original name
            if success:
                try:
                    ct_file.unlink() # Deletes the original CT file
                    temp_resampled_path.rename(ct_file) # Renames the resampled file to the original name
                    print(f"[INFO] Replaced original CT with resampled version successfully.")
                except Exception as e:
                    print(f"[ERROR] Failed to clean up or rename files in {folder.name}: {e}")
            
        elif len(cts) > 0 and len(pets) > 0:
            print(f"[WARNING] Multiple CTs ({len(cts)}) or PETs ({len(pets)}) found in {folder.name}. Skipping to avoid mismatches.")

def convert_tree(input_root, output_root):
    """
    Recursively scan for DICOM series folders and convert each to a NIfTI file,
    followed by an automatic resampling phase for matching CT/PET pairs.
    """
    input_root = Path(input_root)
    output_root = Path(output_root)
    
    print("===== STARTING DICOM TO NIFTI CONVERSION =====")
    for dirpath, _, filenames in os.walk(input_root):
        dirpath = Path(dirpath)

        # Detect if this folder contains DICOM files
        dicom_files = [f for f in dirpath.iterdir() if f.is_file() and is_dicom_file(f)]
        if len(dicom_files) == 0:
            continue

        # Build output file path
        rel = dirpath.relative_to(input_root)
        folder_name = rel.name  
        output_file = (output_root / rel.parent / f"{folder_name}.nii.gz")

        print(f"[INFO] Converting DICOM series: {dirpath}")
        convert_dicom_folder(dirpath, output_file)
        
    # Run the resampling process after all conversions are completed
    post_process_resampling(output_root)
    print("\n[INFO] All processes completed successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    convert_tree(args.input_dir, args.output_dir)