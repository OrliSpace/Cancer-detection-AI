
from google.colab import drive
import os
import subprocess
from tqdm import tqdm

# ---------------------------------------------------------
# 1) Mount Google Drive
# ---------------------------------------------------------
drive.mount('/content/drive')

# ---------------------------------------------------------
# 2) Path configuration
# ---------------------------------------------------------
INPUT_ROOT = "/content/drive/MyDrive/PatientsRaw"      # Source folders
OUTPUT_ROOT = "/content/drive/MyDrive/PatientsSorted"  # Output folders
SCRIPT_PATH = "/content/sort_sectra.py"                # Your original script

os.makedirs(OUTPUT_ROOT, exist_ok=True)

# ---------------------------------------------------------
# 3) Check if a folder contains a Sectra XML file
# ---------------------------------------------------------
def has_xml(folder):
    xml1 = os.path.join(folder, "content.xml")
    xml2 = os.path.join(folder, "SECTRA", "content.xml")
    return os.path.exists(xml1) or os.path.exists(xml2)

# ---------------------------------------------------------
# 4) Run the original script on a single folder
# ---------------------------------------------------------
def process_folder(src, dst):
    os.makedirs(dst, exist_ok=True)

    cmd = [
        "python3",
        SCRIPT_PATH,
        src,
        dst,
        "--debug"
    ]

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ---------------------------------------------------------
# 5) Collect all patient folders
# ---------------------------------------------------------
patient_folders = [
    f for f in os.listdir(INPUT_ROOT)
    if os.path.isdir(os.path.join(INPUT_ROOT, f))
]

print(f"Found {len(patient_folders)} folders in source directory")

# ---------------------------------------------------------
# 6) Choose: test mode (3 folders) or full run
# ---------------------------------------------------------
TEST_MODE = True   # ← Change to False for full processing

if TEST_MODE:
    folders_to_run = patient_folders[:3]
    print("🔍 TEST MODE ENABLED — processing only 3 folders")
else:
    folders_to_run = patient_folders
    print("🚀 FULL RUN MODE — processing all folders")

# ---------------------------------------------------------
# 7) Create master log file
# ---------------------------------------------------------
log_file_path = os.path.join(OUTPUT_ROOT, "master_log.txt")
log_file = open(log_file_path, "w", encoding="utf-8")

# ---------------------------------------------------------
# 8) Process folders with progress bar
# ---------------------------------------------------------
for folder in tqdm(folders_to_run, desc="Processing folders"):
    src = os.path.join(INPUT_ROOT, folder)
    dst = os.path.join(OUTPUT_ROOT, folder)

    log_file.write(f"\n=== Processing {folder} ===\n")

    # Skip folders already processed
    if os.path.exists(dst) and os.listdir(dst):
        log_file.write("Skipped (already processed)\n")
        continue

    # Skip folders without XML
    if not has_xml(src):
        log_file.write("❌ Missing XML — skipped\n")
        continue

    # Run the processing
    ok = process_folder(src, dst)

    if ok:
        log_file.write("✅ Success\n")
    else:
        log_file.write("❌ Failed\n")

log_file.close()

print("\n🎉 DONE! Master log saved at:")
print(log_file_path)