import os
import ants
import numpy as np
from pathlib import Path
from tqdm import tqdm
from scipy.ndimage import center_of_mass
import matplotlib.pyplot as plt


# -----------------------------
# Utils
# -----------------------------
def find_modality_file(folder_path: Path, keywords: list):
    for file in folder_path.glob("*.nii.gz"):
        filename_upper = file.name.upper()
        if any(kw in filename_upper for kw in keywords):
            return file
    return None


# -----------------------------
# Debug + Scoring
# -----------------------------
def run_registration_debug(fixed_wb_ct, moving_ob_ct, warped_ob_ct, transforms, output_dir):
    print("\n===== REGISTRATION DEBUG (INTENSITY-BASED) =====")

    wb = fixed_wb_ct.numpy()
    ob_after = warped_ob_ct.numpy()

    # ---------------------------------
    # 1. ROI Definition (Intensity Only)
    # Using -500 HU to ensure lungs are included in the tissue mask
    # ---------------------------------
    print("[INFO] Using intensity-based ROI (HU > -500)")
    wb_mask = wb > -500
    ob_mask = ob_after > -500

    if ob_mask.sum() < 1000:
        print("🚨 WARNING: OB ROI too small → likely empty image or severe registration failure")
        return 0

    # ---------------------------------
    # 2. Correlation (ROI ONLY)
    # ---------------------------------
    wb_roi = wb[ob_mask]
    ob_roi = ob_after[ob_mask]

    def corr(a, b):
        return np.corrcoef(a.flatten(), b.flatten())[0, 1]

    try:
        corr_roi = corr(wb_roi, ob_roi)
    except Exception:
        corr_roi = 0

    print(f"\n[Correlation - ROI] {corr_roi:.4f}")

    # ---------------------------------
    # 3. Coverage (Replaces traditional Dice for Partial vs Whole Body)
    # Measures what percentage of the OB scan is inside the WB body bounds
    # ---------------------------------
    intersection = np.logical_and(wb_mask, ob_mask).sum()
    coverage = intersection / (ob_mask.sum() + 1e-8)

    print(f"\n[Coverage - OB inside WB] {coverage:.4f}")

    # ---------------------------------
    # 4. Jacobian (Detecting folding/tearing)
    # ---------------------------------
    jac_penalty = 0
    try:
        jac = ants.create_jacobian_determinant_image(
            fixed_wb_ct, transforms[0]
        ).numpy()

        jac_min, jac_max = np.min(jac), np.max(jac)

        print(f"\n[Jacobian] min={jac_min:.3f}, max={jac_max:.3f}")

        if jac_min <= 0:
            jac_penalty = 1.0  # Non-physical folding occurred
        elif jac_max > 5:
            jac_penalty = 0.5  # Extreme unnatural stretching

    except Exception as e:
        print("[WARNING] Jacobian failed:", e)

    # ---------------------------------
    # 5. Overlay Display
    # ---------------------------------
    try:
        # Find the center of mass of the OB to select a relevant slice
        # This ensures the debug image actually shows the overlapping region
        ob_com = center_of_mass(ob_mask)
        slice_idx = int(ob_com[0]) 

        plt.figure(figsize=(6, 6))
        plt.imshow(wb[slice_idx], cmap='gray', vmin=-1000, vmax=800)
        plt.imshow(ob_after[slice_idx], cmap='jet', alpha=0.3, vmin=-1000, vmax=800)
        plt.title(f"Overlay at Slice {slice_idx}")
        plt.axis('off')

        overlay_path = output_dir / "debug_overlay.png"
        plt.savefig(overlay_path, bbox_inches='tight')
        plt.close()

        print(f"[INFO] Overlay saved: {overlay_path}")

    except Exception as e:
        print("[WARNING] Overlay failed:", e)

    # ---------------------------------
    # 6. FINAL SCORE
    # ---------------------------------
    score = (
        70 * max(0, corr_roi) +  # 70% weight to correlation (most important for CT)
        30 * coverage +          # 30% weight to making sure OB is fully inside WB
        -30 * jac_penalty        # Heavy penalty for unphysical deformations
    )

    score = max(0, min(100, score))

    print(f"\n🎯 FINAL SCORE: {score:.2f}/100")

    if score > 75:
        print("✅ GOOD registration")
    elif score > 50:
        print("⚠️ MEDIUM registration")
    else:
        print("🚨 BAD registration")

    print("===== DEBUG DONE =====\n")

    return score
# -----------------------------
# Core Registration
# -----------------------------
def register_patient_data(wb_dir: Path, ob_dir: Path, output_dir: Path, debug=False):
    wb_ct_path = find_modality_file(wb_dir, ["CT"])
    ob_ct_path = find_modality_file(ob_dir, ["CT"])
    ob_pet_path = find_modality_file(ob_dir, ["PT", "PET"])
    ob_mask_path = find_modality_file(ob_dir, ["MASK", "LABEL", "SEG"])

    if not wb_ct_path or not ob_ct_path or not ob_pet_path:
        print(f"\n[ERROR] Missing CT/PET in {wb_dir.name}")
        return False, None

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        fixed_wb_ct = ants.image_read(str(wb_ct_path))
        moving_ob_ct = ants.image_read(str(ob_ct_path))
        moving_ob_pet = ants.image_read(str(ob_pet_path))

        registration = ants.registration(
            fixed=fixed_wb_ct,
            moving=moving_ob_ct,
            type_of_transform='SyNRA',
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

        if ob_mask_path:
            moving_ob_mask = ants.image_read(str(ob_mask_path))
            warped_ob_mask = ants.apply_transforms(
                fixed=fixed_wb_ct,
                moving=moving_ob_mask,
                transformlist=transforms,
                interpolator='nearestNeighbor'
            )
            ants.image_write(warped_ob_mask, str(output_dir / "Warped_OB_Mask.nii.gz"))

        score = None
        if debug:
            score = run_registration_debug(
                fixed_wb_ct,
                moving_ob_ct,
                warped_ob_ct,
                transforms,
                output_dir
            )

        return True, score

    except Exception as e:
        print(f"\n[ERROR] Failed for {wb_dir}: {e}")
        return False, None


# -----------------------------
# Dataset Loop
# -----------------------------
def process_entire_dataset(input_root: Path, output_root: Path, debug=False):
    print("===== STARTING DATASET REGISTRATION =====")

    patient_dirs = [d for d in input_root.iterdir() if d.is_dir()]
    scores = {}

    for patient_dir in tqdm(patient_dirs, desc="Processing Patients"):
        patient_id = patient_dir.name

        wb_dirs = [d for d in patient_dir.rglob("*") if d.is_dir() and "WB" in d.name.upper()]
        ob_dirs = [d for d in patient_dir.rglob("*") if d.is_dir() and "OB" in d.name.upper()]

        if wb_dirs and ob_dirs:
            success, score = register_patient_data(
                wb_dirs[0],
                ob_dirs[0],
                output_root / patient_id,
                debug=debug
            )

            if score is not None:
                scores[patient_id] = score
        else:
            tqdm.write(f"[WARNING] Missing OB/WB for {patient_id}")

    # ---- Summary
    if debug and scores:
        print("\n===== DATASET SUMMARY =====")
        for pid, s in scores.items():
            print(f"{pid}: {s:.2f}")

        avg = np.mean(list(scores.values()))
        print(f"\nAverage Score: {avg:.2f}")

    print("\n===== ALL DONE! =====")


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CT-PET Registration Pipeline")

    parser.add_argument("-i", "--input_dir", required=True)
    parser.add_argument("-o", "--output_dir", required=True)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    process_entire_dataset(
        Path(args.input_dir),
        Path(args.output_dir),
        debug=args.debug
    )