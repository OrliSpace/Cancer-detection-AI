import os
import shutil
import ants
import numpy as np
from pathlib import Path
from scipy.ndimage import center_of_mass
import matplotlib.pyplot as plt

# -------------------------
# Debug function
# -------------------------
def run_registration_debug_deform(fixed_wb_ct, warped_ob_ct, transforms, output_dir):
    print("\n===== DEFORMABLE REGISTRATION DEBUG (IMPROVED) =====")

    wb = fixed_wb_ct.numpy()
    ob = warped_ob_ct.numpy()

    wb_mask = wb > -400
    ob_mask = ob > -400

    if ob_mask.sum() < 1000:
        print("🚨 OB too small → failed registration")
        return 0

    # Center Distance
    wb_center = np.array(center_of_mass(wb_mask))
    ob_center = np.array(center_of_mass(ob_mask))

    center_dist = np.linalg.norm(wb_center - ob_center)
    print(f"[Center Distance] {center_dist:.2f}")

    # Slice Overlap
    overlap_slices = 0
    for i in range(wb.shape[0]):
        if np.logical_and(wb_mask[i], ob_mask[i]).sum() > 200:
            overlap_slices += 1

    print(f"[Overlapping slices] {overlap_slices}")

    # Jacobian
    jac_penalty = 0
    try:
        jac = ants.create_jacobian_determinant_image(
            fixed_wb_ct, transforms[0]
        ).numpy()

        jac_min, jac_max = np.min(jac), np.max(jac)
        print(f"[Jacobian] min={jac_min:.3f}, max={jac_max:.3f}")

        if jac_min <= 0:
            print("🚨 Folding detected!")
            jac_penalty = 40
        elif jac_max > 5:
            print("⚠️ Extreme stretching")
            jac_penalty = 20

    except Exception as e:
        print("[WARNING] Jacobian failed:", e)

    # Overlay visualization
    try:
        slice_idx = int(ob_center[0])
        plt.figure(figsize=(6, 6))
        plt.imshow(wb[slice_idx], cmap='gray', vmin=-1000, vmax=800)
        plt.imshow(ob[slice_idx], cmap='jet', alpha=0.3)
        plt.axis('off')
        plt.title("Deformable Overlay")

        path = output_dir / "debug_overlay_deform.png"
        plt.savefig(path, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Overlay saved: {path}")
    except Exception:
        pass

    # Score
    score = 100
    score -= min(center_dist * 0.5, 50)
    score += min(overlap_slices, 50) * 0.5
    score -= jac_penalty

    score = max(0, min(100, score))

    print(f"\n🎯 FINAL SCORE: {score:.2f}/100")
    print("===== DEBUG DONE =====\n")

    return score


# -------------------------
# Main registration function
# -------------------------
def register_patient_data_deform(fixed_img_path, moving_img_path, output_dir, debug=False):
    """
    מבצע רגיסטרציה דפורמבילית בין WB (Fixed) ל-OB (Moving).
    שומר את קבצי הטרנספורמציה (מתמטיקה) ולא רק את התמונה המעוותת.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Fixed CT (WB): {Path(fixed_img_path).name}")
    print(f"📂 Moving CT (OB): {Path(moving_img_path).name}")

    # 1. טעינת התמונות
    fixed_ct = ants.image_read(str(fixed_img_path))
    moving_ct = ants.image_read(str(moving_img_path))

    # 2. הרצת הרגיסטרציה
    print("🚀 Running deformable registration (SyNRA)...")
    reg = ants.registration(
        fixed=fixed_ct,
        moving=moving_ct,
        type_of_transform='SyNRA'
    )

    # 3. חילוץ ושמירת קבצי הטרנספורמציה (הכי חשוב בשביל השרת!)
    fwd_transforms = reg['fwdtransforms']
    
    for i, transform_path in enumerate(fwd_transforms):
        file_name = Path(transform_path).name
        
        if ".mat" in file_name:
            final_name = "0GenericAffine.mat"
        elif "Warp" in file_name:
            final_name = "1Warp.nii.gz"
        else:
            final_name = f"transform_{i}{Path(transform_path).suffix}"
            
        destination = output_dir / final_name
        shutil.copy(transform_path, destination)

    print("✅ Transforms saved successfully")

    # 4. שמירת ה-CT המעוות כדי שתוכלי לראות בעיניים שזה עבד
    warped_ct = ants.apply_transforms(
        fixed=fixed_ct,
        moving=moving_ct,
        transformlist=reg['fwdtransforms'],
        interpolator='linear'
    )
    
    ants.image_write(
        warped_ct,
        str(output_dir / "Warped_OB_CT_Deform.nii.gz")
    )
    print("✅ Warped CT saved")

    # 5. דיבאג במקרה הצורך
    score = None
    if debug:
        score = run_registration_debug_deform(
            fixed_ct,
            warped_ct,
            reg['fwdtransforms'],
            output_dir
        )

    return True, score