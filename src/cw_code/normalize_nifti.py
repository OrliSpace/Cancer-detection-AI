import os
from pathlib import Path
import nibabel as nib
import numpy as np
import shutil


def normalize_nifti(src_path: Path, dst_path: Path, modality: str):
    img = nib.load(str(src_path))
    arr = img.get_fdata().astype(np.float32)

    mask = arr > -800 if modality.upper() == "CT" else arr > 0
    fg = arr[mask]

    if len(fg) < 100:
        fg = arr.flatten()

    p_low, p_high = np.percentile(fg, (0.5, 99.5))
    mean, std = fg.mean(), fg.std() + 1e-8

    arr = np.clip(arr, p_low, p_high)
    arr = (arr - mean) / std

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(arr, img.affine, img.header), str(dst_path))


def detect_modality(path: Path):
    """Very simple heuristic: CT or PET based on filename."""
    name = path.name.lower()
    if "ct" in name:
        return "CT"
    if "pet" in name or "pt" in name:
        return "PET"
    return "PET"  # default fallback


def normalize_tree(input_root, output_root):
    input_root = Path(input_root)
    output_root = Path(output_root)

    for dirpath, dirnames, filenames in os.walk(input_root):
        dirpath = Path(dirpath)

        for f in filenames:
            if not f.endswith(".nii") and not f.endswith(".nii.gz"):
                continue

            src = dirpath / f
            rel = src.relative_to(input_root)
            dst = output_root / rel

            modality = detect_modality(src)

            print(f"[INFO] Normalizing {modality}: {src}")
            normalize_nifti(src, dst, modality)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args()

    normalize_tree(args.input_dir, args.output_dir)