import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf

import cv2
import face_recognition
import os

# ----------------------------
# Config
# ----------------------------
KNOWN_FACES_DIR = "known_faces"
TOLERANCE = 0.6
MODEL = "hog"  # or "cnn"


# ----------------------------
# Helpers
# ----------------------------
def load_known_faces(known_faces_dir):
    encodings, names = [], []
    if not os.path.exists(known_faces_dir):
        print(f"[WARN] No {known_faces_dir} directory found")
        return encodings, names

    for name in os.listdir(known_faces_dir):
        person_dir = os.path.join(known_faces_dir, name)
        if not os.path.isdir(person_dir):
            continue
        for filename in os.listdir(person_dir):
            path = os.path.join(person_dir, filename)
            try:
                image = face_recognition.load_image_file(path)
                encoding = face_recognition.face_encodings(image)[0]
                encodings.append(encoding)
                names.append(name)
                print(f"[INFO] Loaded {path} for {name}")
            except Exception as e:
                print(f"[ERROR] Failed to load {path}: {e}")
    return encodings, names


def cv_frame_to_pixbuf(frame_bgr):
    """Convert OpenCV BGR numpy array -> GdkPixbuf for Gtk.Image."""
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w, c = frame_rgb.shape
    rowstride = w * c
    return GdkPixbuf.Pixbuf.new_from_data(
        frame_rgb.tobytes(),
        GdkPixbuf.Colorspace.RGB,
        False,
        8,
        w,
        h,
        rowstride,
    )


# ----------------------------
# GTK Window
# ----------------------------
class FaceGreeter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Face Recognition Greeter")
        self.set_default_size(800, 600)
        self.connect("destroy", Gtk.main_quit)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(vbox)

        self.label = Gtk.Label(label="Look at the camera…")
        vbox.pack_start(self.label, False, False, 0)

        self.image = Gtk.Image()
        vbox.pack_start(self.image, True, True, 0)

        self.status = Gtk.Label(label="Initializing…")
        vbox.pack_start(self.status, False, False, 0)

        quit_btn = Gtk.Button(label="Quit")
        quit_btn.connect("clicked", lambda *_: Gtk.main_quit())
        vbox.pack_start(quit_btn, False, False, 0)

        # Load faces
        self.known_encs, self.known_names = load_known_faces(KNOWN_FACES_DIR)

        # Camera (try 0, then 1)
        self.cap = None
        for idx in (0, 1):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                self.cap = cap
                print(f"[INFO] Camera opened at index {idx}")
                break
            else:
                cap.release()
        if not self.cap:
            self.status.set_text("❌ No camera found")
            print("[ERROR] Could not open any camera")
        else:
            GLib.timeout_add(50, self.update_frame)  # ~20 FPS

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            self.status.set_text("❌ Camera not available")
            return True

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.status.set_text("⚠️ No camera frame")
            print("[WARN] No frame from camera")
            return True

        # Show frame
        try:
            pixbuf = cv_frame_to_pixbuf(frame)
            self.image.set_from_pixbuf(pixbuf)
        except Exception as e:
            self.status.set_text(f"Frame convert error: {e}")
            return True

        # Do recognition (scale down for speed)
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        locs = face_recognition.face_locations(small, model=MODEL)
        encs = face_recognition.face_encodings(small, locs)

        matched_name = None
        for enc in encs:
            matches = face_recognition.compare_faces(
                self.known_encs, enc, TOLERANCE
            )
            if True in matches:
                matched_name = self.known_names[matches.index(True)]
                break

        if matched_name:
            msg = f"✅ Matched: {matched_name}, quitting…"
            print(msg)
            self.status.set_text(msg)
            # release & quit
            self.cap.release()
            Gtk.main_quit()
            return False

        self.status.set_text("No match yet")
        return True


if __name__ == "__main__":
    win = FaceGreeter()
    win.show_all()
    Gtk.main()
