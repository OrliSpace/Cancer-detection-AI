import os
import slicer

BASE_DIR = r"C:\...\sorted\Study_xxx"
OUTPUT_DIR = os.path.join(BASE_DIR, "pairs_mrb")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_first_dicom(folder):
    for f in os.listdir(folder):
        if f.lower().endswith(".dcm"):
            return os.path.join(folder, f)
    return None

def find_pairs(base_dir):
    ct_dir = os.path.join(base_dir, "CT")
    pet_dir = os.path.join(base_dir, "PET")

    pairs = []

    for ct in os.listdir(ct_dir):
        for pet in os.listdir(pet_dir):
            if ct.split("_")[0] == pet.split("_")[0]:  # לפי PAIR_X
                pairs.append((ct, pet))

    return pairs

pairs = find_pairs(BASE_DIR)

for idx, (ct_name, pet_name) in enumerate(pairs, start=1):

    slicer.mrmlScene.Clear()

    ct_path = get_first_dicom(os.path.join(BASE_DIR, "CT", ct_name))
    pet_path = get_first_dicom(os.path.join(BASE_DIR, "PET", pet_name))

    if not ct_path or not pet_path:
        continue

    print(f"Processing {ct_name} + {pet_name}")

    ct_node = slicer.util.loadVolume(ct_path)
    pet_node = slicer.util.loadVolume(pet_path)

    if not ct_node or not pet_node:
        continue

    # overlay
    composite = slicer.app.layoutManager().sliceWidget("Red").sliceLogic().GetSliceCompositeNode()
    composite.SetBackgroundVolumeID(ct_node.GetID())
    composite.SetForegroundVolumeID(pet_node.GetID())
    composite.SetForegroundOpacity(0.4)

    # segmentation ready
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(ct_node)

    segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    segmentEditorWidget.setSegmentationNode(segmentationNode)
    segmentEditorWidget.setMasterVolumeNode(ct_node)

    # save
    output_path = os.path.join(OUTPUT_DIR, f"PAIR_{idx}.mrb")
    slicer.util.saveScene(output_path)

    print(f"Saved: {output_path}")

print("ALL DONE")