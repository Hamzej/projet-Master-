from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
import base64
import numpy as np

from .models import Student, Embedding, Attendance


class StudentModelTest(TestCase):
    """Tests unitaires pour le modèle Student"""

    def test_create_student(self):
        student = Student.objects.create(name="Test Student", email="test@example.com")
        self.assertEqual(student.name, "Test Student")
        self.assertTrue(student.active)


class EmbeddingModelTest(TestCase):
    """Tests unitaires pour le modèle Embedding"""

    def test_create_embedding(self):
        student = Student.objects.create(name="Test Student")
        emb = np.random.randn(512).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        embedding_bytes = emb.tobytes()

        embedding = Embedding.objects.create(student=student, embedding=embedding_bytes)
        self.assertEqual(embedding.student.name, "Test Student")


class AttendanceModelTest(TestCase):
    """Tests unitaires pour le modèle Attendance"""

    def test_log_attendance(self):
        student = Student.objects.create(name="Test Student")
        attendance = Attendance.objects.create(student=student, confidence=0.95)
        self.assertEqual(attendance.student.name, "Test Student")
        self.assertAlmostEqual(attendance.confidence, 0.95)


class APITest(TestCase):
    """Tests API REST"""

    def setUp(self):
        self.client = APIClient()
        self.student = Student.objects.create(name="API Student", email="api@example.com")

        # Créer un embedding factice
        emb = np.random.randn(512).astype(np.float32)
        emb = emb / np.linalg.norm(emb)
        self.embedding_bytes = emb.tobytes()
        self.embedding_b64 = base64.b64encode(self.embedding_bytes).decode("utf-8")

    def test_enroll_student(self):
        url = f"/api/students/{self.student.id}/enroll/"
        response = self.client.post(url, {
            "photo_path": "photo.jpg",
            "embedding": self.embedding_b64,
            "quality_metrics": {"sharpness": 50, "brightness": 40}
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("embedding_id", response.data)

    def test_recognize_attendance(self):
        # Enrôler d'abord
        Embedding.objects.create(student=self.student, embedding=self.embedding_bytes)

        url = "/api/attendance/recognize/"
        response = self.client.post(url, {
            "embedding": self.embedding_b64
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("student", response.data)

    def test_stats(self):
        url = "/api/attendance/stats/"
        response = self.client.get(url, {"date": "2026-04-23"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("active_students", response.data)
