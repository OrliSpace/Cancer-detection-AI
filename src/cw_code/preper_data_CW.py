from pathlib import Path
from datetime import datetime

from dicom_to_nifti import convert_tree as dicom_to_nifti
from cw_code.normalize_nifti import normalize_tree
from cw_code.nifti_to_mha import convert_folder_to_mha


def run_pipeline(dicom_root, output_root):
    """
    Full pipeline:
    1. Convert DICOM → NIfTI (includes CT→PET resampling)
    2. Normalize NIfTI (CT + PET)
    3. Create nnUNet-style output
    4. Convert nnUNet NIfTI → MHA
    """

    dicom_root = Path(dicom_root)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = output_root / f"pipeline_log_{timestamp}.txt"

    with open(log_path, "w", encoding="utf-8") as log:

        def write(msg):
            print(msg)
            log.write(msg + "\n")

        write("====================================")
        write("        STARTING FULL PIPELINE      ")
        write("====================================")
        write(f"Input DICOM root: {dicom_root}")
        write(f"Output root:      {output_root}")
        write(f"Timestamp:        {timestamp}")
        write("")

        # 1. Convert DICOM → NIfTI
        write("\n===== STEP 1: DICOM → NIFTI =====")
        nifti_root = output_root / "nifti_raw"
        dicom_to_nifti(dicom_root, nifti_root)

        # 2. Normalize NIfTI
        write("\n===== STEP 2: NORMALIZATION =====")
        normalized_root = output_root / "nifti_normalized"
        normalize_tree(nifti_root, normalized_root)

        # 3. Build nnUNet structure
        write("\n===== STEP 3: BUILDING NNUNET STRUCTURE =====")
        nnunet_root = output_root / "nnUNet_raw"
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

                ct_files[0].replace(ct_out)
                pet_files[0].replace(pet_out)

                write(f"[SUCCESS] Added patient: {patient}")

        # 4. Convert nnUNet NIfTI → MHA
        write("\n===== STEP 4: NIFTI → MHA =====")
        mha_root = output_root / "mha_output"
        convert_folder_to_mha(images_dir, mha_root)

        write("\n===== PIPELINE COMPLETED SUCCESSFULLY =====")
        write(f"Final nnUNet folder: {nnunet_root}")
        write(f"Final MHA folder:    {mha_root}")

    return mha_root


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Full PET/CT preprocessing pipeline")
    parser.add_argument("dicom_root", help="Folder containing raw DICOM data")
    parser.add_argument("output_root", help="Folder where processed NIfTI will be stored")

    args = parser.parse_args()

    run_pipeline(args.dicom_root, args.output_root)