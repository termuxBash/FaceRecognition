# FaceRecognition
Face unlock for linux xfce4 desktops, doesn't need **IR sensors**, via python `face_recognition` and `opencv`.

# 🔓 Face Unlock for Linux (GTK + OpenCV + Face Recognition)

A simple facial recognition login window using Python 3, OpenCV, and GTK. Designed to run on Linux desktops with camera support.

---

## 🚀 Features

- Real-time face recognition using your webcam
- Fullscreen GTK window with logging
- Auto-exits on successful face match
- Optional dark-frame detection
- Supports multiple users/faces

---

## 📷 Requirements

- Python 3.6+
- Webcam (integrated or USB)
- GTK 3
- OpenCV
- face_recognition (uses dlib)
- numpy

Install requirements:

```bash
pip install opencv-python face_recognition numpy PyGObject
```


# ⚙️ Configuration

Edit these options at the top of face_unlock.py:

Change the `MODEL` according to your preference of hardware

MODEL = "hog"  # or "cnn"

TOLERANCE = 0.6


MODEL: "hog" is fast (CPU). "cnn" is accurate but slow (needs GPU).

TOLERANCE: Lower = stricter match (default 0.6)

Change the log file to add it in your own custom directory prefferbaly the temp or cache dir.

| Option  | Description                                                                                                                   |
| ------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `"hog"` | **Histogram of Oriented Gradients** — Fast, CPU-based face detector. Best for real-time applications or low-resource systems. |
| `"cnn"` | **Convolutional Neural Network** — More accurate but slower. Requires a CUDA-enabled GPU for performance.                     |
