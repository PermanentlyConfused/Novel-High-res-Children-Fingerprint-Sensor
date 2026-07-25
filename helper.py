def resource_path(relative_path):
    from os import path

    #Handles pathing if app is launched as pyinstaller exe or script
    try: 
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")
    return path.join(base_path, relative_path)

def find_arducam_index() -> int | None:
    try:
        from cv2_enumerate_cameras import enumerate_cameras
        import cv2
    except Exception:
        return None
    for camera_info in enumerate_cameras(cv2.CAP_DSHOW):
        if camera_info.name == "Arducam IMX477 HQ Camera":
            return camera_info.index
    return None