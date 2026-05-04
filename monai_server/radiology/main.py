# c:\Users\ELAL\Desktop\projects\Cancer-detection-AI\monai_server\radiology\main.py

import logging
import os
import random
from typing import Dict

from monai.networks.nets import SwinUNETR

from monailabel.interfaces.app import MONAILabelApp
from monailabel.interfaces.tasks.strategy import Strategy
from monailabel.interfaces.tasks.infer_v2 import InferTask
from monailabel.interfaces.tasks.train import TrainTask

# Import your inference and training tasks
from lib.infers.segmentation import Segmentation
try:
    from lib.trainers.segmentation import Segmentation as TrainSegmentation
except ImportError:
    TrainSegmentation = None

logger = logging.getLogger(__name__)


class CTOnlyRandom(Strategy):
    def __init__(self):
        super().__init__("Randomly select a CT image")

    def __call__(self, request, datastore):
        unlabeled_images = datastore.get_unlabeled_images()
        ct_images = [img for img in unlabeled_images if "_CT" in img]
        if not ct_images:
            return None
        return {"id": random.choice(ct_images)}


class MyApp(MONAILabelApp):
    def __init__(self, app_dir, studies, conf):
        self.model_dir = os.path.join(app_dir, "model")
        os.makedirs(self.model_dir, exist_ok=True)

        self.labels = {
            "background": 0,
            "tumor": 1
        }

        self.network = SwinUNETR(
            in_channels=2,
            out_channels=2,
            feature_size=48,
            spatial_dims=3
        )

        super().__init__(
            app_dir=app_dir,
            studies=studies,
            conf=conf,
            name="BladderTumorActiveLearning",
            description="Active Learning for Bladder Tumor segmentation using multi-modal 3D scans (CT and PET)",
            version="1.0"
        )

    def init_infers(self) -> Dict[str, InferTask]:
        infers: Dict[str, InferTask] = {}
        
        infers["segmentation"] = Segmentation(
            path=[
                os.path.join(self.model_dir, "pretrained.pt"),
                os.path.join(self.model_dir, "segmentation.pt")
            ],
            network=self.network,
            labels=self.labels,
            roi_size=(96, 96, 96)
        )
        
        return infers

    def init_trainers(self) -> Dict[str, TrainTask]:
        trainers: Dict[str, TrainTask] = {}
        
        if TrainSegmentation is not None:
            trainers["segmentation"] = TrainSegmentation(
                model_dir=self.model_dir,
                network=self.network,
                labels=self.labels,
                roi_size=(96, 96, 96)
            )
            
        return trainers

    def init_strategies(self) -> Dict[str, Strategy]:
        return {"random": CTOnlyRandom()}
