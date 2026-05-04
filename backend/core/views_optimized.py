"""
backend/core/views.py - VERSION CORRIGÉE COMPLÈTE
✅ Logging amélioré
✅ Statistiques fixes
✅ Tous les endpoints synchronisés
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Max, Min
import logging
import base64
import tempfile
import os
import hashlib
from pathlib import Path
import numpy as np
import traceback
import time as time_module
from datetime import datetime, time
from django.utils.timezone import now, make_aware
from django.utils import timezone
from backend.settings_complete import MEDIA_URL


from .models import Student, Attendance
from .serializers import StudentSerializer, AttendanceSerializer

from backend import settings_complete
from django.http import request


logger = logging.getLogger(__name__)

def get_pipeline():
    """Lazy import du pipeline"""
    from pipeline.pipeline_service import get_pipeline_service
    return get_pipeline_service()

def clean_base64(image_base64):
    """Nettoyer le préfixe data:image si présent"""
    if "," in image_base64:
        return image_base64.split(",")[1]
    return image_base64


class StudentViewSet(viewsets.ModelViewSet):
    """API pour la gestion des étudiants"""
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    lookup_field = 'student_id'
    
    @action(detail=False, methods=["post"])
    def enroll_from_image(self, request):
        """ENROLL: Plusieurs images base64 → Pipeline → Student + Embeddings"""
        try:
            name = request.data.get("name")
            email = request.data.get("email")
            level = request.data.get("level")
            filiere = request.data.get("filiere")
            images_base64 = request.data.get("images_base64", [])

            # ✅ Vérification des champs obligatoires
            if not name or not images_base64 or not level or not filiere:
                logger.warning("[ENROLL] Champs manquants: name, images_base64, level ou filiere")
                return Response(
                    {"error": "Name, images_base64, level et filiere requis"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            logger.info(f"[ENROLL] Enrolling: {name} avec {len(images_base64)} photo(s)")

            enrollment_summary = {"success": 0, "total_photos": len(images_base64)}
            student_id = None

            # ✅ Boucle sur toutes les photos
            for img_b64 in images_base64:
                image_path = None
                try:
                    clean_b64 = clean_base64(img_b64)
                    image_bytes = base64.b64decode(clean_b64)

                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(image_bytes)
                        image_path = tmp_file.name

                    pipeline = get_pipeline()
                    success, student_id = pipeline.enroll_student(
                        name=name,
                        image_path=image_path,
                        email=email,
                        level=level,
                        filiere=filiere
                    )

                    if success:
                        enrollment_summary["success"] += 1

                except Exception as e:
                    logger.error(f"[ENROLL] Erreur sur une photo: {e}")
                    continue
                finally:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)

            # ✅ Résultat final
            if enrollment_summary["success"] > 0 and student_id:
                student_info = pipeline.get_student(student_id)
                return Response({
                    "success": True,
                    "student_id": student_id,
                    "name": student_info.get('name', name) if student_info else name,
                    "email": student_info.get('email', email) if student_info else email,
                    "level": student_info.get('level', level) if student_info else level,
                    "filiere": student_info.get('filiere', filiere) if student_info else filiere,
                    "enrollment_summary": enrollment_summary,
                    "message": "Student enrolled successfully"
                }, status=status.HTTP_201_CREATED)

            return Response(
                {"error": "Cette photo est déjà utilisée, veuillez insérer une autre"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"[ENROLL] Error: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=["post"])
    def search(self, request):
        """SEARCH ENDPOINT"""
        try:
            query = request.data.get('query', '').strip()
            
            if not query or len(query) < 2:
                return Response({
                    "success": False,
                    "results": [],
                    "error": "Query must be at least 2 characters"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"[SEARCH] Searching for: {query}")
            
            students = Student.objects.filter(
                active=True
            ).filter(
                Q(name__icontains=query) | Q(email__icontains=query)
            ).values('student_id', 'name', 'email')[:10]
            
            results = list(students)
            
            return Response({
                "success": True,
                "results": results,
                "count": len(results)
            })
        
        except Exception as e:
            logger.error(f"[SEARCH] Error: {e}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Statistiques globales des étudiants"""
        try:
            pipeline = get_pipeline()
            stats = pipeline.get_db_stats()
            
            logger.info(f"[STUDENT_STATS] active_students={stats.get('active_students', 0)}")
            
            return Response({
                "success": True,
                "data": {
                    "active_students": stats.get('active_students', 0),
                    "total_attendance": stats.get('total_attendance', 0),
                    "unique_students": stats.get('unique_students', 0)
                }
            })
        except Exception as e:
            logger.error(f"[STUDENT_STATS] Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
class AttendanceViewSet(viewsets.ModelViewSet):
    """API pour la gestion de la présence"""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    lookup_field = 'attendance_id'
  
    def list(self, request):
        """
        ✅ CORRIGÉE: Récupère l'attendance d'aujourd'hui avec TOUS les détails
        
        Corrections appliquées:
        1. Timestamp inclut DATE + HEURE (pas seulement heure)
        2. Filtre par range de dates (cohérent avec get_attendance_summary)
        3. Pas de redondance (student vs name vs full_name)
        4. Tous les imports présents
        """
        try:
            # Récupérer la date d'aujourd'hui
            now_local = timezone.localtime(timezone.now())
            today = now_local.date()

            start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # ✅ FILTRER PAR RANGE (cohérent avec get_attendance_summary)
            records = Attendance.objects.filter(
                timestamp__range=(start, end)
            ).order_by("-timestamp")
            
            logger.info(f"[LIST] Found {records.count()} records")
            
            data = []
            for r in records:
                data.append({
                    "attendance_id": r.id,
                    "student_id": r.student.student_id,
                    # ✅ PAS DE REDONDANCE - garder seulement 'student'
                    # Le frontend utilise "student" pour afficher le nom
                    "student": r.student.name,
                    "confidence": float(r.confidence) if r.confidence else 0,
                    # ✅ TIMESTAMP COMPLET - DATE + HEURE
                    "timestamp": timezone.localtime(r.timestamp).strftime("%Y-%m-%d %H:%M:%S")

                })
            
            logger.info(f"[LIST] Returning {len(data)} formatted records")
            
            return Response({
                "success": True,
                "count": len(data),
                "data": {
                    "count": len(data),
                    "date": str(today),
                    "records": data
                }
            })
        except Exception as e:
            logger.error(f"[LIST] Error: {e}", exc_info=True)
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def recognize(self, request):
        """ENDPOINT PRINCIPAL: Image → Pipeline → Présence"""
        request._start_time = time_module.time()
        try:
            image_base64 = request.data.get("image_base64")
            if not image_base64:
                logger.warning("[RECOGNIZE] No image provided")
                return Response({"error": "image_base64 required"}, 
                              status=status.HTTP_400_BAD_REQUEST)

            clean_b64 = clean_base64(image_base64)
            try:
                image_bytes = base64.b64decode(clean_b64)
            except Exception as e:
                logger.error(f"[RECOGNIZE] Decode error: {e}")
                return Response({"error": "Invalid image encoding"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            image_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(image_bytes)
                    image_path = tmp_file.name

                pipeline = get_pipeline()
                logger.info("[RECOGNIZE] Processing image...")

                # ÉTAPE 1: Détection + Extraction embedding
                embedding = pipeline.process_image(image_path)

                # VALIDATION STRICTE DE L'EMBEDDING
                if (embedding is None or 
                    not isinstance(embedding, np.ndarray) or 
                    embedding.shape != (512,)):
                    
                    logger.error(f"[RECOGNIZE] INVALID EMBEDDING: type={type(embedding)} shape={getattr(embedding, 'shape', None)}")
                    return Response({
                        "success": False,
                        "stage": "PIPELINE",
                        "error": "INVALID_EMBEDDING"
                    }, status=404)
                
                # ÉTAPE 2: Matching avec base de données
                try:
                    student_id, confidence, embedding_id, photo_path = pipeline.recognize_face(embedding)
                    logger.info(f"[RECOGNIZE] MATCH RESULT: id={student_id}, confidence={confidence}")
                except Exception as e:
                    logger.exception("[RECOGNIZE] PIPELINE MATCHING CRASHED")
                    return Response({
                        "success": False,
                        "stage": "PIPELINE_MATCHING",
                        "error": str(e)
                    }, status=500)
                
                # ÉTAPE 3: Si match trouvé
                if student_id is not None and confidence > 0.55:
                    
                    # Log présence dans le pipeline
                    pipeline.log_attendance(
                        student_id=student_id,
                        confidence=confidence,
                        embedding_id=embedding_id
                    )
                    
                    # Récupérer infos étudiant
                    student_info = pipeline.get_student(student_id)
                    
                    # Sync avec Django ORM
                    #attendance_record = None
                    #try:
                    #    student_orm = Student.objects.get(student_id=student_id)
                        #attendance_record = None 
                     #   attendance_record = Attendance.objects.create(
                      #      student=student_orm,
                       #     confidence=confidence,
                        #     timestamp=timezone.now()
                        #)
                       # logger.info(f"[RECOGNIZE] Django record created: id={attendance_record.id}")
                    #except Exception as e:
                     #   logger.warning(f"[RECOGNIZE] Django sync warning: {e}")
                    
                    logger.info(f"[RECOGNIZE] SUCCESS: {student_info.get('name')} ({confidence:.4f})")
                    
                    processing_time = time_module.time() - request._start_time
                    logger.info(f"[PERF] processing_time={processing_time:.3f}s")

                    return Response({
                        "success": True,
                        "student_id": student_id,
                        "student": student_info.get('name'),
                        "email": student_info.get('email'),
                        "confidence": float(confidence),
                        "attendance_id": student_id,  # ou uuid.uuid4() si tu veux un ID unique
                        "timestamp": timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S"), 
                        "photo_path": request.build_absolute_uri(MEDIA_URL + photo_path.replace("\\", "/")),                        
                        "message": f"Welcome {student_info.get('name')}!"
                    })
                
                # PAS DE MATCH
                else:
                    processing_time = time_module.time() - request._start_time
                    logger.info(f"[RECOGNIZE] NO MATCH: confidence={confidence}")
                    logger.info(f"[PERF] processing_time={processing_time:.3f}s")

                    return Response({
                        "success": False,
                        "message": "Unknown face - no match found",
                        "confidence": float(confidence) if confidence else 0.0,
                        "debug_stage": "NO_MATCH",
                        "threshold": 0.55
                    }, status=status.HTTP_404_NOT_FOUND)

            finally:
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.warning(f"[RECOGNIZE] Cleanup failed: {e}")
        
        except Exception as e:
            logger.error("[RECOGNIZE] FULL TRACEBACK:\n" + traceback.format_exc())
            
            return Response(
                {"error": "Internal recognition error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Statistiques de présence"""
        try:
            pipeline = get_pipeline()
            summary = pipeline.get_attendance_summary()
            
            logger.info(f"[ATTENDANCE_STATS] total_records={summary.get('total_records', 0)}")
            
            return Response({
                "success": True,
                "data": {
                    "unique_students": summary.get('unique_students', 0),
                    "total_records": summary.get('total_records', 0),
                    "avg_confidence": float(summary.get('avg_confidence', 0)),
                    "max_confidence": float(summary.get('max_confidence', 0)),
                    "min_confidence": float(summary.get('min_confidence', 0))
                }
            })
        except Exception as e:
            logger.error(f"[ATTENDANCE_STATS] Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    @action(detail=False, methods=["get"])
    def status(self, request):
        """Status présent/absent pour tous les étudiants"""
        try:
            today = timezone.localdate()  # ✅ date locale correcte
            start = timezone.make_aware(datetime.combine(today, time.min))
            end = timezone.make_aware(datetime.combine(today, time.max))

            present_ids = set(
                Attendance.objects.filter(
                    timestamp__range=(start, end),
                    confidence__gte=0.55
                ).values_list("student_id", flat=True).distinct()
            )
            logger.info(f"[STATUS] Found {len(present_ids)} students present today")

            students = []
            for student in Student.objects.filter(active=True).order_by('name'):
                students.append({
                    "student_id": student.student_id,
                    "name": student.name,
                    "email": student.email,
                    "present": int(student.student_id) in present_ids
                })

            return Response({
                "success": True,
                "date": str(today),
                "data": {
                    "date": str(today),
                    "total_students": len(students),
                    "present_today": sum(1 for s in students if s['present']),
                    "absent_today": sum(1 for s in students if not s['present']),
                    "students": students
                }
            })
        except Exception as e:
            logger.error(f"[STATUS] Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def student_history(self, request):
        """Historique d'un étudiant"""
        try:
            student_id = request.query_params.get('student_id')
            
            if not student_id:
                return Response({"error": "student_id required"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            try:
                student = Student.objects.get(student_id=int(student_id))
            except Student.DoesNotExist:
                return Response({"error": "Student not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            records = Attendance.objects.filter(
                student_id=int(student_id)
            ).order_by('-timestamp')[:100]
            
            return Response({
                "success": True,
                "student_id": student.student_id,
                "name": student.name,
                "email": student.email,
                "total_records": len(records),
                "records": [
                    {

                        "date": timezone.localtime(r.timestamp).strftime("%Y-%m-%d"),
                        "time": timezone.localtime(r.timestamp).strftime("%H:%M:%S"),

                        "confidence": float(r.confidence) if r.confidence else 0
                    }
                    for r in records
                ]
            })
        except Exception as e:
            logger.error(f"[HISTORY] Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #------manuel--------------------
    @action(detail=False, methods=["post"])
    def manual_attendance(self, request):
        """
        ENDPOINT: Marquer présence / absence manuellement
        """
        try:
            student_id = request.data.get('student_id')
            is_present = request.data.get('is_present')

            if student_id is None or is_present is None:
                return Response(
                    {"success": False, "error": "student_id et is_present requis"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ✅ FIX bool (très important)
            is_present = str(is_present).lower() == "true"
            student_id = int(student_id)

            # Vérifier étudiant
            try:
                student = Student.objects.get(student_id=student_id)
            except Student.DoesNotExist:
                return Response(
                    {"success": False, "error": "Étudiant non trouvé"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # ✅ FIX TIMEZONE (IMPORTANT)
            today = timezone.localdate()
            start = timezone.make_aware(datetime.combine(today, time.min))
            end = timezone.make_aware(datetime.combine(today, time.max))

            # ===============================
            # ✅ CAS 1 : PRÉSENT
            # ===============================
            if is_present:

                existing = Attendance.objects.filter(
                    student_id=student_id,
                    timestamp__range=(start, end)
                ).first()

                if existing:
                    return Response({
                        "success": True,
                        "message": f"{student.name} déjà PRÉSENT",
                        "data": {
                            "student_id": student_id,
                            "name": student.name,
                            "status": "PRESENT",
                            "timestamp": timezone.localtime(existing.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                        }
                    })

                attendance = Attendance.objects.create(
                    student=student,
                    confidence=1.0
                )

                return Response({
                    "success": True,
                    "message": f"{student.name} marqué PRÉSENT",
                    "data": {
                        "student_id": student_id,
                        "name": student.name,
                        "status": "PRESENT",
                        "timestamp": timezone.localtime(attendance.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    }
                })

            # ===============================
            # ❌ CAS 2 : ABSENT
            # ===============================
            else:

                deleted_count, _ = Attendance.objects.filter(
                    student_id=student_id,
                    timestamp__range=(start, end)
                ).delete()

                if deleted_count > 0:
                    return Response({
                        "success": True,
                        "message": f"{student.name} marqué ABSENT",
                        "data": {
                            "student_id": student_id,
                            "name": student.name,
                            "status": "ABSENT"
                        }
                    })

                return Response({
                    "success": True,
                    "message": f"{student.name} déjà ABSENT",
                    "data": {
                        "student_id": student_id,
                        "name": student.name,
                        "status": "ABSENT"
                    }
                })

        except Exception as e:
            logger.error(f"[MANUAL] Error: {e}", exc_info=True)
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )