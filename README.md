# Smart Attendance

A web-based attendance system that uses real-time face recognition to automatically mark attendance via webcam.

## How it works

1. **Register** a student — capture 10+ webcam frames to build their face profile.
2. **Train** — the backend extracts ArcFace embeddings from each captured frame and trains an SVM classifier.
3. **Recognize** — on the attendance page, the webcam stream is processed through a YOLOv8 face detector, then an ArcFace embedding is matched against the trained SVM to identify the student and log attendance.

### ML pipeline

| Stage | Model |
|---|---|
| Face detection | YOLOv8n-face (YOLO-face community) |
| Embedding | InsightFace `buffalo_sc` (ArcFace, 512-d) |
| Classification | Scikit-learn SVM (RBF kernel) |

The SVM model is persisted to `svm_model.pkl` and reloaded on each recognition request. For a single enrolled user, a cosine-similarity threshold is used instead of SVM.

## Tech stack

- **Backend** — Flask, Flask-JWT-Extended, Flask-SQLAlchemy (SQLite)
- **Face ML** — InsightFace, Ultralytics YOLOv8, OpenCV, scikit-learn
- **Frontend** — Vanilla JS + HTML/CSS, webcam via `getUserMedia`

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

The app will be available at `http://localhost:5001`.

On first run the YOLOv8 face model (`yolov8n-face.pt`) is downloaded automatically (~6 MB). The InsightFace `buffalo_sc` model pack is downloaded on first recognition request.

## Project structure

```
smart-attendance/
├── app.py              # Flask app & route registration
├── models.py           # SQLAlchemy models (User, FaceCapture, Attendance)
├── face_utils.py       # ML pipeline: YOLO gate → ArcFace embed → SVM predict
├── config.py           # App configuration
├── requirements.txt
├── routes/
│   ├── auth.py         # JWT login/logout
│   ├── users.py        # User CRUD
│   ├── attendance.py   # Attendance log endpoints
│   ├── recognition.py  # Real-time recognition endpoint
│   └── training.py     # Trigger SVM retrain
├── templates/          # Jinja2 HTML pages
└── static/             # CSS & JS
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | JWT login |
| GET/POST | `/api/users` | List / create users |
| POST | `/api/recognize` | Identify face from webcam frame |
| POST | `/api/training/retrain` | Retrain SVM from DB |
| GET | `/api/attendance` | List attendance records |
