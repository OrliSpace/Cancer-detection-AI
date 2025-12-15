import pathlib as plb
import os
import sys
import shutil
import numpy as np
import pydicom
import nibabel as nib
import SimpleITK as sitk
import nilearn.image
from tqdm import tqdm
from pathlib import Path

# --- Helper Functions for SUV Calculation ---

def conv_time(time_str):
    """Converts DICOM time string (HHMMSS.frac) to seconds."""
    try:
        return (float(time_str[:2]) * 3600 + float(time_str[2:4]) * 60 + float(time_str[4:]))
    except Exception:
        return 0.0

def calculate_suv_factor(dcm_path):
    """Reads a PET DICOM file and calculates the SUV conversion factor."""
    try:
        ds = pydicom.dcmread(str(dcm_path))
        
        # Check if necessary tags exist
        if not hasattr(ds, 'RadiopharmaceuticalInformationSequence'):
            print("⚠️ Warning: No Radiopharmaceutical info found. SUV factor = 1.0")
            return 1.0
            
        seq = ds.RadiopharmaceuticalInformationSequence[0]
        
        total_dose = float(seq.RadionuclideTotalDose)
        half_life = float(seq.RadionuclideHalfLife)
        
        # Handle time formats
        start_time_str = str(seq.RadiopharmaceuticalStartTime)
        acq_time_str = str(ds.AcquisitionTime)
        
        if not start_time_str or not acq_time_str:
            return 1.0

        start_time = conv_time(start_time_str)
        acq_time = conv_time(acq_time_str)
        
        # Patient weight is crucial
        if hasattr(ds, 'PatientWeight'):
            weight = float(ds.PatientWeight)
        else:
            print("⚠️ Warning: Patient Weight missing. SUV factor = 1.0")
            return 1.0

        # Decay correction
        time_diff = acq_time - start_time
        act_dose = total_dose * 0.5 ** (time_diff / half_life)
        
        suv_factor = 1000 * weight / act_dose
        return suv_factor
    except Exception as e:
        print(f"⚠️ Error calculating SUV factor: {e}. Defaulting to 1.0")
        return 1.0

def convert_pet_to_suv(nifti_path, suv_factor, output_path):
    """Loads a raw PET NIfTI, multiplies by SUV factor, and saves."""
    try:
        pet = nib.load(str(nifti_path))
        affine = pet.affine
        pet_data = pet.get_fdata()
        
        # Apply factor
        pet_suv_data = (pet_data * suv_factor).astype(np.float32)
        
        # Save
        pet_suv = nib.Nifti1Image(pet_suv_data, affine)
        nib.save(pet_suv, str(output_path))
        print(f"   Saved SUV image to: {output_path.name}")
    except Exception as e:
        print(f"❌ Error creating SUV NIfTI: {e}")

# --- Core Conversion Functions using SimpleITK ---

def dcm2nii_sitk(dcm_dir, output_file_path):
    """
    Generic function to convert DICOM series to NIfTI using SimpleITK.
    Handles series selection automatically (picks the largest series in folder).
    """
    reader = sitk.ImageSeriesReader()
    
    # Find DICOM series IDs in the directory
    try:
        series_ids = reader.GetGDCMSeriesIDs(str(dcm_dir))
    except Exception as e:
        # Fallback for weird paths
        series_ids = []

    if not series_ids:
        # Sometimes SimpleITK fails if folder contains subfolders. 
        # But our find_studies logic should handle this.
        # Let's try to force reading file names manually if GetGDCMSeriesIDs fails
        print(f"   ⚠️ SimpleITK didn't find series ID automatically in {dcm_dir.name}, trying manual scan...")
        # (This is a simplified fallback, usually not needed if structure is correct)
        raise ValueError(f"No DICOM series found in {dcm_dir}")
    
    # If multiple series exist (e.g., Localizer + CT), pick the one with most files
    selected_series_id = series_ids[0]
    max_files = 0
    
    for sid in series_ids:
        fnames = reader.GetGDCMSeriesFileNames(str(dcm_dir), sid)
        if len(fnames) > max_files:
            max_files = len(fnames)
            selected_series_id = sid
            
    # Load the selected series
    dicom_names = reader.GetGDCMSeriesFileNames(str(dcm_dir), selected_series_id)
    reader.SetFileNames(dicom_names)
    
    # Read and Execute
    image = reader.Execute()
    
    # Write to NIfTI
    sitk.WriteImage(image, str(output_file_path))

def dcm2nii_CT(ct_dir, nii_out_path):
    print(f"   Converting CT from: {ct_dir}")
    output_path = nii_out_path / 'CT.nii.gz'
    dcm2nii_sitk(ct_dir, output_path)

def dcm2nii_PET(pet_dir, nii_out_path):
    print(f"   Converting PET from: {pet_dir}")
    
    # 1. Convert Raw PET
    raw_pet_path = nii_out_path / 'PET.nii.gz'
    dcm2nii_sitk(pet_dir, raw_pet_path)
    
    # 2. Calculate SUV
    # Find a sample DCM file to read metadata
    sample_dcm = None
    for f in pet_dir.glob('*'):
        if f.is_file() and f.suffix.lower() not in ['.xml', '.txt']:
            sample_dcm = f
            break
    
    if sample_dcm:
        suv_factor = calculate_suv_factor(sample_dcm)
        print(f"   Calculated SUV Factor: {suv_factor}")
        convert_pet_to_suv(raw_pet_path, suv_factor, nii_out_path / 'SUV.nii.gz')
    else:
        print("⚠️ No valid DICOM found for SUV calculation.")

def dcm2nii_mask(seg_dir, nii_out_path):
    """
    Conversion of SEG/Mask. 
    Kept the original logic (pydicom/numpy) as SimpleITK can be tricky with specific SEG SOP classes.
    """
    print(f"   Converting SEG from: {seg_dir}")
    try:
        # Find the SEG file (usually a single file)
        seg_files = list(seg_dir.glob('*.dcm'))
        if not seg_files:
             # Try recursive
             seg_files = list(seg_dir.rglob('*.dcm'))
        
        if not seg_files:
            raise ValueError("No SEG DICOM file found.")

        mask_dcm = seg_files[0]
        
        # 🛠️ FIX: Use dcmread instead of read_file (pydicom 3.0 update)
        mask = pydicom.dcmread(str(mask_dcm)) 
        
        mask_array = mask.pixel_array
        
        # Orientation correction (Dataset specific logic from original script)
        mask_array = np.transpose(mask_array,(2,1,0))  
        
        try:
            mask_orientation = mask[0x5200, 0x9229][0].PlaneOrientationSequence[0].ImageOrientationPatient
            if mask_orientation[4] == 1:
                mask_array = np.flip(mask_array, 1)
        except:
            pass # Pass if orientation tags are different
        
        # Get affine from PET (Requires PET to be converted first)
        pet_path = nii_out_path / 'PET.nii.gz'
        if not pet_path.exists():
             print("⚠️ PET file missing (PET.nii.gz), cannot align Mask.")
             return

        pet = nib.load(str(pet_path))
        pet_affine = pet.affine
        
        # Save
        mask_out = nib.Nifti1Image(mask_array, pet_affine)
        nib.save(mask_out, nii_out_path / 'SEG.nii.gz')
        print("   Saved SEG.nii.gz")
        
    except Exception as e:
        print(f"❌ Error converting SEG: {e}")
        # Print full trace for debugging if needed
        import traceback
        traceback.print_exc()

def resample_ct(nii_out_path):
    try:
        ct_path = nii_out_path / 'CT.nii.gz'
        pet_path = nii_out_path / 'PET.nii.gz'
        
        if not ct_path.exists() or not pet_path.exists():
            return

        ct = nib.load(str(ct_path))
        pet = nib.load(str(pet_path))
        
        print("   Resampling CT to PET resolution...")
        CTres = nilearn.image.resample_to_img(ct, pet, fill_value=-1024)
        nib.save(CTres, nii_out_path / 'CTres.nii.gz')
        print("   Saved CTres.nii.gz")
    except Exception as e:
        print(f"⚠️ Resampling failed: {e}")

# --- Directory & Modality Handling ---

def find_studies(path_to_data):
    """
    Finds study subdirectories.
    🛠️ FIX: Adjusted to assume the input path IS the patient folder (based on your docker mount).
    """
    dicom_root = plb.Path(path_to_data)
    study_dirs = []
    
    # The Docker mount is /data/dicom_in -> "patient 1"
    # Inside "patient 1", we expect "study 1".
    
    # Iterate over items in the root (patient folder)
    for item in dicom_root.iterdir():
        if item.is_dir():
            # We assume any subdirectory here is a "Study" folder (e.g., "study 1")
            study_dirs.append(item)
            
    return study_dirs

def identify_modalities(study_dir):
    """
    Scans a study directory RECURSIVELY to find CT, PET, and SEG folders.
    Returns a dictionary mapping 'CT', 'PT', 'SEG' to their folder paths.
    """
    modalities = {}
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(study_dir):
        # Look for at least one DICOM file in the folder to identify it
        for file in files:
            if file.endswith('.dcm') or '.' not in file:
                try:
                    filepath = Path(root) / file
                    # Read only header for speed
                    ds = pydicom.dcmread(filepath, stop_before_pixels=True)
                    
                    if hasattr(ds, "Modality"):
                        mod = ds.Modality
                        
                        # Fix for Segmentation sometimes labeled differently
                        if mod == "RTSTRUCT":
                            mod = "SEG"

                        # Store the folder path
                        modalities[mod] = Path(root)
                        modalities["ID"] = ds.StudyInstanceUID
                        
                        # Once we identify the folder's modality, we can skip other files in this specific folder
                        # But we continue walking other folders
                        break 
                except:
                    continue
                    
    return modalities

def convert_tcia_to_nifti(study_dirs, nii_out_root):
    for study_dir in tqdm(study_dirs):
        
        # Use the folder name (e.g., "study 1") as the identifier
        study_name = study_dir.name
        print(f"\nPROCESSING: {study_name}")
        
        # 1. Output Path
        # We save directly into nii_out_root / study_name
        nii_out_path = nii_out_root / study_name
        os.makedirs(nii_out_path, exist_ok=True)

        # 2. Identify Modalities
        try:
            modalities = identify_modalities(study_dir)
            print(f"   Found modalities: {list(modalities.keys())}")
        except Exception as e:
            print(f"❌ Error identifying modalities: {e}")
            continue

        # 3. Convert CT
        ct_success = False
        if "CT" in modalities:
            try:
                dcm2nii_CT(modalities["CT"], nii_out_path)
                ct_success = True
            except Exception as e:
                print(f"❌ CT Conversion Failed: {e}")
        else:
            print("⚠️ CT data missing.")

        # 4. Convert PET
        pet_success = False
        if "PT" in modalities:
            try:
                dcm2nii_PET(modalities["PT"], nii_out_path)
                pet_success = True
            except Exception as e:
                 print(f"❌ PET Conversion Failed: {e}")
        else:
            print("⚠️ PET data missing.")

        # 5. Convert Segmentation
        if "SEG" in modalities:
            dcm2nii_mask(modalities["SEG"], nii_out_path)
        elif "RTSTRUCT" in modalities:
             dcm2nii_mask(modalities["RTSTRUCT"], nii_out_path)

        # 6. Resample
        if ct_success and pet_success:
            resample_ct(nii_out_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python tcia_dicom_to_nifti.py <DICOM_INPUT_FOLDER> <NIFTI_OUTPUT_FOLDER>")
        sys.exit(1)

    path_to_data = plb.Path(sys.argv[1])
    nii_out_root = plb.Path(sys.argv[2])

    print(f"Input: {path_to_data}")
    print(f"Output: {nii_out_root}")

    study_dirs = find_studies(path_to_data)
    convert_tcia_to_nifti(study_dirs, nii_out_root)