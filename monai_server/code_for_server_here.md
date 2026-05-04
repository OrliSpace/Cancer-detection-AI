Here is the complete list of files we have modified or added to the MONAI Label server and client during our multi-modal CT+PET project:

### Phase 1: Data Preparation (Dataset Store)

* **Registration & Alignment**: Spatially registered and aligned multi-modal scans to NIfTI format.
* **Naming Convention**: Organized paired scans with strict `_CT.nii.gz` and `_PET.nii.gz` suffixes.
* **Data Cleaning**: Verified dataset for clean data (e.g., empty bladder scans).

### Phase 2: Server Development (MONAI Label App)

**Modified Files (Changed):**
* `radiology/main.py` - Updated the network architecture to `SwinUNETR`, configured it to accept 2 input channels and output 2 channels, and replaced the default labels with `{"background": 0, "tumor": 1}`. Added a custom Active Learning strategy `CTOnlyRandom` to ensure only CT scans are fetched when clicking "Next Sample".
* `radiology/lib/infers/segmentation.py` - Completely rewrote the `pre_transforms` to load both CT and PET, apply custom spacings, independently scale/normalize their intensities, and concatenate them into a single 2-channel tensor.
* `radiology/lib/trainers/segmentation.py` - Replicated the multi-modal `pre_transforms` for the training and validation data loaders, and configured the `DiceCELoss` (with `include_background=False` and `squared_pred=True`) to handle extreme class imbalances and small bladder tumors.

**New Files (Added):**
* `radiology/lib/transforms/multimodal.py` - Created this file to house the custom `AddPETPathd` transform, which dynamically finds and attaches the matching `_PET.nii.gz` file for each `_CT.nii.gz` scan in the dataset.

### Phase 3: 3D Slicer Automation (Client)

**New Files (Added):**
* `petct_loader.py` - Created an external Python script for 3D Slicer that adds a "Load PET Overlay" button to the toolbar. It automatically:
  - Identifies the loaded CT volume.
  - Downloads the corresponding PET volume from the MONAI Label server API.
  - Sets the correct Slicer display presets (`vtkMRMLColorTableNodeGrey` for CT, `vtkMRMLColorTableNodeRainbow` for PET).
  - Configures Window/Level for both images.
  - Sets up a composite view with 0.5 opacity for the foreground (PET).
  - Adds a keyboard shortcut (`p`) to toggle the PET overlay's visibility.