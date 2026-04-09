from pathlib import Path
import SimpleITK as sitk


def convert_nii_to_mha(nii_path: Path, mha_path: Path):
    img = sitk.ReadImage(str(nii_path))
    mha_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(mha_path), True)
    print(f"✔ {nii_path.name} -> {mha_path}")


def convert_folder_to_mha(input_dir: Path, out_dir: Path):
    """
    Convert all *_0000.nii.gz (CT) and *_0001.nii.gz (PET) to MHA.
    """
    input_dir = Path(input_dir)
    out_dir = Path(out_dir)

    ct_files = list(input_dir.glob("*_0000.nii.gz"))
    pet_files = list(input_dir.glob("*_0001.nii.gz"))

    ct_map = {f.stem.replace("_0000", ""): f for f in ct_files}
    pet_map = {f.stem.replace("_0001", ""): f for f in pet_files}

    common_ids = sorted(set(ct_map.keys()) & set(pet_map.keys()))

    print(f"🔍 Found {len(common_ids)} CT/PET pairs for MHA conversion.")

    for case_id in common_ids:
        ct_nii = ct_map[case_id]
        pet_nii = pet_map[case_id]

        ct_mha = out_dir / "images" / "ct" / f"{case_id}.mha"
        pet_mha = out_dir / "images" / "pet" / f"{case_id}.mha"

        convert_nii_to_mha(ct_nii, ct_mha)
        convert_nii_to_mha(pet_nii, pet_mha)

    print("✅ MHA conversion completed.")
    return out_dir