import os
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

        print(f"[SUCCESS] Saved: {output_file}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed converting {dicom_dir}: {e}")
        return False


def resample_ct(ct_path: Path, pet_path: Path, out_path: Path):
    print(f"[INFO] Resampling CT to PET space:\n  -> CT:  {ct_path.name}\n  -> PET: {pet_path.name}")
    try:
        ct = nib.load(str(ct_path))
        pet = nib.load(str(pet_path))

        ct_res = nilearn.image.resample_to_img(ct, pet, fill_value=-1024)
        nib.save(ct_res, str(out_path))

        print(f"[SUCCESS] Saved resampled CT: {out_path.name}")
        return True

    except Exception as e:
        print(f"[ERROR] Resampling failed for {ct_path.name}: {e}")
        return False


def post_process_resampling(output_root: Path):
    print("\n===== STARTING CT->PET RESAMPLING =====")

    folder_groups = {}
    for nii_file in output_root.rglob("*.nii.gz"):
        parent = nii_file.parent
        folder_groups.setdefault(parent, []).append(nii_file)

    # רשימת תיקיות שעברו resampling מלא
    fully_processed_folders = set()

    for folder, files in folder_groups.items():
        cts = [f for f in files if "CT" in f.name.upper() and "PT" not in f.name.upper() and "PET" not in f.name.upper()]
        pets = [f for f in files if "PT" in f.name.upper() or "PET" in f.name.upper()]

        if len(cts) == 1 and len(pets) == 1:
            ct_file = cts[0]
            pet_file = pets[0]

            temp_resampled_path = folder / ct_file.name.replace(".nii.gz", "_temp_resampled.nii.gz")

            success = resample_ct(ct_file, pet_file, temp_resampled_path)

            if success:
                try:
                    ct_file.unlink()
                    temp_resampled_path.rename(ct_file)
                    print(f"[INFO] Replaced original CT with resampled version successfully.")
                    fully_processed_folders.add(folder)
                except Exception as e:
                    print(f"[ERROR] Failed to clean up or rename files in {folder.name}: {e}")

        elif len(cts) > 0 and len(pets) > 0:
            print(f"[WARNING] Multiple CTs ({len(cts)}) or PETs ({len(pets)}) found in {folder.name}. Skipping.")

    # יצירת flag רק בתיקיות שעברו המרה מלאה + resampling
    for folder in fully_processed_folders:
        flag_file = folder / FLAG_NAME
        try:
            flag_file.write_text("done")
            print(f"[FLAG] Marked folder as fully processed: {folder}")
        except:
            pass

    print("\n===== RESAMPLING COMPLETED =====")


def convert_tree(input_root, output_root):
    input_root = Path(input_root)
    output_root = Path(output_root)

    print("===== STARTING DICOM TO NIFTI CONVERSION =====")

    for dirpath, _, filenames in os.walk(input_root):
        dirpath = Path(dirpath)

        dicom_files = [f for f in dirpath.iterdir() if f.is_file() and is_dicom_file(f)]
        if not dicom_files:
            continue

        rel = dirpath.relative_to(input_root)
        folder_name = rel.name
        output_folder = output_root / rel.parent
        output_file = output_folder / f"{folder_name}.nii.gz"
        flag_file = output_folder / FLAG_NAME

        # דילוג על תיקייה שכבר עברה המרה מלאה + resampling
        if flag_file.exists():
            print(f"[SKIP] Folder already fully processed: {output_folder}")
            continue

        print(f"[INFO] Converting DICOM series: {dirpath}")
        success = convert_dicom_folder(dirpath, output_file)

        if not success:
            print(f"[ERROR] Conversion failed, skipping resampling for this folder.")
            continue

    # אחרי כל ההמרות → מבצעים resampling ומסמנים תיקיות מוצלחות
    post_process_resampling(output_root)

    print("\n[INFO] All processes completed successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    convert_tree(args.input_dir, args.output_dir)
