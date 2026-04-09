import sys
import shutil
from pathlib import Path
from datetime import datetime

from dicom_to_nifti import convert_tree as dicom_to_nifti
from cw_code.normalize_nifti import normalize_tree
from cw_code.nifti_to_mha import convert_folder_to_mha


class DualLogger:
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
    directory = Path(directory)
    if any(directory.rglob("*.nii.gz")) or any(directory.rglob("*.nii")):
        return False
    return True


def run_pipeline(input_root, output_root):
    input_root = Path(input_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_root / f"pipeline_log_{timestamp}.txt"

    original_stdout = sys.stdout
    logger = DualLogger(log_path)
    sys.stdout = logger

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

        # 3. Build temp nnUNet structure (SMART ID GENERATION)
        print("\n===== STEP 3: BUILDING TEMP NNUNET STRUCTURE =====")
        nnunet_root = output_root / "nnUNet_raw_temp"
        images_dir = nnunet_root / "imagesTr"
        images_dir.mkdir(parents=True, exist_ok=True)

        # נרוץ על כל תת-התיקיות בכל עומק שהוא כדי למצוא זוגות
        for scan_dir in normalized_root.rglob("*"):
            if not scan_dir.is_dir():
                continue

            ct_files = list(scan_dir.glob("*CT*.nii.gz"))
            pet_files = list(scan_dir.glob("*PT*.nii.gz")) + list(scan_dir.glob("*PET*.nii.gz"))

            # אם התיקייה הספציפית הזו מכילה גם CT וגם PET, מצאנו סריקה תקינה!
            if len(ct_files) >= 1 and len(pet_files) >= 1:
                
                # חילוץ מזהה המטופל וסוג הסריקה מהנתיב, תוך סינון התיקייה "Study..."
                try:
                    relative_parts = scan_dir.relative_to(normalized_root).parts
                except ValueError:
                    relative_parts = (scan_dir.name,)

                name_parts = [p.replace(" ", "_") for p in relative_parts if not p.startswith("Study")]
                
                if not name_parts:
                    final_id = scan_dir.name.replace(" ", "_")
                else:
                    # חיבור החלקים (למשל "3129058" ו-"OB") למזהה ייחודי אחד
                    final_id = "_".join(name_parts)

                ct_out = images_dir / f"{final_id}_0000.nii.gz"
                pet_out = images_dir / f"{final_id}_0001.nii.gz"

                shutil.copy(ct_files[0], ct_out)
                shutil.copy(pet_files[0], pet_out)

                print(f"[SUCCESS] Prepared nnUNet format for: {final_id}")

        # 4. Convert nnUNet NIfTI → MHA (Maintaining nnUNet structure)
        print("\n===== STEP 4: NIFTI → MHA =====")
        mha_root = output_root / "mha_output"
        mha_images_dir = mha_root / "imagesTr"
        mha_images_dir.mkdir(parents=True, exist_ok=True)
        
        convert_folder_to_mha(images_dir, mha_images_dir)

        # 5. Cleanup temp folders
        print("\n===== STEP 5: CLEANUP TEMP FILES =====")
        if nnunet_root.exists():
            shutil.rmtree(nnunet_root)
            print("Deleted temporary NIfTI nnUNet folder.")
            
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

    parser = argparse.ArgumentParser(description="Full PET/CT preprocessing pipeline for nnUNet (MHA output)")
    parser.add_argument("input_root", help="Folder containing raw data (DICOM or NIfTI)")
    parser.add_argument("output_root", help="Folder where processed data will be stored")

    args = parser.parse_args()

    run_pipeline(args.input_root, args.output_root)