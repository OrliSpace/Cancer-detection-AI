"""
DICOM PET/CT Sorting and Filtering Tool
---------------------------------------
This script processes DICOM data using Sectra XML metadata.
Fixed version for SLURM / Sectra directory structures.
"""

import os
import xml.etree.ElementTree as ET
import re
import argparse
from datetime import datetime
import pydicom
from pydicom.uid import generate_uid

# ---------------------------------------------------------
# Logging - שמרתי על המבנה המקורי והמפורט שלך
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

def friendly_name(modality, description, number, match_tag=""):
    """Generate a cleaned, filesystem-friendly series name."""
    desc = (description or "UNKNOWN").upper()
    mod_upper = modality.upper()
    
    # ניקוי כפילויות של Modality בתוך התיאור
    if mod_upper in ["PT", "PET"]:
        desc = re.sub(r'\b(PT|PET)\b', '', desc)
    elif mod_upper == "CT":
        desc = re.sub(r'\bCT\b', '', desc)
        
    if match_tag:
        desc = re.sub(rf'\b{match_tag}\b', '', desc)

    desc = desc.replace(" ", "_")
    desc = re.sub(r'__+', '_', desc)
    desc = desc.strip("_")
    
    parts = [mod_upper]
    if match_tag:
        parts.append(match_tag)
    if desc:
        parts.append(desc)
    parts.append(f"S{number}")
    
    return "_".join(parts)

# ---------------------------------------------------------
# DICOM processing
# ---------------------------------------------------------
def process_and_save_dicom(src, dst, study_uid, series_uid, series_desc, series_number, modality):
    """Read a DICOM file, update key study and series tags, and save it."""
    try:
        ds = pydicom.dcmread(src)

        # עדכון מטא-דאטה לשמירה על עקביות ב-nnU-Net
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.SeriesDescription = series_desc
        ds.SeriesNumber = int(series_number)
        ds.ProtocolName = series_desc

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
    """Search for Sectra XML metadata files."""
    candidates = [
        os.path.join(patient_root, "content.xml"),
        os.path.join(patient_root, "CONTENT.XML"),
        os.path.join(patient_root, "SECTRA", "CONTENT.XML"),
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
    """Parse the Sectra XML file and return series metadata."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    series_map = {}
    series_list = root.findall(".//series")

    log_info(f"Found {len(series_list)} series in XML")

    for series in series_list:
        sid = series.get("id")
        modality = series.findtext("series_data/modality", "UNKNOWN")
        number = series.findtext("series_data/number", "0")
        description = series.findtext("series_data/description", "UNKNOWN")

        series_time = "UNKNOWN"
        first_image = series.find("image")
        if first_image is not None:
            dt_node = first_image.find("datetime")
            if dt_node is not None and dt_node.text:
                parts = dt_node.text.strip().split()
                series_time = parts[1] if len(parts) >= 2 else parts[0]

        files = []
        for img in series.findall(".//dicom_file/src"):
            # הפיכת נתיבי ווינדוס ללינוקס
            src = img.text.replace("..\\", "").replace("../", "").replace("\\", os.sep)
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
    """Filter PET for quality and match to the best diagnostic CT."""
    log_info("\n===== SMART PET ↔ CT MATCHING =====")

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
        except: return 9999

    # סינון וזיהוי PET הכי טוב (לפי כמות קבצים) לכל סוג
    ob_pets = [p for p in pet_series if any(x in p["description"].upper() for x in ["OB", "ONE BED"])]
    wb_pets = [p for p in pet_series if p not in ob_pets]

    best_ob_pet = max(ob_pets, key=lambda x: len(x["files"]), default=None)
    best_wb_pet = max(wb_pets, key=lambda x: len(x["files"]), default=None)

    selected_pets = []
    if best_ob_pet: selected_pets.append((best_ob_pet, "OB"))
    if best_wb_pet: selected_pets.append((best_wb_pet, "WB"))

    match_map = {}
    keep_sids = set()

    for pet, pet_type in selected_pets:
        pet_sid = pet["sid"]
        pet_time = get_minutes(pet["time"])
        best_ct = None
        min_diff = float('inf')

        for ct in ct_series:
            ct_desc = ct["description"].upper()
            if any(x in ct_desc for x in ["DOSE", "FUSION", "SCREEN", "LUNG"]): continue
            
            diff = abs(pet_time - get_minutes(ct["time"]))
            if diff < min_diff:
                min_diff = diff
                best_ct = ct

        if best_ct:
            match_map[pet_sid] = best_ct["sid"]
            keep_sids.add(pet_sid)
            keep_sids.add(best_ct["sid"])
            log_info(f"MATCH: {pet_type} PET S{pet['number']} -> CT S{best_ct['number']} ({min_diff} min)")
        else:
            log_warning(f"No CT match for {pet_type} PET")

    return keep_sids, match_map

def apply_pet_ct_references(series_map, output_root, study_uid, match_map):
    """Write PET DICOM files with references to their matched CT series."""
    log_info("\n===== APPLYING PET ↔ CT DICOM REFERENCES =====")

    study_folder = os.path.join(output_root, f"Study_{study_uid}")

    for pet_sid, ct_sid in match_map.items():
        if ct_sid is None: continue

        pet_data, ct_data = series_map[pet_sid], series_map[ct_sid]
        pet_tag = pet_data.get("match_tag", "")
        ct_tag = ct_data.get("match_tag", "")

        pet_fname = friendly_name(pet_data["modality"], pet_data["description"], pet_data["number"], pet_tag)
        ct_fname = friendly_name(ct_data["modality"], ct_data["description"], ct_data["number"], ct_tag)

        pet_dir = os.path.join(study_folder, pet_tag or "PET", pet_fname)
        ct_dir = os.path.join(study_folder, ct_tag or "CT", ct_fname)

        if os.path.exists(pet_dir) and os.path.exists(ct_dir):
            ct_files = [f for f in os.listdir(ct_dir) if os.path.isfile(os.path.join(ct_dir, f))]
            if not ct_files: continue
            ct_uid = pydicom.dcmread(os.path.join(ct_dir, ct_files[0])).SeriesInstanceUID
            
            for f in os.listdir(pet_dir):
                p = os.path.join(pet_dir, f)
                ds = pydicom.dcmread(p)
                ref = pydicom.dataset.Dataset()
                ref.SeriesInstanceUID = ct_uid
                ds.ReferencedSeriesSequence = [ref]
                ds.save_as(p)
            log_info(f"Linked: {pet_fname} -> {ct_fname}")

# ---------------------------------------------------------
# Main sorting
# ---------------------------------------------------------

def sort_dicom_from_xml(patient_root, output_root):
    log_info(f"Starting sort for patient folder: {patient_root}")

    xml_path = find_xml(patient_root)
    if xml_path is None: return

    # התיקון הקריטי למבנה ה-Sectra
    actual_patient_base = os.path.dirname(os.path.dirname(xml_path))
    log_info(f"Detected actual patient base: {actual_patient_base}")

    series_map = parse_xml(xml_path)

    # פריקת ה-Tuple (התיקון לשגיאת ה-items)
    keep_sids, match_map = match_pet_to_ct(series_map)
    
    # תיוג זוגות ה-OB/WB
    for pet_sid, ct_sid in match_map.items():
        p_desc = series_map[pet_sid]["description"].upper()
        p_type = "OB" if ("ONE BED" in p_desc or "OB" in p_desc) else "WB"
        series_map[pet_sid]["match_tag"] = p_type
        series_map[ct_sid]["match_tag"] = p_type

    study_uid = generate_uid()
    log_info(f"Generated Study UID: {study_uid}")

    total_processed = 0

    # עיבוד כל הסדרות (כולל אלו שלא ב-match_map - לפי בקשתך)
    for sid, data in series_map.items():
        modality = data["modality"].upper()
        match_tag = data.get("match_tag", "")
        fname = friendly_name(modality, data["description"], data["number"], match_tag)

        # קביעת תיקייה: OB/WB לזוגות, או לפי המודליטי לשאר
        mod_folder = match_tag if match_tag else modality
        out_dir = os.path.join(output_root, f"Study_{study_uid}", mod_folder, fname)
        os.makedirs(out_dir, exist_ok=True)

        series_uid = generate_uid()
        log_info(f"--> [SERIES] {fname} | Expected Slices: {len(data['files'])}")

        for rel_path in data["files"]:
            src = os.path.join(actual_patient_base, rel_path)
            dst = os.path.join(out_dir, os.path.basename(src))

            if os.path.exists(src):
                if process_and_save_dicom(src, dst, study_uid, series_uid, fname, data["number"], modality):
                    total_processed += 1
            else:
                # ניסיון חילוץ נוסף
                alt_src = os.path.join(actual_patient_base, "DICOM", os.path.basename(rel_path))
                if os.path.exists(alt_src):
                    process_and_save_dicom(alt_src, dst, study_uid, series_uid, fname, data["number"], modality)
                    total_processed += 1
                else:
                    log_warning(f"Missing: {src}")

    apply_pet_ct_references(series_map, output_root, study_uid, match_map)
    log_info(f"\n===== SUMMARY =====")
    log_info(f"Total Slices Processed: {total_processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_folder")
    parser.add_argument("output_folder")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    DEBUG_ENABLED = args.debug
    os.makedirs(args.output_folder, exist_ok=True)
    log_path = os.path.join(args.output_folder, f"sort_log_{datetime.now().strftime('%H%M%S')}.txt")
    LOG_FILE = open(log_path, "w", encoding="utf-8")

    sort_dicom_from_xml(args.input_folder, args.output_folder)
    LOG_FILE.close()
