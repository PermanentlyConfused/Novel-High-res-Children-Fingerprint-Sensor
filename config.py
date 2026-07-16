from os import path

DATA_FILEPATH = path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "Fingerprint_Data")
LOG_FILEPATH = path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "fingerprint_log.csv") 
FILE_EXTENSION = '.png'

PICTURE_RES = (3840, 2160)
FPS = 30