#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk

import cv2
import face_recognition
import os
import sys
import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # Set working directory

# ----------------------------
# Config
# ----------------------------
KNOWN_FACES_DIR = "known_faces"
TOLERANCE = 0.6
MODEL = "hog"  # or "cnn"
FOCUS_TIMEOUT_MS = 200  # Reassert focus every 200ms
DELAY_BEFORE_QUIT_MS = 1000  # Delay before quitting (ms)
SESSION_LOG_FILE = "face_unlock.log"  # Log file on disk

# ----------------------------
# Helpers
# ----------------------------
def load_known_faces(known_faces_dir, logger):
    encodings, names = [], []
    if not os.path.exists(known_faces_dir):
        logger(f"[WARN] No {known_faces_dir} directory found")
        return encodings, names

    for name in os.listdir(known_faces_dir):
        person_dir = os.path.join(known_faces_dir, name)
        if not os.path.isdir(person_dir):
            continue
        for filename in os.listdir(person_dir):
            path = os.path.join(person_dir, filename)
            try:
                image = face_recognition.load_image_file(path)
                encoding = face_recognition.face_encodings(image)
                if encoding:
                    encodings.append(encoding[0])
                    names.append(name)
                    logger(f"[INFO] Loaded {path} for {name}")
            except Exception as e:
                logger(f"[ERROR] Failed to load {path}: {e}")
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

import numpy as np
def is_frame_black(frame, threshold=15):
    """Return True if the average brightness is below threshold."""
    if frame is None:
        return True
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    return avg_brightness < threshold


# ----------------------------
# GTK Window
# ----------------------------
class FaceUnlockWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Face Unlock Authentication")
        self.matched_name = None  # Track matched user

        self.set_decorated(False)
        self.set_keep_above(True)
        
        # Attempt to set window to fullscreen
        self.fullscreen()

        # Alternatively, explicitly set window to screen size
        screen = Gdk.Screen.get_default()
        width = screen.get_width()
        height = screen.get_height()
        self.set_default_size(width, height)

        

        self.connect("destroy", self.quit_app)
        self.connect("key-press-event", self.on_key_press)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(vbox)

        self.label = Gtk.Label(label="Authenticating with face…")
        vbox.pack_start(self.label, False, False, 0)

        self.image = Gtk.Image()
        vbox.pack_start(self.image, True, True, 0)

        self.status = Gtk.Label(label="Initializing…")
        vbox.pack_start(self.status, False, False, 0)

        # Logging area
        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView(buffer=self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        log_scroller = Gtk.ScrolledWindow()
        log_scroller.set_size_request(-1, 150)
        log_scroller.add(self.log_view)
        vbox.pack_start(log_scroller, False, True, 0)

        # Load known faces
        self.known_encs, self.known_names = load_known_faces(KNOWN_FACES_DIR, lambda msg: self.log(msg, write_to_file=False))

        # Try camera indices
        self.cap = None
        for idx in (0, 1):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                self.cap = cap
                self.log(f"[INFO] Camera opened at index {idx}", write_to_file=False)
                break
            else:
                cap.release()
        if not self.cap:
            self.status.set_text("❌ No camera found")
            self.log("[ERROR] Could not open any camera")
        else:
            GLib.timeout_add(50, self.update_frame)
            GLib.timeout_add(FOCUS_TIMEOUT_MS, self.check_and_focus)

    def exit_with_code(self):
        if self.matched_name:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure

    def log(self, message, write_to_file=True):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"{timestamp} {message}"
        print(full_msg)

        # Show in GTK TextView
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, full_msg + "\n")
        adj = self.log_view.get_vadjustment()
        GLib.idle_add(adj.set_value, adj.get_upper() - adj.get_page_size())

        # Save to log file (only if allowed)
        if write_to_file:
            with open(SESSION_LOG_FILE, "a") as f:
                f.write(full_msg + "\n")


    def check_and_focus(self):
        self.present()
        return True

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_q:
            self.status.set_text("Q pressed. Quitting.")
            self.log("[INFO] User aborted authentication with 'Q' key.")
            GLib.timeout_add(300, self.quit_app)
            return True
        return True


    def quit_app(self, *args):
        self.log("[INFO] Shutting down application...", write_to_file=False)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        Gtk.main_quit()
        GLib.idle_add(self.exit_with_code) # Schedule exit after loop ends


    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            self.status.set_text("❌ Camera not available")
            return True

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.status.set_text("⚠️ No camera frame")
            return True

        # 🆕 Check for black frame
        if is_frame_black(frame):
            self.status.set_text("⚠️ Camera feed appears dark or blocked. Please check your webcam.")
            return True

        try:
            pixbuf = cv_frame_to_pixbuf(frame)
            self.image.set_from_pixbuf(pixbuf)
        except Exception as e:
            self.status.set_text(f"Frame convert error: {e}")
            return True

        # Face recognition
        small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        locs = face_recognition.face_locations(small, model=MODEL)
        encs = face_recognition.face_encodings(small, locs)

        matched_name = None
        for enc in encs:
            matches = face_recognition.compare_faces(self.known_encs, enc, TOLERANCE)
            if any(matches):
                matched_name = self.known_names[matches.index(True)]
                break

        if matched_name:
            msg = f"✅ Matched: {matched_name}, quitting…"
            self.status.set_text(msg)
            self.log(msg)
            self.log(f"[AUTH] User '{matched_name}' matched and logged in successfully.")
            self.matched_name = matched_name  # 🆕 Needed for exit code
            GLib.timeout_add(DELAY_BEFORE_QUIT_MS, self.quit_app)
            return False

        self.status.set_text("No match yet")
        return True

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    win = FaceUnlockWindow()
    win.show_all()
    Gtk.main()
