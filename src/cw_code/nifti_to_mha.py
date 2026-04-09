from pathlib import Path
import SimpleITK as sitk

def convert_nii_to_mha(nii_path: Path, mha_path: Path):
    img = sitk.ReadImage(str(nii_path))
    mha_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(mha_path), True)
    print(f"✔ {nii_path.name} -> {mha_path.name}")

def convert_folder_to_mha(input_dir: Path, out_dir: Path):
    """
    Convert all NIfTI files to MHA while preserving nnUNet structure 
    (keeps _0000 and _0001 suffixes and puts them in the same folder).
    """
    input_dir = Path(input_dir)
    out_dir = Path(out_dir)

    # מציאת כל קבצי ה-NIfTI בתיקייה
    nifti_files = list(input_dir.glob("*.nii.gz"))
    
    if not nifti_files:
        print("❌ No NIfTI files found in the input directory.")
        return out_dir

    print(f"🔍 Found {len(nifti_files)} files for MHA conversion.")

    for nii_file in nifti_files:
        # מחליפים את המחרוזת המלאה של הסיומת כדי למנוע .nii.mha
        clean_name = nii_file.name.replace(".nii.gz", ".mha")
        mha_file = out_dir / clean_name
        
        convert_nii_to_mha(nii_file, mha_file)

    print("✅ MHA conversion completed.")
    return out_dir