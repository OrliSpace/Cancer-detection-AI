import argparse
import numpy as np
import SimpleITK as sitk
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from pathlib import Path
import sys

def interactive_viewer(input_dir, mask_path=None):
    base_path = Path(input_dir)
    patient_id = Path(input_dir).parents[1].name
  # שם המטופל מהתיקייה

    # 1. חיפוש קבצי CT ו-PET
    ct_patterns = ["*_0000.nii.gz", "case_0000.nii.gz", "CT_norm.nii.gz", "CT_*.nii.gz"]
    pet_patterns = ["*_0001.nii.gz", "case_0001.nii.gz", "PET_norm.nii.gz", "PT_*.nii.gz"]

    def find_file(patterns):
        for pattern in patterns:
            found = list(base_path.rglob(pattern))
            if found:
                return found[0]
        return None

    ct_file = find_file(ct_patterns)
    pet_file = find_file(pet_patterns)

    if not ct_file or not pet_file:
        print(f"❌ Error: Could not find CT or PET files in {input_dir}")
        sys.exit(1)

    ct_img = sitk.ReadImage(str(ct_file))
    pet_img = sitk.ReadImage(str(pet_file))
    ct_arr = sitk.GetArrayFromImage(ct_img)
    pet_arr = sitk.GetArrayFromImage(pet_img)

    # --- זיהוי נרמול ---
    is_normalized = np.max(ct_arr) < 50
    if is_normalized:
        print("ℹ️ Detected Normalized data (Z-score). Adjusting display scales...")
        ct_min, ct_max = -2, 5
        pet_vmax = 5
        pet_thresh = 0.5
    else:
        print("ℹ️ Detected Raw data (HU/SUV). Using standard scales...")
        ct_min, ct_max = -150, 250
        pet_vmax = np.max(pet_arr) * 0.5
        pet_thresh = np.max(pet_arr) * 0.1

    # --- מסכה ---
    has_mask = False
    mask_arr = None
    max_z = ct_arr.shape[0] - 1
    init_z = max_z // 2

    if mask_path:
        m_path = Path(mask_path)
        if m_path.exists():
            mask_img = sitk.ReadImage(str(m_path))
            mask_arr = sitk.GetArrayFromImage(mask_img)
            slice_counts = np.sum(mask_arr, axis=(1, 2))
            if np.any(slice_counts > 0):
                init_z = int(np.argmax(slice_counts))
                print(f"🎯 Mask detected! Jumping to slice {init_z}")
            has_mask = True

    # --- תצוגה ---
    num_panels = 4 if has_mask else 3
    fig, axes = plt.subplots(1, num_panels, figsize=(5 * num_panels, 5))
    plt.subplots_adjust(bottom=0.25)

    # --- CT ---
    im_ct = axes[0].imshow(
        ct_arr[init_z],
        cmap='gray',
        vmin=ct_min,
        vmax=ct_max
    )
    axes[0].set_title("CT Source")

    # --- PET ---
    im_pet = axes[1].imshow(
        pet_arr[init_z],
        cmap='hot',
        vmin=0,
        vmax=pet_vmax
    )
    axes[1].set_title("PET Source")

    # --- MASK ---
    if has_mask:
        mask_slice = mask_arr[init_z]
        mask_display = np.ma.masked_where(mask_slice == 0, mask_slice)

        im_mask = axes[2].imshow(
            ct_arr[init_z],
            cmap='gray',
            alpha=0.8,
            vmin=ct_min,
            vmax=ct_max
        )
        im_mask_overlay = axes[2].imshow(
            mask_display,
            cmap='spring',
            alpha=0.7
        )
        axes[2].set_title("AI Mask Overlay")
        fused_ax = axes[3]
    else:
        fused_ax = axes[2]

    # --- FUSION ---
    im_fused_ct = fused_ax.imshow(
        ct_arr[init_z],
        cmap='gray',
        vmin=ct_min,
        vmax=ct_max
    )

    pet_masked = np.ma.masked_where(pet_arr[init_z] < pet_thresh, pet_arr[init_z])
    im_fused_pet = fused_ax.imshow(
        pet_masked,
        cmap='hot',
        alpha=0.5,
        vmin=0,
        vmax=pet_vmax
    )

    if has_mask:
        mask_display = np.ma.masked_where(mask_arr[init_z] == 0, mask_arr[init_z])
        im_fused_mask = fused_ax.imshow(
            mask_display,
            cmap='spring',
            alpha=0.4
        )

    fused_ax.set_title("Fusion Check")

    for ax in axes:
        ax.axis('off')

    # --- סליידר ---
    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03])
    z_slider = Slider(ax_slider, 'Slice', 0, max_z, valinit=init_z, valstep=1)

    def update(val):
        z = int(z_slider.val)

        # CT
        im_ct.set_data(ct_arr[z])

        # PET
        im_pet.set_data(pet_arr[z])

        # Fused CT
        im_fused_ct.set_data(ct_arr[z])

        # Fused PET
        pet_m = np.ma.masked_where(pet_arr[z] < pet_thresh, pet_arr[z])
        im_fused_pet.set_data(pet_m)

        if has_mask:
            mask_slice = mask_arr[z]
            mask_display = np.ma.masked_where(mask_slice == 0, mask_slice)

            im_mask.set_data(ct_arr[z])
            im_mask_overlay.set_data(mask_display)
            im_fused_mask.set_data(mask_display)

        plt.suptitle(f"Patient: {patient_id} | {status} | Slice {z}", fontsize=12)
        fig.canvas.draw_idle()

    z_slider.on_changed(update)

    status = "Normalized" if is_normalized else "Raw HU/SUV"
    plt.suptitle(f"Patient: {patient_id} | {status} | Slice {init_z}", fontsize=12)

    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_dir", required=True)
    parser.add_argument("-m", "--mask", required=False, default=None)
    args = parser.parse_args()
    interactive_viewer(args.input_dir, args.mask)
