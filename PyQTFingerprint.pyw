
import os
import sys
import threading
import queue
import datetime
import time
import subprocess

import cv2
import numpy as np
from PIL import Image

from rembg import remove
from rembg.bg import new_session

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

#! ------------------ Configurations ------------------
DATA_FILEPATH = os.path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "Fingerprint_Data")
LOG_FILEPATH = os.path.join(os.environ["USERPROFILE"], "Documents", "FingerprintCapture", "fingerprint_log.csv") 
FILE_EXTENSION = '.png'

PICTURE_RES = (4645, 3496)
FPS = 10

#! ---------------------------------------------------

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def find_arducam_index() -> int | None:
    try:
        from cv2_enumerate_cameras import enumerate_cameras
    except Exception:
        return None
    for camera_info in enumerate_cameras(cv2.CAP_DSHOW):
        if camera_info.name == "Arducam_16MP":
            # print(int(str(camera_info.index)[-1])) #TODO Looks
            return int(str(camera_info.index)[-1])
    return None

#! ---------- Camera Thread ----------
class CameraThread(QtCore.QThread):
    frame_ready = QtCore.pyqtSignal(object) 
    def __init__(self, camera_index, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        # print(camera_index)
        self._running = True
        self._preview_running = True
        self.cap = None

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
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(cv2.CAP_PROP_FOCUS, 1023)
        print( int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        while self._running and self.cap.isOpened():
            if self._preview_running:
                ret, frame = self.cap.read()
                if ret:
                    h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    cropped = frame[round(h * (25/152)) : round(h * (1845/3496)),
                                    round(w * (1465/4645)) : round(w * (3065/4656))]
                    self.frame_ready.emit(cropped)
                time.sleep(1 / FPS)
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

#! ---------- Main Window ----------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(resource_path("./assets/icon.png")))
        self.setWindowTitle("Clarkson AVHBAC Fingerprint Capture")
        self.resize(1200, 800)

        self.duplicate = False
        self.duplicate_number = None
        self.latest_frame = None  
        self.frame_lock = threading.Lock()
        self.task_queue = queue.Queue()
        self.worker_running = True

        # Start rembg session
        self.initialize_rembg()
        
        
        self._build_ui()
        self.worker_thread = threading.Thread(target=self._task_worker, daemon=True)
        self.worker_thread.start()

        # Camera
        camera_index = find_arducam_index()

        if camera_index is None:
            QtWidgets.QMessageBox.critical(self, "‼ Error ‼", "Fingerprint Scanner NOT detected.")
            camera_index = 0  # fall back to default
            # None #! Will test with the camera later

        self.camera_thread = CameraThread(camera_index)
        self.camera_thread.frame_ready.connect(self._on_frame)
        self.camera_thread.start()

        # Start a QTimer to update preview widget (throttled)
        self.preview_timer = QtCore.QTimer()
        self.preview_timer.timeout.connect(self.update_preview_label)
        self.preview_timer.start(50)

    #* ---------------- UI ----------------
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        # Header
        header = QtWidgets.QLabel("AVHBAC Fingerprint Scanner")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header_font = QtGui.QFont("Arial", 24, QtGui.QFont.Bold)
        header.setFont(header_font)
        layout.addWidget(header)

        # Top controls
        top_widget = QtWidgets.QWidget()
        top_layout = QtWidgets.QGridLayout(top_widget)

        normal_font = QtGui.QFont("Arial", 12)

        top_layout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        self.name_entry = QtWidgets.QLineEdit()
        self.name_entry.setFont(normal_font)
        top_layout.addWidget(self.name_entry, 0, 1)

        top_layout.addWidget(QtWidgets.QLabel("ID"), 1, 0)
        self.id_entry = QtWidgets.QLineEdit()
        self.id_entry.setFont(normal_font)
        top_layout.addWidget(self.id_entry, 1, 1)
        self.next_id_btn = QtWidgets.QPushButton("Next Free")
        self.next_id_btn.setFont(normal_font)
        self.next_id_btn.clicked.connect(self.next_free)
        top_layout.addWidget(self.next_id_btn, 1, 2)

        top_layout.addWidget(QtWidgets.QLabel("Finger"), 2, 0)
        self.finger_options = ['', 'R_Thumb','R_Index','R_Middle','R_Ring','R_Little','L_Thumb','L_Index','L_Middle','L_Ring','L_Little']
        self.finger_cb = QtWidgets.QComboBox()
        self.finger_cb.addItems(self.finger_options)
        self.finger_cb.setFont(normal_font)
        top_layout.addWidget(self.finger_cb, 2, 1)
        self.next_finger_btn = QtWidgets.QPushButton("Next Finger")
        self.next_finger_btn.setFont(normal_font)
        self.next_finger_btn.clicked.connect(self.next_finger)
        top_layout.addWidget(self.next_finger_btn, 2, 2)

        self.duplicate_cb = QtWidgets.QCheckBox("Allow duplicate finger pictures")
        self.duplicate_cb.setFont(normal_font)
        top_layout.addWidget(self.duplicate_cb, 3, 0, 1, 2)

        layout.addWidget(top_widget)

        # Middle: Camera preview + processed image
        self.middle_widget = QtWidgets.QWidget()
        mid_layout = QtWidgets.QHBoxLayout(self.middle_widget)

        # camera preview label
        self.camera_label = QtWidgets.QLabel()
        self.camera_label.setFixedSize( int(self.width() * 0.37), int(self.height() * 0.44) )
        self.camera_label.setStyleSheet("background-color: #222;")
        self.camera_label.setAlignment(QtCore.Qt.AlignCenter)
        mid_layout.addWidget(self.camera_label)

        # processed image label
        self.image_label = QtWidgets.QLabel()
        self.image_label.setFixedSize( int(self.width() * 0.37), int(self.height() * 0.44) )
        self.image_label.setStyleSheet("background-color: #111;")
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        mid_layout.addWidget(self.image_label)

        layout.addWidget(self.middle_widget)

        bottom = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QHBoxLayout(bottom)

        self.capture_btn = QtWidgets.QPushButton("Capture")
        big_font = QtGui.QFont("Arial", 20, QtGui.QFont.Bold)
        self.capture_btn.setFont(big_font)
        self.capture_btn.clicked.connect(lambda: self.task_queue.put('take_photo'))
        bottom_layout.addWidget(self.capture_btn)

        self.metric_label = QtWidgets.QLabel("")
        self.metric_label.setFont(big_font)
        self.metric_label.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(self.metric_label)

        layout.addWidget(bottom)

    #* ---------------- RemBg ----------------
    def initialize_rembg(self):
        u2net_path = resource_path('.u2net')
        os.environ["U2NET_HOME"] = u2net_path
        try:
            self.rembg_session = new_session("u2netp")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "rembg init failed", f"rembg session init failed: {e}")
            self.rembg_session = None

    #* ---------------- Camera frame handler ----------------
    @QtCore.pyqtSlot(object)
    def _on_frame(self, frame_bgr):
        with self.frame_lock:
            self.latest_frame = frame_bgr.copy()

    def update_preview_label(self):
        #? display latest_frame on camera_label
        frame = None
        with self.frame_lock:
            if self.latest_frame is not None:
                frame = self.latest_frame.copy()
        if frame is not None:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            scaled = qimg.scaled(self.camera_label.size(), QtCore.Qt.KeepAspectRatio)
            pix = QtGui.QPixmap.fromImage(scaled)
            self.camera_label.setPixmap(pix)

    #* ---------------- Task worker ----------------
    def _task_worker(self):
        while self.worker_running:
            try:
                task = self.task_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if task == 'take_photo':
                #? run take_photo in a separate thread to avoid blocking this worker loop
                try:
                    self.capture_btn.setEnabled(False)
                    t = threading.Thread(target=self.take_photo, daemon=True)
                    t.start()
                    t.join()
                finally:
                    self.capture_btn.setEnabled(True)
            self.task_queue.task_done()

    #* ---------------- Take Photo / Processing ----------------
    def take_photo(self):
        # self.camera_thread.pause_preview()

        #? grab latest frame
        with self.frame_lock:
            frame = self.latest_frame.copy() if self.latest_frame is not None else None

        if frame is None:
            QtWidgets.QMessageBox.critical(self, "Error", "Could not capture frame from camera.")
            self.camera_thread.resume_preview()
            return

        # self.camera_thread.resume_preview()


        name = self.name_entry.text()
        id_str = str(self.id_entry.text()).strip() or "0"
        finger = str(self.finger_cb.currentText())
        os.makedirs(os.path.join(DATA_FILEPATH, id_str), exist_ok=True)
        os.makedirs(os.path.join(DATA_FILEPATH, id_str, 'Real'), exist_ok=True)
        os.makedirs(os.path.join(DATA_FILEPATH, id_str, 'NFIQ'), exist_ok=True)
        os.makedirs(os.path.join(DATA_FILEPATH, id_str, 'Raw'), exist_ok=True)

        self.duplicate = bool(self.duplicate_cb.isChecked())
        if self.duplicate:
            self.duplicate_number = 0
            for fname in os.listdir(os.path.join(DATA_FILEPATH, id_str, 'Real')):
                if f"{id_str}_{finger}" in fname:
                    self.duplicate_number += 1
            self.duplicate_number = str(self.duplicate_number)

        #? Save Raw (original cropped frame is BGR)
        raw_path = os.path.join(DATA_FILEPATH, id_str, 'Raw', f"{id_str}_{finger}_Raw")
        if self.duplicate:
            raw_path = raw_path + "_" + self.duplicate_number + FILE_EXTENSION
        else:
            raw_path = raw_path + FILE_EXTENSION
        cv2.imwrite(raw_path, frame)

        try:
            #? convert BGR->RGB for rembg which expects RGB-like input
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if self.rembg_session:
                bg_removed = remove(rgb, session=self.rembg_session)
            else:
                bg_removed = rgb
        except Exception as e:
            QtWidgets.QMessageBox.information(self, "Remove Background Failed", f"Remove Background Failed: {e}")
            bg_removed = rgb

        grayscaled = cv2.cvtColor(bg_removed, cv2.COLOR_RGB2GRAY)
        grayscaled = cv2.GaussianBlur(grayscaled, (3,3), 1)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(15,15))
        cl1 = clahe.apply(grayscaled)
        _, threshold = cv2.threshold(cl1, thresh=100, maxval=255, type=cv2.THRESH_TOZERO)
        inverted = cv2.bitwise_not(threshold)

        #? save resized 640x640 for NFIQ
        resized = cv2.resize(inverted, (640, 640))

        #? Save Real and NFIQ files
        real_fname = f"{id_str}_{finger}"
        if self.duplicate:
            real_fname += f"_{self.duplicate_number}"
        real_path = os.path.join(DATA_FILEPATH, id_str, 'Real', real_fname + FILE_EXTENSION)
        nfiq_path = os.path.join(DATA_FILEPATH, id_str, 'NFIQ', f"{id_str}_{finger}_NFIQ")
        if self.duplicate:
            nfiq_path += f"_{self.duplicate_number}"
        nfiq_path += FILE_EXTENSION

        cv2.imwrite(real_path, resized)
        cv2.imwrite(nfiq_path, resized)

        #! set 500 DPI by using PIL if needed
        try:
            img = Image.open(real_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(real_path, dpi=(500,500))
        except Exception:
            pass

        # Show processed image in GUI (converted to QPixmap)
        qimg = QtGui.QImage(resized.data, resized.shape[1], resized.shape[0], resized.shape[1], QtGui.QImage.Format_Grayscale8)
        scaled = qimg.scaled(self.image_label.size(), QtCore.Qt.KeepAspectRatio)
        pix = QtGui.QPixmap.fromImage(scaled)
        self.image_label.setPixmap(pix)

        #? Run NFIQ2 if available
        nfiq2_score = 'na'
        # nfiq2_path = "C:\\Program Files\\NFIQ 2\\bin\\nfiq2.exe"
        nfiq2_path = resource_path("./NFIQ 2/bin/nfiq2.exe")
        # print(nfiq2_path)
        image_for_nfiq = real_path
        if os.path.exists(nfiq2_path):
            try:
                result = subprocess.run([nfiq2_path, image_for_nfiq], 
                                        input='y', 
                                        capture_output=True,
                                        text=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW )
                if 'Error' not in result.stdout:
                    out = result.stdout.strip()
                    nfiq2_score = out[-2:]
                    self.metric_label.setText(f'NFIQ2 SCORE: {nfiq2_score}')
                else:
                    self.metric_label.setText('NFIQ2 SCORE: ERROR')
            except Exception:
                self.metric_label.setText('NFIQ2 SCORE: ERROR')
        else:
            self.metric_label.setText('NFIQ2 Not Installed/Not Found')

        #? Log to CSV
        logfile_exists = os.path.exists(LOG_FILEPATH)
        os.makedirs(os.path.dirname(LOG_FILEPATH), exist_ok=True)
        with open(LOG_FILEPATH, 'a', newline='') as csvfile:
            if not logfile_exists:
                csvfile.write('date,name,id,finger,nfiq\n')
            csvfile.write(f'{datetime.datetime.now()},{name},{id_str},{finger},{str(nfiq2_score).strip()}\n')

        #? reset duplicate flag
        self.duplicate = False
        self.duplicate_cb.setChecked(False)

    #! ---------------- Utility functions ----------------
    def next_free(self):
        id_count = 0
        if os.path.exists(DATA_FILEPATH):
            for _, subfolders, __ in os.walk(DATA_FILEPATH):
                if subfolders != []:
                    id_count += len(subfolders)
        self.id_entry.setText(str(id_count))

    def next_finger(self):
        cur = self.finger_cb.currentIndex()
        nxt = 0 if cur == (len(self.finger_options) - 1) else cur + 1
        self.finger_cb.setCurrentIndex(nxt)

    #! ---------------- Close / cleanup ----------------
    def closeEvent(self, ev):
        self.worker_running = False
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
            except queue.Empty:
                break
        if hasattr(self, "camera_thread") and self.camera_thread.isRunning():
            self.camera_thread.stop()
        if hasattr(self, "worker_thread") and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
        for t in threading.enumerate():
            if t is not threading.current_thread():
                try:
                    t.join(timeout=0.5)
                except Exception:
                    pass

        print("All threads stopped. Closing application cleanly.")
        ev.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    os.makedirs(DATA_FILEPATH, exist_ok=True)
    splash_pixmap = QPixmap(resource_path("./assets/splash.png"))    
    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    win = MainWindow()
    splash.show()
    splash.showMessage("Loading modules...", Qt.AlignCenter, Qt.black)
    win.show()
    splash.finish(win)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
