from rest_framework import serializers
from backend.core.models import Student, Embedding, Attendance   # 🔎 importer les vrais modèles
from django.utils import timezone


# ==============================
# STUDENT SERIALIZER
# ==============================
class StudentSerializer(serializers.ModelSerializer):
    """Serializer for Student model"""

    class Meta:
        model = Student   # 🔎 utiliser la classe, pas une string
        fields = [
            "student_id",
            "name",
            "email",
            "level",      
            "filiere",
            "enrollment_date",
            "active",
            "photo_path"   # ✅ virgule corrigée
        ]
        read_only_fields = ["student_id", "enrollment_date", "photo_path"]


# ==============================
# EMBEDDING SERIALIZER
# ==============================
class EmbeddingSerializer(serializers.ModelSerializer):
    """Serializer for Embedding model"""

    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = Embedding
        fields = [
            "embedding_id",
            "student_name",
            "enrollment_photo_path",
            "created_date",
            "quality_metrics"
        ]
        read_only_fields = ["embedding_id", "created_date"]


# ==============================
# ATTENDANCE SERIALIZER
# ==============================
class AttendanceSerializer(serializers.ModelSerializer):
    """Safe serializer for Attendance (frontend friendly types)"""
   
    attendance_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    confidence = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()

    matched_embedding_id = serializers.IntegerField(
        source="matched_embedding.embedding_id",
        read_only=True,
        allow_null=True
    )
       
    photo_path = serializers.CharField(
        source="matched_embedding.enrollment_photo_path",
        read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            "attendance_id",
            "student_id",
            "student_name",
            "timestamp",
            "confidence",
            "matched_embedding_id",
            "photo_path"   # ✅ virgule corrigée
        ]


    def get_attendance_id(self, obj):
        try:
            return int(obj.id)
        except Exception:
            return 0

    def get_student_name(self, obj):
        try:
            if obj.student and obj.student.name:
                return str(obj.student.name).strip()
        except Exception:
            pass
        return "Unknown"

    def get_student_id(self, obj):
        try:
            if obj.student and hasattr(obj.student, 'student_id'):
                return int(obj.student.student_id)
        except Exception:
            pass
        return 0
    
    def get_timestamp(self, obj):
        try:
            if obj.timestamp:
                local_time = timezone.localtime(obj.timestamp)
                return local_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return None
    
    def get_confidence(self, obj):
        try:
            if obj.confidence is not None:
                value = float(obj.confidence)
                return max(0.0, min(1.0, value))
        except Exception:
            pass
        return 0.0
