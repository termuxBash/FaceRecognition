#!/usr/bin/env python3
import os
import cv2
import face_recognition
import time

KNOWN_FACES_DIR = "known_faces"
TOLERANCE = 0.6
MODEL = "hog"
TIMEOUT = 10  # seconds

def load_known_faces(known_faces_dir):
    faces, names = [], []
    for name in os.listdir(known_faces_dir):
        for filename in os.listdir(f"{known_faces_dir}/{name}"):
            img = face_recognition.load_image_file(f"{known_faces_dir}/{name}/{filename}")
            enc = face_recognition.face_encodings(img)
            if enc:
                faces.append(enc[0])
                names.append(name)
    return faces, names

def verify(timeout=TIMEOUT):
    faces, names = load_known_faces(KNOWN_FACES_DIR)
    video = cv2.VideoCapture(0)
    start = time.time()
    cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)

    # Get screen size and set window to 50%
    screen_width = 800
    screen_height = 600
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except Exception:
        pass
    win_width = int(screen_width * 0.5)
    win_height = int(screen_height * 0.5)
    cv2.resizeWindow("Face Recognition", win_width, win_height)

    result = False
    matched_name = None
    while True:
        ret, img = video.read()
        if not ret:
            break
        small = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
        locs = face_recognition.face_locations(small, model=MODEL)
        encs = face_recognition.face_encodings(small, locs)
        for enc, loc in zip(encs, locs):
            matches = face_recognition.compare_faces(faces, enc, TOLERANCE)
            if True in matches:
                idx = matches.index(True)
                matched_name = names[idx]
                result = True
                break
        # Draw skip button (supports [s] and [space])
        btn_text = "Skip [s] or [space]"
        btn_color = (50, 50, 255)
        btn_pos = (10, 30)
        cv2.rectangle(img, (5, 5), (250, 40), btn_color, -1)
        cv2.putText(img, btn_text, btn_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        cv2.imshow("Face Recognition", img)
        key = cv2.waitKey(1) & 0xFF
        if result:
            video.release()
            cv2.destroyAllWindows()
            return True, matched_name, "matched"
        if time.time() - start > timeout:
            video.release()
            cv2.destroyAllWindows()
            return False, None, "timeout"
        if key == ord('s') or key == 32:  # 32 is space
            video.release()
            cv2.destroyAllWindows()
            return False, None, "skipped"
    video.release()
    cv2.destroyAllWindows()
    return False, None, "error"

if __name__ == "__main__":
    res, name, status = verify()
    print(res, name, status)