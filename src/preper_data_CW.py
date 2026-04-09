import sys
import shutil
from pathlib import Path
from datetime import datetime

from dicom_to_nifti import convert_tree as dicom_to_nifti
from cw_code.normalize_nifti import normalize_tree
from cw_code.nifti_to_mha import convert_folder_to_mha

class DualLogger:
    """
    מחלקה שמנתבת את כל ההדפסות (stdout) גם למסך וגם לקובץ לוג.
    """
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()


def has_dicom_files(directory):
    """
    בודקת אם התיקייה מכילה קבצי DICOM.
    מחזירה True אם נמצאו קבצי .dcm, או אם אין בכלל קבצי .nii/.nii.gz בתיקייה.
    """
    directory = Path(directory)
    if any(directory.rglob("*.nii.gz")) or any(directory.rglob("*.nii")):
        return False
    return True


def run_pipeline(input_root, output_root):
    """
    Full pipeline:
    1. Convert DICOM → NIfTI (Conditional)
    2. Normalize NIfTI
    3. Create temp nnUNet-style output
    4. Convert nnUNet NIfTI → MHA
    5. Cleanup ALL temp folders (Normalized NIfTI & nnUNet)
    """

    input_root = Path(input_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_root / f"pipeline_log_{timestamp}.txt"

    original_stdout = sys.stdout
    logger = DualLogger(log_path)
    sys.stdout = logger

    # משתנה שיעזור לנו לדעת בסוף התהליך אם ביצענו המרה
    converted_from_dicom = False

    try:
        print("====================================")
        print("        STARTING FULL PIPELINE      ")
        print("====================================")
        print(f"Input root:       {input_root}")
        print(f"Output root:      {output_root}")
        print(f"Timestamp:        {timestamp}")
        print("")

        # 1. Convert DICOM → NIfTI (Conditional)
        if has_dicom_files(input_root):
            converted_from_dicom = True
            print("\n===== STEP 1: DICOM → NIFTI =====")
            print("Detected DICOM format. Starting conversion...")
            nifti_root = output_root / "nifti_raw"
            dicom_to_nifti(input_root, nifti_root)
        else:
            print("\n===== STEP 1: DICOM → NIFTI (SKIPPED) =====")
            print("Detected NIfTI format. Skipping DICOM conversion.")
            nifti_root = input_root

        # 2. Normalize NIfTI
        print("\n===== STEP 2: NORMALIZATION =====")
        normalized_root = output_root / "nifti_normalized"
        normalize_tree(nifti_root, normalized_root)

        # 3. Build temp nnUNet structure
        print("\n===== STEP 3: BUILDING TEMP NNUNET STRUCTURE =====")
        nnunet_root = output_root / "nnUNet_raw_temp"
        images_dir = nnunet_root / "imagesTr"
        images_dir.mkdir(parents=True, exist_ok=True)

        for study_dir in normalized_root.rglob("*"):
            if not study_dir.is_dir():
                continue

            ct_files = list(study_dir.glob("*CT*.nii.gz"))
            pet_files = list(study_dir.glob("*PT*.nii.gz")) + list(study_dir.glob("*PET*.nii.gz"))

            if len(ct_files) == 1 and len(pet_files) == 1:
                patient = study_dir.name.replace(" ", "_")

                ct_out = images_dir / f"{patient}_0000.nii.gz"
                pet_out = images_dir / f"{patient}_0001.nii.gz"

                shutil.copy(ct_files[0], ct_out)
                shutil.copy(pet_files[0], pet_out)

                print(f"[SUCCESS] Prepared patient for MHA conversion: {patient}")

        # 4. Convert nnUNet NIfTI → MHA
        print("\n===== STEP 4: NIFTI → MHA =====")
        mha_root = output_root / "mha_output"
        convert_folder_to_mha(images_dir, mha_root)

        # 5. Cleanup temp folders
        print("\n===== STEP 5: CLEANUP TEMP FILES =====")
        if nnunet_root.exists():
            shutil.rmtree(nnunet_root)
            print("Deleted temporary nnUNet folder.")
            
        if normalized_root.exists():
            shutil.rmtree(normalized_root)
            print("Deleted temporary normalized NIfTI folder.")

        print("\n===== PIPELINE COMPLETED SUCCESSFULLY =====")
        print("Final retained data:")
        if converted_from_dicom:
            print(f"- Raw NIfTI (from DICOM): {nifti_root}")
        print(f"- Final MHA output:       {mha_root}")

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        raise

    finally:
        sys.stdout = original_stdout
        logger.close()

    return mha_root


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Full PET/CT preprocessing pipeline (DICOM or NIfTI input)")
    parser.add_argument("input_root", help="Folder containing raw data (DICOM or NIfTI)")
    parser.add_argument("output_root", help="Folder where processed data will be stored")

    args = parser.parse_args()

    run_pipeline(args.input_root, args.output_root)