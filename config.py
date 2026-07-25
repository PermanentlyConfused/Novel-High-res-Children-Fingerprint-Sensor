import os

DATA_FILEPATH = os.path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "Fingerprint_Data")
LOG_FILEPATH = os.path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "fingerprint_log.csv") 
FILE_EXTENSION = '.png'

PICTURE_RES = (3840, 2160)
FPS = 30

#! Enable image segmentation for background removal. False = off | True = on
REMBG_ENABLE = False