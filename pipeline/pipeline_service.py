"""
pipeline_service.py - VERSION FINALE PRODUCTION STABLE
✔ Singleton safe
✔ Lazy loading optimisé
✔ Factorisation dépendances
✔ Health check intégré
✔ Thread-safe léger (verrou simple)
"""

import logging
import numpy as np
from pathlib import Path
import sys
import io
import threading
from typing import Optional, Tuple, List, Dict
from pipeline.pipeline_extensions import (
    validate_embedding,
    decode_image_robust,
    log_step,
    log_error
)
from insightface.app import FaceAnalysis
from django.db.models import Avg, Max, Min
from backend.core.models import Attendance
from django.utils import timezone
from django.db.models.functions import TruncDate

from datetime import datetime, time
from django.utils.timezone import make_aware
from django.db.models import Avg, Max, Min
from django.utils.timezone import now



# ✅ Préchargement du modèle au démarrage
face_processor = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
face_processor.prepare(ctx_id=0, det_size=(640, 640))

def get_pipeline_service():
    return face_processor



def to_numpy_embedding(blob):
    """
    Convertit un BLOB MySQL en vecteur numpy float32.
    """
    if isinstance(blob, (bytes, bytearray)):
        # ✅ Cas normal : BLOB → float32
        return np.frombuffer(blob, dtype=np.float32)
    elif isinstance(blob, str):
        # ⚠️ Cas rare : si l'embedding est stocké en texte (JSON ou liste)
        return np.array(eval(blob), dtype=np.float32)
    else:
        raise ValueError(f"Type inattendu pour embedding: {type(blob)}")


# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Orchestrateur central du système :
    FaceProcessor + EnrollmentSystem + AttendanceDetector + MySQL
    """

    _instance = None
    _lock = threading.Lock()
    _base_path = Path(__file__).parent.parent / "pipeline"

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:   # double-check locking
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._modules = {}
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info(" PipelineService initialisé (FINAL VERSION)")
        self._initialized = True

        if str(self._base_path) not in sys.path:
            sys.path.insert(0, str(self._base_path))

    def process_image(self, image_path: str):
        try:
            fp = self.face_processor()
            success, _, emb = fp.process_image(image_path)

            if not success or not validate_embedding(emb):
                log_error("PROCESS_IMAGE", "Embedding invalide")
                return None

            log_step("PROCESS_IMAGE", "Embedding valide")
            return emb
        except Exception as e:
            log_error("PROCESS_IMAGE", f"Erreur: {e}")
            return None

    # ==================== CORE LOADER ====================
    def _load(self, key: str, factory):
        if key in self._modules:
            return self._modules[key]

        try:
            instance = factory()
            self._modules[key] = instance
            logger.info(f" Loaded: {key}")
            return instance
        except Exception as e:
            logger.error(f" Load failed {key}: {e}")
            raise
    #""""""""""""""""""""""""""""""""""""""""""""""""
    def get_attendance_summary(self):
        """
        Compatibilité backend Django (stats dashboard)
         Construit à partir de la base MySQL
         """

        db = self.database()

        stats = db.get_db_stats()

        return {
            "unique_students": stats.get("active_students", 0),
            "total_records": stats.get("total_attendance", 0),
            "avg_confidence": float(stats.get("avg_confidence", 0) or 0),
            "max_confidence": float(stats.get("max_confidence", 0) or 0),
            "min_confidence": float(stats.get("min_confidence", 0) or 0),
        }
    #-------------------------------------------
    # ==================== DEPENDENCIES ====================
    def face_processor(self):
        from face_processor import FaceProcessor
        return self._load("face_processor", lambda: FaceProcessor("buffalo_l", 0))

    def database(self):
        from database_mysql import StudentDatabase
        return self._load("database", lambda: StudentDatabase(
            host="127.0.0.1",
            user="root",
            password="",
            database="attendance_db"
        ))

    def enrollment(self):
        from enrollment import EnrollmentSystem
        return self._load("enrollment", lambda: EnrollmentSystem(
            self.face_processor(),
            self.database(),
            "enrolled_students"
        ))

    def detector(self):
        from attendance import AttendanceDetector
        return self._load("detector", lambda: AttendanceDetector(
            self.face_processor(),
            self.database(),
            similarity_threshold=0.55,
            frame_skip=2
        ))
    def process_frame(self, frame):
        fp = self.face_processor()
        results = fp.process_frame(frame)

        if not results:
            logger.warning("Aucun visage détecté dans le frame")
            return []

        for a, e in results:
            logger.debug(f"Résultat: student_id={a}, embedding_shape={getattr(e, 'shape', None)}")

        return [
            (a, e) for a, e in results
            if isinstance(e, np.ndarray) and e.shape == (512,)
        ]

    # ==================== Vérifie uniquement que l’embedding est (512,) ====================
    #def process_image(self, image_path: str):
    #   fp = self.face_processor()
    #    success, _, emb = fp.process_image(image_path)

    #    if not success or emb is None or emb.shape != (512,):
    #        return None

    #    return emb

    def process_frame(self, frame):
        fp = self.face_processor()
        results = fp.process_frame(frame)

        return [
            (a, e) for a, e in results
            if isinstance(e, np.ndarray) and e.shape == (512,)
        ]

    def recognize_face(self, embedding):
        if embedding is None or embedding.shape != (512,):
            return None, 0.0, None

        return self.detector().find_match(embedding)

    def enroll_student(
        self,
        name: str,
        image_path: str,
        email: str = None,
        level: str = None,
        filiere: str = None
    ):
        return self.enrollment().enroll_from_image(
            name=name,
            image_path=image_path,
            email=email,
            level=level,
            filiere=filiere
        )
    



    def log_attendance(self, student_id: int, confidence: float, embedding_id=None):
        # ✅ Conversion explicite ici aussi
        student_id = int(student_id) if student_id is not None else None
        confidence = float(confidence) if confidence is not None else None
        embedding_id = int(embedding_id) if embedding_id is not None else None
        return self.database().log_attendance(student_id, confidence, embedding_id)

    def get_student(self, student_id: int):
        return self.database().get_student(student_id)

    def get_db_stats(self):
        return self.database().get_db_stats()

    def reload_detector(self):
        if "detector" in self._modules:
            self._modules["detector"].reload_enrollments()
            logger.info(" Detector reloaded")

    # ==================== HEALTH CHECK ====================
    def health_check(self) -> Dict:
        """Vérifie l'état des modules"""
        status = {
            "face_processor": "face_processor" in self._modules,
            "database": "database" in self._modules,
            "enrollment": "enrollment" in self._modules,
            "detector": "detector" in self._modules,
        }

        status["all_ok"] = all(status.values())
        return status

    def get_attendance_summary(self):
        """
        CORRIGÉE: Retourne les statistiques d'AUJOURD'HUI UNIQUEMENT
        
        Avant: Comptait TOUTES les données jamais enregistrées
        Après: Compte seulement les données d'AUJOURD'HUI
        """
        
        # Récupérer la date d'aujourd'hui
        today = now().date()
        
        # Créer les limites temporelles (00:00:00 à 23:59:59)
        start = make_aware(datetime.combine(today, time.min))
        end = make_aware(datetime.combine(today, time.max))
        
        # ✅ FILTRER PAR DATE (c'était le problème!)
        today_records = Attendance.objects.filter(
            timestamp__range=(start, end)
        )
        
        # Calculer les statistiques SEULEMENT pour aujourd'hui
        total_records = today_records.count()
        
        avg_confidence = today_records.aggregate(
            Avg('confidence')
        )['confidence__avg'] or 0
        
        max_confidence = today_records.aggregate(
            Max('confidence')
        )['confidence__max'] or 0
        
        min_confidence = today_records.aggregate(
            Min('confidence')
        )['confidence__min'] or 0
        
        unique_students = today_records.values('student').distinct().count()

        return {
            "unique_students": unique_students,
            "total_records": total_records,
            "avg_confidence": avg_confidence,
            "max_confidence": max_confidence,
            "min_confidence": min_confidence
        }


# ==================== SINGLETON ACCESS ====================
_service = None
_lock = threading.Lock()

def get_pipeline_service():
    global _service
    if _service is None:
        with _lock:
            if _service is None:
                _service = PipelineService()
    return _service


