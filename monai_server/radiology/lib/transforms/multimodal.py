## my  code

import os
from monai.transforms import MapTransform

class AddPETPathd(MapTransform):
    """
    מקבלת את נתיב ה-CT ממילון הנתונים, 
    מאתרת את קובץ ה-PET התואם באותה תיקייה, 
    ומוסיפה אותו למילון תחת המפתח 'pet_image'.
    """
    def __init__(self, keys, allow_missing_keys=False):
        super().__init__(keys, allow_missing_keys)

    def __call__(self, data):
        d = dict(data)
        for key in self.key_iterator(d):
            ct_path = d[key]
            if isinstance(ct_path, str):
                pet_path = ct_path.replace("_CT.nii.gz", "_PET.nii.gz")
                
                if not os.path.exists(pet_path):
                    raise FileNotFoundError(f"Missing PET file for CT: {ct_path}. Expected at: {pet_path}")
                
                d["pet_image"] = pet_path
        return d