"""
Configuration File
All system parameters in one place
"""

import os
from pathlib import Path

# ============ PATHS ============
PROJECT_ROOT = Path(__file__).parent
DATABASE_PATH = PROJECT_ROOT / "students.db"
ENROLLMENT_FOLDER = PROJECT_ROOT / "enrolled_students"
OUTPUT_VIDEOS = PROJECT_ROOT / "output_videos"

# Create directories if they don't exist
ENROLLMENT_FOLDER.mkdir(exist_ok=True)
OUTPUT_VIDEOS.mkdir(exist_ok=True)

# ============ ARCFACE MODEL ============
ARCFACE_MODEL = "buffalo_l"  # Optimal for face recognition
GPU_CONTEXT = 0  # 0 = GPU, -1 = CPU
EMBEDDING_DIM = 512  # ArcFace output dimension

# ============ FACE DETECTION ============
FACE_DETECTION_SIZE = (640, 640)  # Input size for detection model
MIN_FACE_SIZE = 20  # Minimum face width in pixels

# ============ IMAGE QUALITY ============
MIN_SHARPNESS = 40.0  # Minimum Laplacian variance (blur detection)
MIN_BRIGHTNESS = 30.0  # Minimum average brightness
CLAHE_CLIP_LIMIT = 2.0  # Contrast Limited Adaptive Histogram Equalization

# ============ ENROLLMENT ============
ENROLLMENT_IMAGE_SIZE = (112, 112)  # Aligned face size
ENROLLMENT_QUALITY_THRESHOLD = 0.7  # Quality score for webcam enrollment

# ============ ATTENDANCE DETECTION ============
SIMILARITY_THRESHOLD = 0.35  # Cosine similarity threshold for match
# Threshold Guide:
#   0.25 = Very strict (fewer false positives)
#   0.35 = Balanced (recommended)
#   0.45 = Permissive (more false positives)

DUPLICATE_LOG_THRESHOLD = 5  # Seconds - avoid logging same person twice

# ============ VIDEO SETTINGS ============
CAMERA_INDEX = 0  # Default camera device
VIDEO_FPS = 30
VIDEO_CODEC = "mp4v"  # Video codec for output

# ============ DATABASE ============
DB_TYPE = "sqlite"  # "sqlite" (local) or "mysql" (future)
DB_TIMEOUT = 10  # Connection timeout in seconds

# ============ LOGGING ============
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = PROJECT_ROOT / "system.log"

# ============ DISPLAY ============
DISPLAY_FACE_BOX = True
DISPLAY_CONFIDENCE = True
DISPLAY_STATS = True
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# ============ ADVANCED ============
BATCH_PROCESSING_SIZE = 32  # For bulk operations
CACHE_ENROLLMENTS = True  # Keep enrollments in memory
MAX_DETECTION_FACES = 10  # Maximum faces to detect per frame

# ============ EMAIL NOTIFICATIONS (Future) ============
SEND_EMAIL_ALERTS = False
EMAIL_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_SENDER = "attendance@school.edu"

# ============ WEB INTERFACE (Future) ============
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 5000
WEB_DEBUG = False
