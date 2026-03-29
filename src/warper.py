""" This code is possibale warper for running the soring from VM of google on the drive dirs"""


import os
import subprocess
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import argparse

# ---------------------------------------------------------
# 1) Normalize paths
# ---------------------------------------------------------
def normalize(p):
    return str(Path(p).expanduser().resolve())

# ---------------------------------------------------------
# 2) Check if folder contains Sectra XML
# ---------------------------------------------------------
def has_xml(folder):
    folder = normalize(folder)
    candidates = [
        "content.xml",
        "CONTENT.XML",
        "Content.xml",
        os.path.join("SECTRA", "content.xml"),
        os.path.join("SECTRA", "CONTENT.XML"),
        os.path.join("SECTRA", "Content.xml"),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(folder, c)):
            return True
    return False

# ---------------------------------------------------------
# 3) Run sort_sectra.py on a single folder
# ---------------------------------------------------------
def process_folder(script_path, src, dst, debug=True):
    os.makedirs(dst, exist_ok=True)

    cmd = [
        "python3",
        script_path,
        src,
        dst
    ]

    if debug:
        cmd.append("--debug")

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ---------------------------------------------------------
# 4) Main processing loop
# ---------------------------------------------------------
def main(input_root, output_root, script_path, test_mode=False):
    input_root = normalize(input_root)
    output_root = normalize(output_root)
    script_path = normalize(script_path)

    os.makedirs(output_root, exist_ok=True)

    # Collect patient folders
    patient_folders = [
        f for f in os.listdir(input_root)
        if os.path.isdir(os.path.join(input_root, f))
    ]

    print(f"[INFO] Found {len(patient_folders)} folders")

    if test_mode:
        folders_to_run = patient_folders[:3]
        print("[INFO] TEST MODE — running only 3 folders")
    else:
        folders_to_run = patient_folders
        print("[INFO] FULL RUN — running all folders")

    # Create master log
    log_path = os.path.join(
        output_root,
        f"master_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    log = open(log_path, "w", encoding="utf-8")

    # Process folders
    for folder in tqdm(folders_to_run, desc="Processing"):
        src = os.path.join(input_root, folder)
        dst = os.path.join(output_root, folder)

        log.write(f"\n=== Processing {folder} ===\n")

        # Skip if already processed
        if os.path.exists(dst) and os.listdir(dst):
            log.write("Skipped (already processed)\n")
            continue

        # Skip if missing XML
        if not has_xml(src):
            log.write("❌ Missing XML — skipped\n")
            continue

        # Run processing
        ok = process_folder(script_path, src, dst)

        if ok:
            log.write("✅ Success\n")
        else:
            log.write("❌ Failed\n")

    log.close()
    print(f"\n[INFO] DONE. Master log saved at:\n{log_path}")


# ---------------------------------------------------------
# 5) CLI interface (for VM or local)
# ---------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("input_root", help="Folder with raw patient folders")
    parser.add_argument("output_root", help="Folder to save sorted output")
    parser.add_argument("script_path", help="Path to sort_sectra.py")
    parser.add_argument("--test", action="store_true", help="Run only 3 folders")

    args = parser.parse_args()

    main(args.input_root, args.output_root, args.script_path, test_mode=args.test)