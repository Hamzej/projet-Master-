# 🎓 Smart Attendance System - Face Recognition

Complete system for student enrollment and real-time attendance detection using ArcFace deep learning.

## 📋 Project Structure

```
face_recognition_system/
├── core/
│   ├── face_processor.py      # ArcFace model, detection, alignment, embedding
│   ├── database.py            # SQLite database for students & embeddings
│   ├── enrollment.py          # Student registration (image/camera)
│   └── attendance.py          # Real-time face recognition & logging
├── main.py                    # Interactive menu and demo
├── requirements.txt           # Python dependencies
└── students.db               # SQLite database (created automatically)
```

## 🚀 Installation

### 1. Install Python 3.8+

```bash
python --version
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install CUDA (Optional but recommended for GPU)

For GPU acceleration:
```bash
# NVIDIA CUDA Toolkit 11.8+
# cuDNN 8.6+
```

## 📖 Usage

### Quick Start

```bash
python main.py
```

Interactive menu will guide you through:
1. **Enroll Students** - Register new students with photos
2. **Real-time Detection** - Start attendance tracking from webcam
3. **View Statistics** - Check enrollment and attendance data

---

## 🔧 Core Modules

### 1. FaceProcessor (`face_processor.py`)

Handles face detection and embedding extraction using ArcFace.

```python
from core.face_processor import FaceProcessor

# Initialize
processor = FaceProcessor(model_name="buffalo_l")

# Detect faces in image
faces = processor.detect_faces(image)

# Full pipeline: detect → align → embed
success, aligned_face, embedding = processor.process_image("photo.jpg")

# Process video frames
results = processor.process_frame(video_frame)  # Returns list of embeddings
```

**Key Features:**
- ✅ Face detection (SCRFD)
- ✅ Facial alignment (eye-based rotation)
- ✅ ArcFace embedding extraction (512-dim vectors)
- ✅ L2 normalization
- ✅ Image quality assessment

---

### 2. StudentDatabase (`database.py`)

SQLite database for managing students and embeddings.

```python
from core.database import StudentDatabase

# Initialize
db = StudentDatabase("students.db")

# Add student
student_id = db.add_student("Ahmed Al-Mansouri", "ahmed@school.edu")

# Store embedding
embedding_id = db.add_embedding(
    student_id=student_id,
    embedding=embedding_vector,
    photo_path="enrolled_students/photo.jpg",
    quality_metrics={...}
)

# Log attendance
db.log_attendance(student_id, confidence=0.95)

# Get statistics
stats = db.get_db_stats()
```

**Database Schema:**
- `students` - Student registry
- `embeddings` - Face embeddings (512-dim vectors stored as BLOB)
- `attendance` - Attendance log with timestamps
- Indexes for fast queries

---

### 3. EnrollmentSystem (`enrollment.py`)

Interactive student enrollment.

```python
from core.enrollment import EnrollmentSystem

enrollment = EnrollmentSystem(processor, db)

# From image file
success, student_id = enrollment.enroll_from_image(
    name="Ahmed Al-Mansouri",
    image_path="photo.jpg",
    email="ahmed@school.edu"
)

# From webcam (interactive)
success, student_id = enrollment.enroll_from_camera(
    name="Ahmed Al-Mansouri",
    email="ahmed@school.edu"
)

# Bulk enroll from folder structure
enrolled, failed = enrollment.bulk_enroll_from_folder("students_folder/")
```

**Folder Structure for Bulk Enroll:**
```
students_folder/
├── Ahmed Al-Mansouri/
│   └── photo.jpg
├── Fatima Al-Zahra/
│   ├── photo1.jpg
│   └── photo2.jpg
└── Muhammad Hassan/
    └── enrollment.jpg
```

---

### 4. AttendanceDetector (`attendance.py`)

Real-time face recognition and attendance logging.

```python
from core.attendance import AttendanceDetector

detector = AttendanceDetector(processor, db, similarity_threshold=0.35)

# Real-time video stream
detector.process_video_stream(camera_index=0, output_video="attendance.mp4")

# Batch process images
detector.process_image_batch(["img1.jpg", "img2.jpg"])

# Manual matching
student_id, confidence, _ = detector.find_match(embedding)
```

**Real-time Controls:**
- `R` - Reload enrollments
- `S` - Show statistics
- `Q`/`ESC` - Quit

---

## 💡 Technical Details

### ArcFace Embeddings

- **Dimension:** 512-dimensional vector
- **Normalized:** L2 normalization (unit length)
- **Similarity Metric:** Cosine similarity (dot product)
- **Threshold:** 0.35 (balanced for high accuracy)

### Model Performance (on FERET dataset)

- **AUC:** 0.99
- **EER:** < 1%
- **Rank-1 Accuracy:** > 99%
- **Same Person Similarity:** 0.65
- **Different Person Similarity:** 0.016

### Distance/Similarity Scale

```
-1.0 ──────── 0.0 ──── 0.35 (threshold) ──── 0.65 ──── 1.0
 ↑           ↑                             ↑
complete   unrelated                   same person
opposite
```

---

## 📊 Database Usage

### Check Database Size

```python
from core.database import StudentDatabase

db = StudentDatabase()
stats = db.get_db_stats()

print(f"Students: {stats['active_students']}")
print(f"Embeddings: {stats['total_embeddings']}")
print(f"Size: {stats['database_size_mb']:.2f} MB")
```

### View Attendance Log

```python
# Today's attendance
attendance = db.get_attendance_today()

for record in attendance:
    print(f"{record['name']} - {record['timestamp']}")

# Student statistics
stats = db.get_attendance_stats(student_id=1, days=30)
```

### Clear Database (For Testing)

⚠️ **WARNING: This deletes all data**

```python
db.clear_all_data()
```

---

## 🎥 Real-Time Attendance

### Start Detection

```bash
python main.py
# Select option 4 (Real-time attendance)
```

### Settings

Edit similarity threshold in `attendance.py`:

```python
detector = AttendanceDetector(
    face_processor=face_processor,
    database=database,
    similarity_threshold=0.35  # Adjust as needed
)
```

**Threshold Guidelines:**
- **0.25:** Very strict (fewest false positives)
- **0.35:** Balanced (recommended)
- **0.45:** Permissive (more false positives)

---

## ⚙️ GPU vs CPU

### Auto-detection

The system automatically uses GPU if CUDA is available.

### Force CPU

```python
processor = FaceProcessor(ctx_id=-1)  # -1 = CPU, 0 = GPU
```

### Performance

| Device | Speed | Memory |
|--------|-------|--------|
| GPU (NVIDIA) | ~50 FPS | ~2GB |
| GPU (RTX) | ~100+ FPS | ~3GB |
| CPU | ~5-10 FPS | ~1GB |

---

## 🐛 Troubleshooting

### Camera not detected
```bash
# Check available cameras
python -c "import cv2; cap = cv2.VideoCapture(0); print(cap.isOpened())"
```

### CUDA/GPU issues
```bash
# Use CPU only
# Edit face_processor.py: ctx_id=-1
```

### Database locked error
```python
# Close all connections and delete lock files
rm students.db-shm students.db-wal
```

### Low recognition accuracy
- Ensure good lighting during enrollment
- Center face in frame
- Use high-quality photos (≥ 112x112)
- Check similarity threshold

---

## 📝 Example: Complete Workflow

```python
from core.face_processor import FaceProcessor
from core.database import StudentDatabase
from core.enrollment import EnrollmentSystem
from core.attendance import AttendanceDetector

# 1. Initialize
processor = FaceProcessor()
db = StudentDatabase()
enrollment = EnrollmentSystem(processor, db)
detector = AttendanceDetector(processor, db)

# 2. Enroll students from folder
enrollment.bulk_enroll_from_folder("student_photos/")

# 3. Check enrollment
stats = db.get_db_stats()
print(f"Enrolled: {stats['active_students']} students")

# 4. Start attendance detection
detector.process_video_stream(camera_index=0)

# 5. View attendance
attendance = db.get_attendance_today()
print(f"Present today: {len(attendance)} students")
```

---

## 📚 References

- **ArcFace**: https://arxiv.org/abs/1801.07698
- **InsightFace**: https://github.com/deepinsight/insightface
- **OpenCV**: https://docs.opencv.org/

---

## 📄 License

This project is for educational purposes.

---

## 👨‍💻 Author

Master's Project - Smart Attendance System
University: [Your University]
Date: 2024

---

## 🤝 Support

For issues or questions, check the logs in `console output`.

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # Enable debug logging
```

---

**Last Updated:** 2024
**Version:** 1.0.0 (Beta)
