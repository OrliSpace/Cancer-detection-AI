import os
from pathlib import Path
import dicom2nifti
import dicom2nifti.settings as settings


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


def convert_tree(input_root, output_root):
    """
    Recursively scan for DICOM series folders and convert each to a NIfTI file.
    The output file replaces the folder and keeps the same relative path.
    """
    input_root = Path(input_root)
    output_root = Path(output_root)

    for dirpath, _, filenames in os.walk(input_root):
        dirpath = Path(dirpath)

        # Detect if this folder contains DICOM files
        dicom_files = [f for f in dirpath.iterdir() if f.is_file() and is_dicom_file(f)]
        if len(dicom_files) == 0:
            continue

        # Build output file path (same relative path, but as a .nii.gz file)
        rel = dirpath.relative_to(input_root)
        folder_name = rel.name  # שם התיקייה המקורי, כולל נקודות
        output_file = (output_root / rel.parent / f"{folder_name}.nii.gz")

        print(f"[INFO] Converting DICOM series: {dirpath}")
        convert_dicom_folder(dirpath, output_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    convert_tree(args.input_dir, args.output_dir)