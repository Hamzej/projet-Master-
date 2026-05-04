"""
Smart Attendance System - Face Recognition Module
Complete system for student enrollment and real-time attendance detection
using ArcFace deep learning and SQLite database.

Version: 1.0.0 (Beta)
"""

from .pipeline.face_processor import FaceProcessor, ImageQuality
from .pipeline.database import StudentDatabase
from .pipeline.enrollment import EnrollmentSystem
from .pipeline.attendance import AttendanceDetector

__version__ = "1.0.0"
__author__ = "Your Name"
__all__ = [
    "FaceProcessor",
    "ImageQuality",
    "StudentDatabase",
    "EnrollmentSystem",
    "AttendanceDetector",
]
