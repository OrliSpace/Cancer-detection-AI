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

        pair_id = number  # או לוגיקה לפי XML
        pair_tag = f"PAIR_{pair_id}"
        ds.ImageComments = pair_tag

        ds.save_as(dst)

    except Exception as e:
        log_warning(f"Failed processing {src}: {e}")

# ---------------------------------------------------------
# XML
# ---------------------------------------------------------

def find_xml(patient_root):
    xml1 = os.path.join(patient_root, "content.xml")
    xml2 = os.path.join(patient_root, "SECTRA", "content.xml")

    if os.path.exists(xml1):
        log_info("Found content.xml in patient root")
        return xml1

    if os.path.exists(xml2):
        log_info("Found content.xml inside SECTRA folder")
        return xml2

    log_error("content.xml NOT FOUND")
    return None

def parse_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    series_map = {}
    series_list = root.findall(".//series")

    log_info(f"Found {len(series_list)} series in XML")

    for series in series_list:
        sid = series.get("id")
        modality = series.find("series_data/modality").text
        number = series.find("series_data/number").text
        description = series.find("series_data/description").text or "UNKNOWN"

        files = []
        for img in series.findall(".//dicom_file/src"):
            src = img.text.replace("..\\", "").replace("../", "")
            src = src.replace("\\", os.sep)
            files.append(src)

        series_map[sid] = {
            "modality": modality,
            "number": number,
            "description": description,
            "files": files
        }

    return series_map

# ---------------------------------------------------------
# PET ↔ CT matching (לוג בלבד)
# ---------------------------------------------------------

def match_pet_to_ct(series_map):
    log_info("\n===== PET ↔ CT MATCHING =====")

    ct_series = []
    pet_series = []

    for sid, data in series_map.items():
        modality = data["modality"].upper()
        desc = data["description"]
        number = data["number"]

        fname = friendly_name(modality, desc, number)

        if modality == "CT":
            ct_series.append((sid, desc, fname))
        elif modality in ["PT", "PET"]:
            pet_series.append((sid, desc, fname))

    for sid, desc, fname in pet_series:
        desc_u = desc.upper()

        if "MAC" in desc_u or "AC" in desc_u:
            match = [c for c in ct_series if "CTAC" in c[1].upper()]
            if match:
                log_info(f"{fname:<35} → {match[0][2]}")
                continue

        if "WB" in desc_u:
            match = [c for c in ct_series if "WB" in c[1].upper()]
            if match:
                log_info(f"{fname:<35} → {match[0][2]}")
                continue

        if "ONE BED" in desc_u:
            match = [c for c in ct_series if "CTAC" not in c[1].upper()]
            if match:
                log_info(f"{fname:<35} → {match[0][2]}")
                continue

        if ct_series:
            log_info(f"{fname:<35} → {ct_series[0][2]}")
        else:
            log_info(f"{fname:<35} → NO MATCH FOUND")

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

    # ✅ UID תקני
    study_uid = generate_uid()
    log_info(f"Generated Study UID: {study_uid}")

    for sid, data in series_map.items():
        modality = data["modality"].upper()
        number = data["number"]
        desc = data["description"]

        fname = friendly_name(modality, desc, number)

        if modality == "CT":
            mod_folder = "CT"
        elif modality in ["PT", "PET"]:
            mod_folder = "PET"
        else:
            mod_folder = "OTHER"

        out_dir = os.path.join(
            output_root,
            f"Study_{study_uid}",
            mod_folder,
            fname
        )
        os.makedirs(out_dir, exist_ok=True)

        # ✅ UID ייחודי לכל סדרה
        series_uid = generate_uid()

        for rel_path in data["files"]:
            src = os.path.join(patient_root, rel_path)
            dst = os.path.join(out_dir, os.path.basename(src))

            if os.path.exists(src):
                process_and_save_dicom(
                    src,
                    dst,
                    study_uid,
                    series_uid,
                    fname,
                    number,
                    modality
                )
            else:
                log_warning(f"Missing file: {src}")

    match_pet_to_ct(series_map)

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