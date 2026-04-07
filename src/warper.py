import os
import subprocess
import argparse
import shutil
from tqdm import tqdm

def validate_paths(input_root, output_root, script_path):
    """Validates that all necessary paths exist before starting."""
    errors = []
    if not os.path.exists(input_root):
        errors.append(f"❌ ERROR: INPUT_ROOT does not exist: {input_root}")
    if not os.path.exists(script_path):
        errors.append(f"❌ ERROR: SCRIPT_PATH not found: {script_path}")

    if not os.path.exists(output_root):
        print(f"⚠️ OUTPUT_ROOT not found, creating it: {output_root}")
        os.makedirs(output_root, exist_ok=True)

    if errors:
        print("\n".join(errors))
        raise SystemExit("⛔ Stopping execution due to missing paths.")
    
    print("✅ All paths validated successfully.")

def process_folder(script_path, src, dst, debug=False):
    """Runs the sort_sectra.py script on a single folder using subprocess."""
    os.makedirs(dst, exist_ok=True)
    
    cmd = ["python3", script_path, src, dst]
    if debug:
        cmd.append("--debug")

    try:
        subprocess.run(cmd, check=True)
        
        # יצירת חותמת הצלחה רק אם התהליך עבר ללא שגיאות
        success_file = os.path.join(dst, ".success")
        with open(success_file, "w") as f:
            f.write("Processed successfully.")
            
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    parser = argparse.ArgumentParser(description="Batch runner for DICOM sorting")
    parser.add_argument("-i", "--input", required=True, help="Path to input root folder containing patient folders")
    parser.add_argument("-o", "--output", required=True, help="Path to destination root folder")
    parser.add_argument("-s", "--script", required=True, help="Path to sort_sectra.py script")
    parser.add_argument("-n", "--num_folders", type=int, default=0, help="Number of folders to process (0 for all)")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging in the underlying script")
    
    args = parser.parse_args()

    validate_paths(args.input, args.output, args.script)

    # Collect all patient folders
    patient_folders = [
        f for f in os.listdir(args.input)
        if os.path.isdir(os.path.join(args.input, f))
    ]
    
    print(f"Found {len(patient_folders)} folders in source directory")

    # Apply the limit if requested
    if args.num_folders > 0:
        patient_folders = patient_folders[:args.num_folders]
        print(f"🔍 TEST MODE ENABLED — processing only {args.num_folders} folders")
    else:
        print("🚀 FULL RUN MODE — processing all folders")

    log_file_path = os.path.join(args.output, "master_log.txt")
    
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        def log(msg):
            print(msg)
            log_file.write(msg + "\n")

        # Process folders with a progress bar
        for folder in tqdm(patient_folders, desc="Processing folders"):
            src = os.path.join(args.input, folder)
            dst = os.path.join(args.output, folder)
            success_marker = os.path.join(dst, ".success")

            log(f"\n=== Processing {folder} ===")

            # בדיקה אמינה - האם קיימת חותמת ההצלחה מהריצה הקודמת?
            if os.path.exists(success_marker):
                log("⏩ Skipped (already processed completely)")
                continue
            
            # אם התיקייה קיימת אבל אין חותמת הצלחה (הריצה נכשלה/נעצרה באמצע) - נמחק אותה ונתחיל מחדש
            if os.path.exists(dst):
                log("⚠️ Found partially processed data. Cleaning up before retry...")
                shutil.rmtree(dst)

            ok = process_folder(args.script, src, dst, args.debug)

            if ok:
                log("✅ Success")
            else:
                log("❌ Failed")

    print(f"\n🎉 DONE! Master log saved at: {log_file_path}")

if __name__ == "__main__":
    main()