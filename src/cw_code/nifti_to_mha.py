from pathlib import Path
import SimpleITK as sitk

def convert_nii_to_mha(nii_path: Path, mha_path: Path):
    img = sitk.ReadImage(str(nii_path))
    # יוצר את התיקיות בדרך אם הן לא קיימות (images/ct או images/pet)
    mha_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(mha_path), True)
    print(f"✔ {nii_path.name} -> {mha_path.parent.name}/{mha_path.name}")

def convert_folder_to_mha(input_dir: Path, out_dir: Path):
    """
    Convert NIfTI files to MHA and split them into separate folders 
    for CT and PET (expected by the Docker container).
    """
    input_dir = Path(input_dir)
    out_dir = Path(out_dir)

    ct_files = list(input_dir.glob("*_0000.nii.gz"))
    pet_files = list(input_dir.glob("*_0001.nii.gz"))

    if not ct_files and not pet_files:
        print("❌ No NIfTI files found in the input directory.")
        return out_dir

    print(f"🔍 Found {len(ct_files)} CT and {len(pet_files)} PET files for conversion.")

    # עיבוד קבצי ה-CT
    for ct_nii in ct_files:
        # מסירים את ה-_0000 ואת הסיומות, ונשארים עם השם הנקי.mha
        clean_name = ct_nii.name.replace("_0000.nii.gz", ".mha")
        ct_mha = out_dir / "images" / "ct" / clean_name
        convert_nii_to_mha(ct_nii, ct_mha)

    # עיבוד קבצי ה-PET
    for pet_nii in pet_files:
        # מסירים את ה-_0001 ואת הסיומות
        clean_name = pet_nii.name.replace("_0001.nii.gz", ".mha")
        pet_mha = out_dir / "images" / "pet" / clean_name
        convert_nii_to_mha(pet_nii, pet_mha)

    print("✅ MHA conversion to separate CT/PET folders completed.")
    return out_dir