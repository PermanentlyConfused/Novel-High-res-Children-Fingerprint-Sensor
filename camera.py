from PyQt5 import QtCore
import cv2
from config import *

class CameraThread(QtCore.QThread):
    frame_ready = QtCore.pyqtSignal(object) 
    def __init__(self, camera_index, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        # print(camera_index)
        self._running = True
        self._preview_running = True
        self.cap = None

    # def modifyFocus(self,focusVal):
    #     self.cap.set(cv2.CAP_PROP_FOCUS, focusVal)
    
    # def modifyExposure(self,exposureVal):
    #     self.cap.set(cv2.CAP_PROP_EXPOSURE, exposureVal)
    
    def run(self):
        # open capture
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            return
        # set camera properties
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, PICTURE_RES[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, PICTURE_RES[1])
        self.cap.set(cv2.CAP_PROP_FPS, FPS)
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0) # manual mode
        self.cap.set(cv2.CAP_PROP_EXPOSURE, -9)
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)
        self.cap.set(cv2.CAP_PROP_WB_TEMPERATURE,0)
        self.cap.set(cv2.CAP_PROP_ISO_SPEED, 800) 
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(cv2.CAP_PROP_FOCUS, 1024)
        print("DEBUG--", int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        while self._running and self.cap.isOpened():
            if self._preview_running:
                ret, frame = self.cap.read()
                if ret:
                    h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    y1 = round(h * 0.0)
                    y2 = round(h * 1)
                    x1 = round(w * 0.1)
                    x2 = round(w * 0.72)
                    cropped = frame[y1:y2, x1:x2]
                    cropped = cv2.flip(cropped,1)
                    self.frame_ready.emit(cropped)
            else:
                time.sleep(0.05)

        if self.cap and self.cap.isOpened():
            self.cap.release()

    def stop(self):
        self._running = False
        self.wait()

    def pause_preview(self):
        self._preview_running = False

    def resume_preview(self):
        self._preview_running = True