"""
backend/core/models.py
Clean ORM schema aligned with MySQL + AI pipeline
"""

from django.db import models


# =========================
# STUDENT
# =========================
class Student(models.Model):
    """Student entity"""

    student_id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)

    level = models.CharField(max_length=50, null=True, blank=True)   
    filiere = models.CharField(max_length=100, null=True, blank=True) 

    enrollment_date = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "students"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["active"]),
        ]

    def __str__(self):
        return self.name or "Unknown"


# =========================
# EMBEDDING
# =========================
class Embedding(models.Model):
    """Face embedding vector"""

    embedding_id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey( Student,on_delete=models.CASCADE, related_name="embeddings" )
    embedding = models.BinaryField()
    enrollment_photo_path = models.CharField( max_length=500, null=True, blank=True)
    photo_hash = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        unique=False,
        help_text="SHA256 hash de la photo pour détecter les doublons"
    )
    quality_metrics = models.JSONField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "embeddings"
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["created_date"]),
        ]

    def __str__(self):
        return f"Embedding {self.embedding_id} - {self.student.name}"


# =========================
# ATTENDANCE
# =========================
class Attendance(models.Model):
    """Attendance tracking"""

    attendance_id = models.BigAutoField(primary_key=True)

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendances"
    )

    timestamp = models.DateTimeField()


    confidence = models.FloatField(null=True, blank=True)

    matched_embedding = models.ForeignKey(
        Embedding,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = "attendance"
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"Attendance {self.attendance_id} - {self.student.name}"

    # ==================================================
    # COMPATIBILITY LAYER (DRF + LEGACY CODE SAFETY)
    # ==================================================
    @property
    def id(self):
        """Alias for DRF compatibility"""
        return self.attendance_id