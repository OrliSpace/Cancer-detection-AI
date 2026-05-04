# exec(open(r"C:\Users\ELAL\Desktop\projects\Cancer-detection-AI\monai_server\petct_loader.py").read())

import os
import qt
import slicer
import urllib.request

# Determine script directory to locate .env file
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback if executed via exec() in Slicer Python console
    print("not the right path for the dataset")
    
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")
MONAI_SERVER_URL = "http://127.0.0.1:8000"  # Default fallback

if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                if key == "MONAI_SERVER_URL":
                    MONAI_SERVER_URL = val.strip()

# Remove previous shortcut if it exists to avoid duplications
if hasattr(slicer, 'pet_toggle_shortcut'):
    slicer.pet_toggle_shortcut.disconnect('activated()')
    slicer.pet_toggle_shortcut.setParent(None)

def toggle_pet_visibility():
    """Toggles the PET opacity between 0.0 and 0.5"""
    slice_logic = slicer.app.layoutManager().sliceWidget('Red').sliceLogic()
    current_opacity = slice_logic.GetSliceCompositeNode().GetForegroundOpacity()
    new_opacity = 0.0 if current_opacity > 0 else 0.5
    for view_name in ['Red', 'Yellow', 'Green']:
        slicer.app.layoutManager().sliceWidget(view_name).sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(new_opacity)

def load_pet_overlay():
    # Identify active CT
    layoutManager = slicer.app.layoutManager()
    redWidget = layoutManager.sliceWidget('Red')
    if not redWidget:
        slicer.util.errorDisplay("Red slice view not found.")
        return

    redLogic = redWidget.sliceLogic()
    bgLayer = redLogic.GetBackgroundLayer()
    bgNode = bgLayer.GetVolumeNode() if bgLayer else None

    if not bgNode or "_CT" not in bgNode.GetName():
        slicer.util.errorDisplay("Please load a CT volume containing '_CT' in its name first.")
        return

    ct_name = bgNode.GetName()
    base_name = ct_name.split('_CT')[0]
    pet_name = f"{base_name}_PET"
    print(f"Debug: Original node name '{ct_name}' -> Requested PET name '{pet_name}'")

    # Download PET
    url = f"{MONAI_SERVER_URL}/datastore/image?image={pet_name}"
    temp_dir = slicer.app.temporaryPath
    pet_filepath = os.path.join(temp_dir, f"{pet_name}.nii.gz")

    slicer.util.showStatusMessage(f"Downloading {pet_name}...")
    try:
        urllib.request.urlretrieve(url, pet_filepath)
    except Exception as e:
        slicer.util.errorDisplay(f"Failed to download PET image. Is the MONAI server running?\nError: {e}")
        slicer.util.showStatusMessage("")
        return

    # Load PET into scene
    slicer.util.showStatusMessage(f"Loading {pet_name}...")
    petNode = slicer.util.loadVolume(pet_filepath)

    if not petNode:
        slicer.util.errorDisplay("Failed to load PET volume into the scene.")
        slicer.util.showStatusMessage("")
        return

    # Configure CT (Background) display presets
    bgNode.CreateDefaultDisplayNodes()
    ct_display = bgNode.GetDisplayNode()
    ct_display.SetAndObserveColorNodeID('vtkMRMLColorTableNodeGrey')
    ct_display.AutoWindowLevelOff()
    ct_display.SetWindowLevel(400, 40)

    # Configure PET (Foreground) display presets
    petNode.CreateDefaultDisplayNodes()
    petDisplayNode = petNode.GetDisplayNode()
    petDisplayNode.SetAndObserveColorNodeID('vtkMRMLColorTableNodeRainbow')
    petDisplayNode.AutoWindowLevelOn()

    # Configure slice composite nodes
    slicer.util.showStatusMessage("Configuring views...")
    for sliceName in ['Red', 'Yellow', 'Green']:
        sliceWidget = layoutManager.sliceWidget(sliceName)
        if sliceWidget:
            compositeNode = sliceWidget.mrmlSliceCompositeNode()
            compositeNode.SetBackgroundVolumeID(bgNode.GetID())
            compositeNode.SetForegroundVolumeID(petNode.GetID())
            compositeNode.SetForegroundOpacity(0.5)

    # Setup shortcut key for toggling PET visibility
    shortcut_key = 'p'
    slicer.pet_toggle_shortcut = qt.QShortcut(qt.QKeySequence(shortcut_key), slicer.util.mainWindow())
    slicer.pet_toggle_shortcut.connect('activated()', toggle_pet_visibility)

    slicer.util.showStatusMessage("PET Overlay loaded successfully (Press 'p' to toggle).")

# Create toolbar button
toolbar = slicer.util.mainWindow().addToolBar("PETCTLoaderToolBar")
action = qt.QAction("Load PET Overlay", slicer.util.mainWindow())
action.triggered.connect(load_pet_overlay)
toolbar.addAction(action)