import os
import ants
import numpy as np
from pathlib import Path
from tqdm import tqdm
from scipy.ndimage import center_of_mass
import matplotlib.pyplot as plt


def find_modality_file(folder_path: Path, keywords: list):
    for file in folder_path.glob("*.nii.gz"):
        if any(kw in file.name.upper() for kw in keywords):
            return file
    return None


def run_registration_debug_affine(fixed_wb_ct, warped_ob_ct, output_dir):
    print("\n===== AFFINE REGISTRATION DEBUG (IMPROVED) =====")

    wb = fixed_wb_ct.numpy()
    ob = warped_ob_ct.numpy()

    wb_mask = wb > -400
    ob_mask = ob > -400

    if ob_mask.sum() < 1000:
        print("🚨 OB too small → failed registration")
        return 0

    # -------------------------
    # Center Distance
    # -------------------------
    wb_center = np.array(center_of_mass(wb_mask))
    ob_center = np.array(center_of_mass(ob_mask))

    center_dist = np.linalg.norm(wb_center - ob_center)
    print(f"[Center Distance] {center_dist:.2f}")

    # -------------------------
    # Bounding Box Center
    # -------------------------
    coords = np.argwhere(ob_mask)
    ob_bbox_center = coords.mean(axis=0)

    print(f"[OB Center (bbox)] {ob_bbox_center}")

    # -------------------------
    # Slice Overlap
    # -------------------------
    overlap_slices = 0
    for i in range(wb.shape[0]):
        if np.logical_and(wb_mask[i], ob_mask[i]).sum() > 200:
            overlap_slices += 1

    print(f"[Overlapping slices] {overlap_slices}")

    # -------------------------
    # Volume Ratio
    # -------------------------
    volume_ratio = ob_mask.sum() / (wb_mask.sum() + 1e-8)
    print(f"[Volume Ratio OB/WB] {volume_ratio:.4f}")

    # -------------------------
    # Overlay
    # -------------------------
    try:
        slice_idx = int(ob_center[0])
        plt.figure(figsize=(6, 6))
        plt.imshow(wb[slice_idx], cmap='gray', vmin=-1000, vmax=800)
        plt.imshow(ob[slice_idx], cmap='jet', alpha=0.3)
        plt.axis('off')
        plt.title("Affine Overlay")

        path = output_dir / "debug_overlay_affine.png"
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Overlay saved: {path}")
    except Exception as e:
        print("[WARNING] Overlay failed:", e)

    # -------------------------
    # Score (geometry-based)
    # -------------------------
    score = 100
    score -= min(center_dist * 0.5, 50)
    score += min(overlap_slices, 50) * 0.5

    score = max(0, min(100, score))

    print(f"\n🎯 FINAL SCORE: {score:.2f}/100")
    print("===== DEBUG DONE =====\n")

    return score


def register_patient_data_affine(wb_dir, ob_dir, output_dir, debug=False):
    wb_ct = find_modality_file(wb_dir, ["CT"])
    ob_ct = find_modality_file(ob_dir, ["CT"])

    if not wb_ct or not ob_ct:
        return False, None

    output_dir.mkdir(parents=True, exist_ok=True)

    fixed = ants.image_read(str(wb_ct))
    moving = ants.image_read(str(ob_ct))

    reg = ants.registration(fixed=fixed, moving=moving, type_of_transform='Affine')

    warped = ants.apply_transforms(fixed=fixed, moving=moving, transformlist=reg['fwdtransforms'])

    ants.image_write(warped, str(output_dir / "Warped_OB_CT_Affine.nii.gz"))

    score = None
    if debug:
        score = run_registration_debug_affine(fixed, warped, output_dir)

    return True, score