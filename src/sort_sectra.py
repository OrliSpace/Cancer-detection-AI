import os
import xml.etree.ElementTree as ET
import re
import argparse
from datetime import datetime
import pydicom
from pydicom.uid import generate_uid

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

LOG_FILE = None
DEBUG_ENABLED = False

def log_debug(msg):
    if DEBUG_ENABLED and LOG_FILE:
        LOG_FILE.write(f"[DEBUG] {msg}\n")

def log_info(msg):
    print(f"[INFO] {msg}")
    if LOG_FILE:
        LOG_FILE.write(f"[INFO] {msg}\n")

def log_error(msg):
    print(f"[ERROR] {msg}")
    if LOG_FILE:
        LOG_FILE.write(f"[ERROR] {msg}\n")

def log_warning(msg):
    print(f"[WARNING] {msg}")
    if LOG_FILE:
        LOG_FILE.write(f"[WARNING] {msg}\n")

# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def friendly_name(modality, description, number):
    desc = (description or "UNKNOWN").upper()
    desc = desc.replace("PET", "")
    desc = desc.replace("CT ", "CT_")
    desc = desc.replace(" ", "_")
    desc = re.sub(r'__+', '_', desc)
    desc = desc.strip("_")
    return f"{modality.upper()}_{desc}_S{number}"

# ---------------------------------------------------------
# DICOM processing
# ---------------------------------------------------------
def process_and_save_dicom(src, dst, study_uid, series_uid, series_desc, series_number, modality):
    try:
        ds = pydicom.dcmread(src)

        # --- תיקון metadata ---
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.SeriesDescription = series_desc
        ds.SeriesNumber = int(series_number)
        ds.ProtocolName = series_desc

        # pairing tag
        pair_tag = f"{modality}_PAIR_{series_number}"
        ds.ImageComments = pair_tag

        ds.save_as(dst)
        return True  

    except Exception as e:
        log_warning(f"Failed processing {src}: {e}")
        return False 

# ---------------------------------------------------------
# XML Parsing
# ---------------------------------------------------------
def find_xml(patient_root):
    candidates = [
        os.path.join(patient_root, "content.xml"),
        os.path.join(patient_root, "CONTENT.XML"),
        os.path.join(patient_root, "Content.xml"),
        os.path.join(patient_root, "SECTRA", "content.xml"),
        os.path.join(patient_root, "SECTRA", "CONTENT.XML"),
        os.path.join(patient_root, "SECTRA", "Content.xml"),
    ]

    for path in candidates:
        if os.path.exists(path):
            log_info(f"Found XML: {path}")
            return path

    for root, dirs, files in os.walk(patient_root):
        for f in files:
            if f.lower() == "content.xml":
                full = os.path.join(root, f)
                log_info(f"Found XML via recursive search: {full}")
                return full

    log_error("CONTENT.xml NOT FOUND")
    return None

def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    series_map = {}
    series_list = root.findall(".//series")

    log_info(f"Found {len(series_list)} series in XML")

    for series in series_list:
        sid = series.get("id")
        
        modality_node = series.find("series_data/modality")
        modality = modality_node.text if modality_node is not None else "UNKNOWN"
        
        number_node = series.find("series_data/number")
        number = number_node.text if number_node is not None else "0"
        
        desc_node = series.find("series_data/description")
        description = desc_node.text if desc_node is not None else "UNKNOWN"

        # חילוץ הזמן מהתמונה הראשונה בסדרה
        series_time = "UNKNOWN"
        first_image = series.find("image")
        if first_image is not None:
            datetime_node = first_image.find("datetime")
            utc_time_node = first_image.find("utc_time")
            
            if datetime_node is not None and datetime_node.text:
                parts = datetime_node.text.strip().split()
                if len(parts) >= 2:
                    series_time = parts[1]
                else:
                    series_time = datetime_node.text.strip()
            elif utc_time_node is not None and utc_time_node.text:
                series_time = utc_time_node.text.strip()

        files = []
        for img in series.findall(".//dicom_file/src"):
            src = img.text.replace("..\\", "").replace("../", "")
            src = src.replace("\\", os.sep)
            files.append(src)

        series_map[sid] = {
            "modality": modality,
            "number": number,
            "description": description,
            "time": series_time,
            "files": files
        }

    return series_map

# ---------------------------------------------------------
# PET ↔ CT matching
# ---------------------------------------------------------
def match_pet_to_ct(series_map):
    log_info("\n===== SMART PET ↔ CT MATCHING (Anatomy & Time) =====")

    ct_series = []
    pet_series = []

    for sid, data in series_map.items():
        if data["modality"].upper() == "CT":
            ct_series.append(data | {"sid": sid})
        elif data["modality"].upper() in ["PT", "PET"]:
            pet_series.append(data | {"sid": sid})

    def get_minutes(time_str):
        try:
            h, m, s = map(int, time_str.split(':'))
            return h * 60 + m
        except: 
            return 9999

    match_map = {}

    for pet in pet_series:
        pet_sid = pet["sid"]
        pet_desc = pet["description"].upper()
        pet_time = get_minutes(pet["time"])
        pet_fname = friendly_name(pet["modality"], pet["description"], pet["number"])

        pet_type = "OB" if ("ONE BED" in pet_desc or "OB" in pet_desc) else "WB"

        best_ct = None
        min_diff = float('inf')

        for ct in ct_series:
            ct_desc = ct["description"].upper()
            
            # סינון סדרות לא רלוונטיות
            if any(x in ct_desc for x in ["DOSE", "FUSION", "SCREEN", "LUNG"]):
                continue
                
            ct_time = get_minutes(ct["time"])
            time_diff = abs(pet_time - ct_time)

            # מניעת שידוך של WB ל-OB ע"י הגבלת הפרש הזמנים
            if pet_type == "OB" and time_diff > 30:
                continue
            if pet_type == "WB" and time_diff > 45: 
                continue

            if time_diff < min_diff:
                min_diff = time_diff
                best_ct = ct

        if best_ct:
            match_map[pet_sid] = best_ct["sid"]
            ct_fname = friendly_name(best_ct["modality"], best_ct["description"], best_ct["number"])
            log_info(f"{pet_fname:<35} → {ct_fname} (Diff: {min_diff} min)")
        else:
            match_map[pet_sid] = None
            log_info(f"{pet_fname:<35} → NO MATCH FOUND")

    return match_map

def apply_pet_ct_references(series_map, output_root, study_uid, match_map):
    log_info("\n===== APPLYING PET ↔ CT DICOM REFERENCES =====")

    study_folder = os.path.join(output_root, f"Study_{study_uid}")

    for pet_sid, ct_sid in match_map.items():
        if ct_sid is None:
            continue

        pet_data = series_map[pet_sid]
        ct_data = series_map[ct_sid]

        # שימוש ב-Modality המקורי מתוך ה-XML כדי למנוע תיקיות חסרות!
        pet_fname = friendly_name(pet_data["modality"], pet_data["description"], pet_data["number"])
        ct_fname = friendly_name(ct_data["modality"], ct_data["description"], ct_data["number"])

        pet_dir = os.path.join(study_folder, "PET", pet_fname)
        ct_dir = os.path.join(study_folder, "CT", ct_fname)

        if not os.path.exists(pet_dir) or not os.path.exists(ct_dir):
            log_warning(f"Missing PET or CT folder for mapping {pet_fname}")
            continue

        ct_files = [f for f in os.listdir(ct_dir) if os.path.isfile(os.path.join(ct_dir, f))]
        if not ct_files:
            log_warning(f"No CT DICOM files found in {ct_dir}")
            continue

        ct_first = pydicom.dcmread(os.path.join(ct_dir, ct_files[0]))
        ct_series_uid = ct_first.SeriesInstanceUID

        pet_files = [f for f in os.listdir(pet_dir) if os.path.isfile(os.path.join(pet_dir, f))]

        for f in pet_files:
            path = os.path.join(pet_dir, f)
            ds = pydicom.dcmread(path)

            ref_series = pydicom.dataset.Dataset()
            ref_series.SeriesInstanceUID = ct_series_uid

            ds.ReferencedSeriesSequence = [ref_series]
            ds.save_as(path)

        log_info(f"Added CT Series reference to PET series: {pet_fname} → {ct_fname}")

# ---------------------------------------------------------
# Main sorting
# ---------------------------------------------------------

def sort_dicom_from_xml(patient_root, output_root):
    log_info(f"Starting sort for patient folder: {patient_root}")

    xml_path = find_xml(patient_root)
    if xml_path is None:
        return

    dicom_root = os.path.join(patient_root, "DICOM")
    if not os.path.exists(dicom_root):
        log_error("DICOM folder NOT FOUND")
        return

    series_map = parse_xml(xml_path)

    study_uid = generate_uid()
    log_info(f"Generated Study UID: {study_uid}")

    total_expected_series = len(series_map)
    total_expected_slices = 0
    total_processed_slices = 0

    for sid, data in series_map.items():
        modality = data["modality"].upper()
        number = data["number"]
        desc = data["description"]
        series_time = data.get("time", "UNKNOWN")
        
        expected_slices = len(data["files"])
        total_expected_slices += expected_slices

        fname = friendly_name(modality, desc, number)

        if modality == "CT":
            mod_folder = "CT"
        elif modality in ["PT", "PET"]:
            mod_folder = "PET"
        else:
            mod_folder = "OTHER"

        out_dir = os.path.join(output_root, f"Study_{study_uid}", mod_folder, fname)
        os.makedirs(out_dir, exist_ok=True)

        series_uid = generate_uid()

        log_info(f"--> [SERIES] {fname} | Modality: {modality} | Time: {series_time} | Expected Slices: {expected_slices}")

        processed_slices_in_series = 0
        for rel_path in data["files"]:
            src = os.path.join(patient_root, rel_path)
            dst = os.path.join(out_dir, os.path.basename(src))

            if os.path.exists(src):
                success = process_and_save_dicom(
                    src, dst, study_uid, series_uid, fname, number, modality
                )
                if success:
                    processed_slices_in_series += 1
                    total_processed_slices += 1
            else:
                log_warning(f"Missing file: {src}")
        
        if processed_slices_in_series != expected_slices:
            log_warning(f"    [!] Mismatch in {fname}: Processed {processed_slices_in_series}/{expected_slices} slices.")
        else:
            log_info(f"    [V] Completed {fname}: All {expected_slices} slices processed.")

    match_map = match_pet_to_ct(series_map)
    apply_pet_ct_references(series_map, output_root, study_uid, match_map)

    log_info("\n===== PROCESSING SUMMARY =====")
    log_info(f"Total Series Processed : {total_expected_series}")
    log_info(f"Total Slices Expected  : {total_expected_slices}")
    log_info(f"Total Slices Processed : {total_processed_slices}")
    
    if total_expected_slices > 0 and total_expected_slices == total_processed_slices:
        log_info("[SUCCESS] ALL data was perfectly converted and saved! No missing slices.")
    else:
        log_error("[WARNING] There is a mismatch between expected files and processed files. Check logs for missing files.")

    log_info("DONE! All series sorted successfully.")
    log_info(f"Output folder: {output_root}")

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort DICOM using Sectra XML")
    parser.add_argument("input_folder")
    parser.add_argument("output_folder")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    DEBUG_ENABLED = args.debug

    os.makedirs(args.output_folder, exist_ok=True)
    log_path = os.path.join(
        args.output_folder,
        f"sort_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    LOG_FILE = open(log_path, "w", encoding="utf-8")

    log_info(f"Debug mode: {DEBUG_ENABLED}")
    log_info(f"Log file: {log_path}")

    sort_dicom_from_xml(args.input_folder, args.output_folder)

    LOG_FILE.close()