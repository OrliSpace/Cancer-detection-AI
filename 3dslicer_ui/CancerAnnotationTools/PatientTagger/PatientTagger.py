import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import json

# =========================================================================
# 1. מחלקת ההגדרות של המודול
# =========================================================================
class PatientTagger(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Patient Tagger"
        self.parent.categories = ["Cancer Detection"]
        self.parent.dependencies = []
        self.parent.contributors = ["Orli Davidpur"]
        self.parent.helpText = "Module for manual PET-CT segmentation and clinical data tagging."

# =========================================================================
# 2. מחלקת הלוגיקה (ה"מוח")
# =========================================================================
class PatientTaggerLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

    def loadNextUntaggedPatient(self, base_dicom_dir, base_info_dir):
        """מוצאת את המטופל הבא שטרם תויג וטוענת אותו"""
        if not os.path.exists(base_dicom_dir):
            return None

        if not os.path.exists(base_info_dir):
            os.makedirs(base_info_dir)

        patient_ids = [d for d in os.listdir(base_dicom_dir) if os.path.isdir(os.path.join(base_dicom_dir, d))]
        patient_to_load = None

        for pid in patient_ids:
            info_path = os.path.join(base_info_dir, pid)
            if not os.path.exists(info_path):
                os.makedirs(info_path)
                patient_to_load = pid
                break
            elif not any(f.endswith('.seg.nrrd') for f in os.listdir(info_path)):
                patient_to_load = pid
                break

        if not patient_to_load:
            return None

        return self.loadSpecificPatient(patient_to_load, base_dicom_dir, base_info_dir)

    def loadSpecificPatient(self, patient_id, base_dicom_dir, base_info_dir):
        """טוענת מטופל ספציפי ומחפשת נתוני עבר (JSON וסגמנטציה)"""
        import slicer
        from DICOMLib import DICOMUtils

        patient_dir = os.path.join(base_dicom_dir, patient_id)
        if not os.path.exists(patient_dir):
            print(f"Error: Patient {patient_id} not found in DICOM directory.")
            return None

        patient_info_dir = os.path.join(base_info_dir, patient_id)
        if not os.path.exists(patient_info_dir):
            os.makedirs(patient_info_dir)

        slicer.mrmlScene.Clear(0)

        # -------------------------------------------------------------
        # בדיקה וטעינה של נתוני עבר (JSON + NRRD) במידה וקיימים
        # -------------------------------------------------------------
        clinical_data = None
        existing_seg_node = None
        
        json_path = os.path.join(patient_info_dir, "info.json")
        seg_path = os.path.join(patient_info_dir, f"{patient_id}_seg.seg.nrrd")

        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    clinical_data = json.load(f)
                print(f"Loaded existing clinical data for {patient_id}.")
            except Exception as e:
                print(f"Failed to load existing JSON: {e}")

        if os.path.exists(seg_path):
            try:
                existing_seg_node = slicer.util.loadSegmentation(seg_path)
                print(f"Loaded existing segmentation for {patient_id}.")
            except Exception as e:
                print(f"Failed to load existing Segmentation: {e}")
        # -------------------------------------------------------------

        # ניווט לתיקיית ה-OB וטעינת ה-DICOM
        study_dirs = [d for d in os.listdir(patient_dir) if d.startswith("Study")]
        if not study_dirs: return None
        ob_dir = os.path.join(patient_dir, study_dirs[0], "OB")
        if not os.path.exists(ob_dir): return None

        original_db_path = slicer.dicomDatabase.databaseDirectory
        temp_db_dir = os.path.join(slicer.app.temporaryPath, "TempDICOMDB")
        if not os.path.exists(temp_db_dir): os.makedirs(temp_db_dir)
        DICOMUtils.openDatabase(temp_db_dir)
        DICOMUtils.importDicom(ob_dir)
        
        db = slicer.dicomDatabase
        ct_series = None
        pt_series = None
        
        for patient in db.patients():
            for study in db.studiesForPatient(patient):
                for series in db.seriesForStudy(study):
                    files = db.filesForSeries(series)
                    if not files: continue
                    modality = db.fileValue(files[0], "0008,0060")
                    
                    if modality == "CT":
                        if not ct_series or len(files) > len(db.filesForSeries(ct_series)):
                            ct_series = series
                    elif modality == "PT":
                        if not pt_series or len(files) > len(db.filesForSeries(pt_series)):
                            pt_series = series
        
        ct_node = None
        pt_node = None
        
        if ct_series:
            loaded_ct_ids = DICOMUtils.loadSeriesByUID([ct_series])
            if loaded_ct_ids: ct_node = slicer.mrmlScene.GetNodeByID(loaded_ct_ids[0])
        if pt_series:
            loaded_pt_ids = DICOMUtils.loadSeriesByUID([pt_series])
            if loaded_pt_ids: pt_node = slicer.mrmlScene.GetNodeByID(loaded_pt_ids[0])
                
        if original_db_path:
            DICOMUtils.openDatabase(original_db_path)
            
        # הגדרת תצוגת PET ו-CT
        if ct_node and pt_node:
            if not pt_node.GetDisplayNode():
                pt_node.CreateDefaultDisplayNodes()
            display_node = pt_node.GetDisplayNode()

            if display_node:
                color_node = slicer.util.getNode('PET-Heat')
                if color_node:
                    display_node.SetAndObserveColorNodeID(color_node.GetID())
                display_node.AutoWindowLevelOff()
                display_node.SetWindowLevel(10000, 6000)

            slicer.util.setSliceViewerLayers(background=ct_node, foreground=pt_node, foregroundOpacity=0.2)
            slicer.util.resetSliceViews()

        # עכשיו מחזירים גם את הנתונים הקיימים (אם יש) ל-GUI
        return patient_id, ct_node, pt_node, clinical_data, existing_seg_node

    def savePatientData(self, patient_id, clinical_data, segmentation_node, output_base_dir):
        """שומרת את המידע הקליני והסגמנטציה לתיקיית המטופל"""
        import os
        import json
        import slicer

        patient_output_dir = os.path.join(output_base_dir, patient_id)
        if not os.path.exists(patient_output_dir):
            os.makedirs(patient_output_dir)

        json_path = os.path.join(patient_output_dir, "info.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(clinical_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save JSON: {e}")
            return False

        if segmentation_node:
            seg_path = os.path.join(patient_output_dir, f"{patient_id}_seg.seg.nrrd")
            try:
                slicer.util.saveNode(segmentation_node, seg_path)
            except Exception as e:
                print(f"Failed to save Segmentation: {e}")
                return False
        
        return True

# =========================================================================
# 3. מחלקת ממשק המשתמש (GUI)
# =========================================================================
class PatientTaggerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.current_patient_id = None 

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        settingsCollapsibleButton = ctk.ctkCollapsibleButton()
        settingsCollapsibleButton.text = "Configuration"
        self.layout.addWidget(settingsCollapsibleButton)
        settingsFormLayout = qt.QFormLayout(settingsCollapsibleButton)

        self.dicomDirSelector = ctk.ctkDirectoryButton()
        savedDicomDir = slicer.app.settings().value("PatientTagger/DicomDir", "")
        if savedDicomDir: self.dicomDirSelector.directory = savedDicomDir
        settingsFormLayout.addRow("DICOM Input Dir:", self.dicomDirSelector)

        self.infoDirSelector = ctk.ctkDirectoryButton()
        savedInfoDir = slicer.app.settings().value("PatientTagger/InfoDir", "")
        if savedInfoDir: self.infoDirSelector.directory = savedInfoDir
        settingsFormLayout.addRow("Data Info Output Dir:", self.infoDirSelector)

        self.loadButton = qt.QPushButton("1. Load Next Untagged Patient")
        self.loadButton.setStyleSheet("font-weight: bold; padding: 10px; height: 30px;")
        self.layout.addWidget(self.loadButton)

        specificLoadLayout = qt.QHBoxLayout()
        self.specificIdInput = qt.QLineEdit()
        self.specificIdInput.setPlaceholderText("Enter Patient ID (e.g. 30977820)...")
        self.loadSpecificButton = qt.QPushButton("Load Specific ID")
        self.loadSpecificButton.setStyleSheet("font-weight: bold; padding: 5px;")
        specificLoadLayout.addWidget(self.specificIdInput)
        specificLoadLayout.addWidget(self.loadSpecificButton)
        self.layout.addLayout(specificLoadLayout)

        self.patientIdLabel = qt.QLabel("Active Patient: None")
        self.patientIdLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin: 10px 0px;")
        self.patientIdLabel.setAlignment(qt.Qt.AlignCenter)
        self.layout.addWidget(self.patientIdLabel)

        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Patient Clinical Data"
        self.layout.addWidget(parametersCollapsibleButton)
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self.heightInput = qt.QDoubleSpinBox()
        self.heightInput.setSuffix(" cm")
        self.heightInput.setMaximum(250)
        parametersFormLayout.addRow("Height:", self.heightInput)

        self.weightInput = qt.QDoubleSpinBox()
        self.weightInput.setSuffix(" kg")
        self.weightInput.setMaximum(300)
        parametersFormLayout.addRow("Weight:", self.weightInput)

        self.tumorTypeInput = qt.QComboBox()
        self.tumorTypeInput.addItems(["Unknown", "Lymphoma", "Lung", "Breast", "Other"])
        parametersFormLayout.addRow("Tumor Type:", self.tumorTypeInput)

        self.diseaseInput = qt.QLineEdit()
        parametersFormLayout.addRow("Background Diseases:", self.diseaseInput)

        self.notesInput = qt.QTextEdit()
        parametersFormLayout.addRow("Notes:", self.notesInput)

        self.segmentationCollapsibleButton = ctk.ctkCollapsibleButton()
        self.segmentationCollapsibleButton.text = "2. Active Segmentation"
        self.segmentationCollapsibleButton.collapsed = True 
        self.layout.addWidget(self.segmentationCollapsibleButton)
        segmentationLayout = qt.QVBoxLayout(self.segmentationCollapsibleButton)
        
        self.segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
        self.segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        self.segmentEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segmentEditorWidget.setSegmentationNodeSelectorVisible(False)
        self.segmentEditorWidget.setSourceVolumeNodeSelectorVisible(False)
        segmentationLayout.addWidget(self.segmentEditorWidget)

        self.saveButton = qt.QPushButton("3. Save Data & Finish Patient")
        self.saveButton.setStyleSheet("font-weight: bold; padding: 10px; background-color: #4CAF50; color: white;")
        self.saveButton.enabled = False 
        self.layout.addWidget(self.saveButton)

        self.layout.addStretch(1)

        self.loadButton.connect('clicked(bool)', self.onLoadNextClicked)
        self.loadSpecificButton.connect('clicked(bool)', self.onLoadSpecificClicked)
        self.saveButton.connect('clicked(bool)', self.onSaveClicked)
        self.dicomDirSelector.connect('directoryChanged(const QString&)', 
                                      lambda d: slicer.app.settings().setValue("PatientTagger/DicomDir", d))
        self.infoDirSelector.connect('directoryChanged(const QString&)', 
                                     lambda d: slicer.app.settings().setValue("PatientTagger/InfoDir", d))

        self.logic = PatientTaggerLogic()

    def _setupLoadedPatientUI(self, loaded_id, ct_node, pt_node, clinical_data, existing_seg_node):
        """פונקציה שמעדכנת את המסך לאחר טעינה, ומשחזרת נתונים קיימים אם יש"""
        self.current_patient_id = loaded_id
        
        self.patientIdLabel.setText(f"Active Patient: {self.current_patient_id}")
        self.patientIdLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #e67e22; margin: 10px 0px;")

        # =========================================================
        # 1. טעינת מידע קליני לתיבות הטקסט (אם יש)
        # =========================================================
        if clinical_data:
            self.heightInput.value = clinical_data.get("height_cm", 0.0)
            self.weightInput.value = clinical_data.get("weight_kg", 0.0)
            tumor_type = clinical_data.get("tumor_type", "Unknown")
            type_index = self.tumorTypeInput.findText(tumor_type)
            if type_index >= 0:
                self.tumorTypeInput.currentIndex = type_index
            self.diseaseInput.setText(clinical_data.get("background_diseases", ""))
            self.notesInput.setPlainText(clinical_data.get("notes", ""))
        else:
            # איפוס במידה ומדובר בחולה נקי
            self.heightInput.value = 0.0
            self.weightInput.value = 0.0
            self.tumorTypeInput.currentIndex = 0
            self.diseaseInput.clear()
            self.notesInput.clear()

        # =========================================================
        # 2. אתחול עורך הסגמנטציה וטעינת הציור הקודם (אם יש)
        # =========================================================
        new_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        self.segmentEditorWidget.setMRMLSegmentEditorNode(new_editor_node)
        
        if existing_seg_node:
            segmentationNode = existing_seg_node
            # אין צורך להוסיף סגמנט חדש, כי טענו את הקובץ הקיים!
        else:
            segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            segmentationNode.SetName(f"{self.current_patient_id}_Segmentation")
            if ct_node:
                segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(ct_node)
            # אם זה חולה חדש לגמרי, יוצרים עבורו את ה-"Tumor" הראשון
            segmentationNode.GetSegmentation().AddEmptySegment("Tumor", "Tumor", [0, 1, 0])
        
        self.segmentEditorWidget.setSegmentationNode(segmentationNode)
        source_node = pt_node if pt_node else ct_node
        self.segmentEditorWidget.setSourceVolumeNode(source_node)
        
        self.segmentationCollapsibleButton.collapsed = False
        self.saveButton.enabled = True

    def onLoadNextClicked(self):
        base_dicom_dir = self.dicomDirSelector.directory
        base_info_dir = self.infoDirSelector.directory
        if not base_dicom_dir or not base_info_dir:
             qt.QMessageBox.warning(slicer.util.mainWindow(), "Missing Paths", "Please select directories.")
             return

        result = self.logic.loadNextUntaggedPatient(base_dicom_dir, base_info_dir)
        if result:
            self._setupLoadedPatientUI(result[0], result[1], result[2], result[3], result[4])
        else:
            self.patientIdLabel.setText("Active Patient: None")
            qt.QMessageBox.information(slicer.util.mainWindow(), "Done", "No more untagged patients found.")

    def onLoadSpecificClicked(self):
        target_id = self.specificIdInput.text.strip()
        if not target_id:
            qt.QMessageBox.warning(slicer.util.mainWindow(), "Missing ID", "Please enter a Patient ID first.")
            return

        base_dicom_dir = self.dicomDirSelector.directory
        base_info_dir = self.infoDirSelector.directory
        if not base_dicom_dir or not base_info_dir:
             qt.QMessageBox.warning(slicer.util.mainWindow(), "Missing Paths", "Please select directories.")
             return

        result = self.logic.loadSpecificPatient(target_id, base_dicom_dir, base_info_dir)
        if result:
            self._setupLoadedPatientUI(result[0], result[1], result[2], result[3], result[4])
            self.specificIdInput.clear()
        else:
            self.patientIdLabel.setText("Active Patient: None")
            qt.QMessageBox.warning(slicer.util.mainWindow(), "Not Found", f"Could not find DICOM folder for Patient ID: {target_id}")

    def onSaveClicked(self):
        if not self.current_patient_id: return

        clinical_data = {
            "patient_id": self.current_patient_id,
            "height_cm": self.heightInput.value,
            "weight_kg": self.weightInput.value,
            "tumor_type": self.tumorTypeInput.currentText,
            "background_diseases": self.diseaseInput.text,
            "notes": self.notesInput.toPlainText()
        }

        segmentation_node = self.segmentEditorWidget.segmentationNode()
        success = self.logic.savePatientData(
            self.current_patient_id, 
            clinical_data, 
            segmentation_node, 
            self.infoDirSelector.directory
        )

        if success:
            qt.QMessageBox.information(slicer.util.mainWindow(), "Success", f"Data for patient {self.current_patient_id} saved successfully!")
            self.resetInterface()
        else:
            qt.QMessageBox.critical(slicer.util.mainWindow(), "Error", "Failed to save data.")

    def resetInterface(self):
        self.current_patient_id = None
        self.patientIdLabel.setText("Active Patient: None")
        self.patientIdLabel.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin: 10px 0px;")
        self.heightInput.value = 0
        self.weightInput.value = 0
        self.tumorTypeInput.currentIndex = 0
        self.diseaseInput.clear()
        self.notesInput.clear()
        self.segmentationCollapsibleButton.collapsed = True
        self.saveButton.enabled = False
        slicer.mrmlScene.Clear(0)