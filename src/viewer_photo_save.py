def save_diagnostic_report(mask_path, sample_id, reports_dir):
    """יצירת תמונה אבחנתית תוך שימוש בקבצי המקור המקוריים"""
    print(f"📸 Generating Report for: {sample_id}")
    
    # נתיב לקבצי המקור המקוריים ששמרנו ב-OB_NIFTI
    source_dir = os.path.join("/home/dsi/kadoshr5/dicom_project/OB_NIFTI_FIXED", sample_id)
    
    # בתיקיית המקור המקורית: 0000 הוא CT ו-0001 הוא PET
    # (זה לא משנה מה ה-AI קיבל, כאן אנחנו רק רוצים לצייר)
    # במקום השורות האלו, תכתוב:
    s_files = list(Path(source_dir).glob("*.nii.gz"))
    ct_p = next((str(f) for f in s_files if "CT" in f.name.upper() and "PT" not in f.name.upper()), None)
    pet_p = next((str(f) for f in s_files if "PT" in f.name.upper() or "PET" in f.name.upper()), None)
    
    if not ct_p or not pet_p: # שינוי קטן לבדיקה בטוחה
        print(f"⚠️ Skipping report for {sample_id}: Source files not found")
        return

    mask_img = nib.load(mask_path)
    mask_data = mask_img.get_fdata()
    
    voxel_vol = np.prod(mask_img.header.get_zooms())
    total_vol_cc = (np.sum(mask_data > 0) * voxel_vol) / 1000
    
    z_counts = np.sum(mask_data > 0, axis=(0, 1))
    best_z = np.argmax(z_counts) if np.max(z_counts) > 0 else mask_data.shape[2] // 2

    ct_arr = nib.load(ct_p).get_fdata()
    pet_arr = nib.load(pet_p).get_fdata()
    
    vmax_val = np.percentile(pet_arr[pet_arr > 0], 99.5) if np.any(pet_arr > 0) else 1

    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    axes[0].imshow(ct_arr[:,:,best_z].T, cmap='gray', origin='lower', vmin=-150, vmax=250)
    axes[0].set_title("CT Source")
    
    axes[1].imshow(pet_arr[:,:,best_z].T, cmap='hot', origin='lower', vmax=vmax_val)
    axes[1].set_title("PET Source")
    
    mask_slice = mask_data[:,:,best_z]
    mask_display = np.ma.masked_where(mask_slice == 0, mask_slice)
    axes[2].imshow(ct_arr[:,:,best_z].T, cmap='gray', origin='lower', alpha=0.8)
    axes[2].imshow(mask_display.T, cmap='spring', origin='lower')
    axes[2].set_title("AI Mask Overlay")
    
    axes[3].imshow(ct_arr[:,:,best_z].T, cmap='gray', origin='lower', vmin=-150, vmax=250)
    pet_masked = np.ma.masked_where(pet_arr[:,:,best_z] < (vmax_val*0.1), pet_arr[:,:,best_z])
    axes[3].imshow(pet_masked.T, cmap='hot', origin='lower', alpha=0.5, vmax=vmax_val)
    axes[3].set_title("Fusion Check")

    for ax in axes: ax.axis('off')
    plt.suptitle(f"ID: {sample_id} | Vol: {total_vol_cc:.2f}cc | Slice: {best_z}")
    
    plt.savefig(os.path.join(reports_dir, f"report_{sample_id}.png"), bbox_inches='tight', dpi=150)
    plt.close()
