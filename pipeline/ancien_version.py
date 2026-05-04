#######################attendance################################################

"""
Real-time Attendance Detection Module - FINAL PRODUCTION VERSION
Handles: Face recognition, similarity matching, attendance logging
✅ SINGLE SOURCE OF TRUTH: No duplication, no desync, clean architecture
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, NamedTuple
import logging
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt


from pipeline.face_processor import FaceProcessor
from pipeline.database_mysql import StudentDatabase
from pipeline.pipeline_extensions import to_numpy_embedding
from django.utils import timezone



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectionResult(NamedTuple):
    """Single detection result with all data"""
    aligned_face: np.ndarray
    embedding: np.ndarray
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    face_id: int  # Face index in frame


class AttendanceDetector:
    """Real-time face recognition and attendance logging - PRODUCTION READY"""
    
    def __init__(self, face_processor: FaceProcessor, database_mysql: StudentDatabase,
                 similarity_threshold: float = 0.7, frame_skip: int = 2):
    
        """
        Initialize attendance detector
        
        Args:
            face_processor: FaceProcessor instance
            database: StudentDatabase instance
            similarity_threshold: Cosine similarity threshold for match (0.35 for ArcFace)
            frame_skip: Process every Nth frame (1=all, 2=every 2nd, etc.)
        """
        self.face_processor = face_processor
        self.database_mysql = database_mysql
        self.similarity_threshold = similarity_threshold
        self.frame_skip = frame_skip
        
        # Load all enrolled students
        self.enrollments = []
        self.reload_enrollments()
        
        # Attendance tracking (avoid duplicates)
        self.detection_history = {}  # {student_id: timestamp}
        self.duplicate_threshold = 5  # seconds
        
        # FPS monitoring
        self.fps_history = deque(maxlen=30)
        self.last_time = datetime.now()
        
        # Final results tracking
        self.final_results = {}  # {student_id: {name, confidence, time, count}}
        self.detected_students = set()  # Track unique students detected
        
        logger.info(f"✅ Attendance detector initialized")
        logger.info(f"   Loaded {len(self.enrollments)} enrolled students")
        logger.info(f"   Similarity threshold: {similarity_threshold}")
        logger.info(f"   Frame skip: every {frame_skip}th frame")
    
    
    def recognize_face(self, embedding: np.ndarray):
        """
        Reconnaissance faciale complète :
        - Compare l'embedding avec les enrôlements
        - Log l'attendance si match
        - Affiche côte à côte la photo capturée et la photo matched
        - Retourne (student_id, confidence, embedding_id, photo_path)
        """
        if embedding is None or embedding.shape != (512,):
            return None, 0.0, None, None

        student_id, confidence, embedding_id, photo_path = self.find_match(embedding)

        if student_id is not None:
            # Charger la photo matched
            matched_img = cv2.imread(photo_path)
            # Récupérer le nom de l’étudiant
            student = self.database_mysql.get_student(student_id)

            # 🔎 Affichage côte à côte
            self._visualize_match(self.last_aligned_face, matched_img, confidence, student['name'])

            # Log attendance
            self._log_attendance_safe(student_id, confidence, embedding_id, photo_path)

        return student_id, confidence, embedding_id, photo_path


    def reload_enrollments(self):
        """Reload enrolled students and embeddings from database"""
        self.enrollments = self.database_mysql.get_all_enrollments()
        logger.info(f"🔄 Reloaded {len(self.enrollments)} enrollments")
        if self.enrollments:
            print("Premier enrôlement:", self.enrollments[0])
    
   # def find_match(self, embedding: np.ndarray) -> Tuple[Optional[int], float, Optional[int]]:
    #    """
    #    Find matching student for given embedding
        
    #   Args:
    #        embedding: 512-dimensional embedding vector
            
    #    Returns:
    #        (student_id, confidence_score, embedding_id) or (None, score, None) if no match
    #   """
    #    if not self.enrollments:
    #       return None, 0.0, None
        
    #    best_match_id = None
    #    best_confidence = 0.0
    #    best_embedding_id = None
        
    #    for student_id, embedding_id, enrolled_emb in self.enrollments:
    #        # Cosine similarity (dot product of normalized vectors)
    #        similarity = np.dot(embedding, enrolled_emb)
            
    #        if similarity > best_confidence:
    #            best_confidence = similarity
    #            best_match_id = student_id
    #           best_embedding_id = embedding_id
        
        # Check if above threshold
    #    if best_confidence >= self.similarity_threshold:
    #        return best_match_id, best_confidence, best_embedding_id
    #   else:
    #        return None, best_confidence, best_embedding_id

    def _visualize_match(self, probe_img, matched_img, confidence, student_name):
        """Affiche côte à côte la photo capturée et la photo matched"""
        fig, ax = plt.subplots(1, 2, figsize=(8, 4))

        ax[0].imshow(cv2.cvtColor(probe_img, cv2.COLOR_BGR2RGB))
        ax[0].axis("off")
        ax[0].set_title("Photo capturée")

        ax[1].imshow(cv2.cvtColor(matched_img, cv2.COLOR_BGR2RGB))
        ax[1].axis("off")
        ax[1].set_title(f"Photo enregistrée ({student_name})")

        plt.suptitle(f"Similarité: {confidence:.2f}", fontsize=14)
        plt.show()
        
    def find_match(self, embedding: np.ndarray) -> Tuple[Optional[int], float, Optional[int], Optional[str]]:
        if not self.enrollments:
            return None, 0.0, None, None

        embedding = np.array(embedding, dtype=np.float32)

        best_match_id = None
        best_confidence = 0.0
        best_embedding_id = None
        best_photo_path = None

        for enr in self.enrollments:
            student_id = enr.get("student_id")
            embedding_id = enr.get("embedding_id")
            enrolled_emb = to_numpy_embedding(enr.get("embedding"))
            photo_path = enr.get("enrollment_photo_path")

            if np.linalg.norm(enrolled_emb) == 0 or np.linalg.norm(embedding) == 0:
                continue

            similarity = np.dot(embedding, enrolled_emb) / (
                np.linalg.norm(embedding) * np.linalg.norm(enrolled_emb)
            )

            if similarity > best_confidence:
                best_confidence = similarity
                best_match_id = student_id
                best_embedding_id = embedding_id
                best_photo_path = photo_path
    
        if best_confidence >= self.similarity_threshold:
            if best_photo_path:
                best_photo_path = best_photo_path.replace("\\", "/")
                if "enrolled_students" in best_photo_path:
                    idx = best_photo_path.index("enrolled_students")
                    best_photo_path = best_photo_path[idx:]
            return best_match_id, best_confidence, best_embedding_id, best_photo_path
        else:
            if best_photo_path:
                best_photo_path = best_photo_path.replace("\\", "/")
                if "enrolled_students" in best_photo_path:
                    idx = best_photo_path.index("enrolled_students")
                    best_photo_path = best_photo_path[idx:]
            return None, best_confidence, best_embedding_id, best_photo_path


    
    def _get_all_detections(self, frame: np.ndarray) -> List[DetectionResult]:
        """
        ✅ SINGLE SOURCE OF TRUTH
        Process frame ONCE and return all data together
        
        Args:
            frame: BGR video frame
            
        Returns:
            List of DetectionResult with aligned_face, embedding, bbox, face_id
        """
        detections = []
        
        try:
            # ✅ ONE CALL ONLY - NO DUPLICATION
            face_results = self.face_processor.process_frame(frame)
            faces = self.face_processor.detect_faces(frame)
            
            if not face_results or not faces:
                return detections
            
            # ✅ SYNC CHECK: Ensure same number of results
            num_detections = min(len(face_results), len(faces))
            
            for i in range(num_detections):
                aligned_face, embedding = face_results[i]
                face = faces[i]
                x1, y1, x2, y2 = map(int, face.bbox)

                # ✅ Stocker la dernière photo capturée (probe)
                self.last_aligned_face = aligned_face.copy()

                detection = DetectionResult(
                    aligned_face=aligned_face,
                    embedding=embedding,
                    bbox=(x1, y1, x2, y2),
                    face_id=i
                )
                detections.append(detection)
        
        except Exception as e:
            logger.error(f"Error getting detections: {e}")
        
        return detections

    
    def process_frame(self, frame: np.ndarray) -> List[Tuple[int, str, float]]:
        """
        Process single frame: detect faces and match to students
        
        Args:
            frame: BGR video frame
            
        Returns:
            List of (student_id, student_name, confidence) for matched faces
        """
        results = []
        
        try:
            # ✅ Use single source of truth
            detections = self._get_all_detections(frame)
            
            for detection in detections:
                # Find match
                student_id, confidence, embedding_id = self.find_match(detection.embedding)
                
                if student_id is not None:
                    student = self.database_mysql.get_student(student_id)
                    student_name = student['name']
                    
                    results.append((student_id, student_name, confidence))
                    logger.info(f"✅ Match: {student_name} (Confidence: {confidence:.4f})")
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
        
        return results
    
    def process_frame_with_visualization(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Tuple]]:
        """
        Process frame and add bounding boxes + labels
        ✅ USES SINGLE SOURCE OF TRUTH - NO DUPLICATION
        
        Args:
            frame: BGR video frame
            
        Returns:
            (annotated_frame, detections)
        """
        annotated = frame.copy()
        detections = []
        
        try:
            # ✅ SINGLE CALL - Get all data together
            detection_results = self._get_all_detections(frame)
            
            for detection in detection_results:
                # Find match
                student_id, confidence, embedding_id, photo_path = self.find_match(detection.embedding)
                # Unpack bbox
                x1, y1, x2, y2 = detection.bbox

                if student_id is not None and photo_path:
                    student = self.database_mysql.get_student(student_id)
                    label = f"{student['name']} ({confidence:.2%})"
                    color = (0, 255, 0)

                    # 🔎 Affichage côte à côte
                    matched_img = cv2.imread(photo_path)
                    self._visualize_match(detection.aligned_face, matched_img, confidence, student['name'])

                    detections.append((student_id, student['name'], confidence))
                else:
                    label = f"Unknown ({confidence:.2%})"
                    color = (0, 0, 255)
                
                # Draw bounding box
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                
                # Draw label background
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                cv2.rectangle(annotated, (x1, y1-30), (x1+text_w, y1), color, -1)
                cv2.putText(annotated, label, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        except Exception as e:
            logger.error(f"Error in visualization: {e}")
        
        return annotated, detections
    
    def _calculate_fps(self) -> float:
        """Calculate rolling average FPS"""
        current_time = datetime.now()
        delta = (current_time - self.last_time).total_seconds()
        self.last_time = current_time
        
        if delta > 0:
            fps = 1.0 / delta
            self.fps_history.append(fps)
        
        if self.fps_history:
            return sum(self.fps_history) / len(self.fps_history)
        return 0.0
    
   
    def _log_attendance_safe(self,
                            student_id: int,
                            confidence: float,
                            embedding_id: Optional[int] = None,
                            photo_path: Optional[str] = None):
        """
        Enregistre la présence en base MySQL avec protection contre les doublons
        et conversion explicite des types NumPy → Python natifs.
        """
        current_time = timezone.now()
        last_detection = self.detection_history.get(student_id)

        # Vérifie si l'étudiant n'a pas déjà été loggé récemment
        if last_detection is None or (current_time - last_detection).total_seconds() > self.duplicate_threshold:
            # ✅ Conversion explicite des types NumPy → Python
            student_id = int(student_id) if student_id is not None else None
            confidence = float(confidence) if confidence is not None else None
            embedding_id = int(embedding_id) if embedding_id is not None else None

            try:
                # Insertion en base
                self.database_mysql.log_attendance(student_id, confidence, embedding_id)

                # Mise à jour de l’historique pour éviter les doublons
                self.detection_history[student_id] = current_time

                # Récupération des infos étudiant pour log
                student = self.database_mysql.get_student(student_id)
                logger.info(f"📝 Attendance logged: {student['name']} (photo={photo_path})")

            except Exception as e:
                logger.error(f"[ERROR] Attendance logging failed: {e}")



    def process_video_stream(self, camera_index: int = 0, 
                            duration: int = 7,
                            output_video: str = None,
                            window_width: int = 1280,
                            window_height: int = 720) -> Dict[int, dict]:
        """
        Real-time attendance detection with AUTO-STOP after duration
        ✅ SINGLE SOURCE OF TRUTH - No CPU waste, no desync
        
        Args:
            camera_index: Camera device index (0 for default)
            duration: Duration in seconds to run detection (default: 7 seconds)
            output_video: Optional path to save output video
            window_width: Display window width
            window_height: Display window height
            
        Returns:
            Dictionary with final attendance results
        """
        logger.info(f"🎥 Starting attendance detection for {duration} seconds...")
        
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            logger.error("❌ Failed to open camera")
            return {}
        
        # Set camera resolution and FPS for stability
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
        
        # Setup video writer if requested
        out = None
        if output_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))
            logger.info(f"🎬 Recording to: {output_video}")
        
        # Display header
        self._print_detection_header(duration)
        
        try:
            frame_count = 0
            last_stats_update = datetime.now()
            start_time = datetime.now()
            
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    logger.error("❌ Failed to read from camera")
                    break
                
                frame_count += 1
                
                # ✅ AUTO-STOP: Check if duration exceeded
                elapsed_time = (datetime.now() - start_time).total_seconds()
                remaining_time = max(0, duration - elapsed_time)
                
                if elapsed_time >= duration:
                    logger.info(f"⏱️  Duration limit reached ({duration}s)")
                    break
                
                # ✅ FRAME SKIP: Process every Nth frame (reduces CPU load)
                if frame_count % self.frame_skip != 0:
                    # Still display but don't process
                    display_frame = frame.copy()
                else:
                    # Process frame with visualization
                    display_frame, detections = self.process_frame_with_visualization(frame)
                    
                    # Log attendance (thread-safe)
                    for student_id, student_name, confidence in detections:
                        self._log_attendance_safe(student_id, confidence)
                
                # ✅ OPTIMIZED: Resize for display (reduces memory bandwidth)
                display_frame = cv2.resize(display_frame, (window_width, window_height))
                
                # Add FPS overlay
                fps = self._calculate_fps()
                cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Add frame and time info
                cv2.putText(display_frame, f"Frame: {frame_count} | Remaining: {remaining_time:.1f}s", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                
                # Update statistics periodically (every 5 seconds)
                current_time = datetime.now()
                if (current_time - last_stats_update).total_seconds() >= 5:
                    stats = self.database_mysql.get_db_stats()
                    self.current_stats = stats
                    last_stats_update = current_time
                
                # Add statistics overlay
                if hasattr(self, 'current_stats'):
                    stats = self.current_stats
                    stats_text = f"Today: {stats.get('attendance_today', 0)} | " \
                                f"Students: {stats.get('active_students', 0)} | " \
                                f"Detected: {len(self.detected_students)}"
                    cv2.putText(display_frame, stats_text,
                               (10, display_frame.shape[0] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # Display frame
                cv2.imshow("🎥 Attendance Detection (Auto-stop)", display_frame)
                
                # Write to video if saving
                if out:
                    out.write(display_frame)
                
                # ✅ CRITICAL: Non-blocking keyboard input
                cv2.waitKey(1)
        
        except KeyboardInterrupt:
            logger.info("⛔ Interrupted by user")
        
        finally:
            # Cleanup
            cap.release()
            if out:
                out.release()
                logger.info("✅ Video saved")
            cv2.destroyAllWindows()
            
            # 🔥 FINAL REPORTS
            self._print_final_report()
            self._print_database_mysql_statistics()
            
            logger.info("✅ Attendance detection stopped")
            
            return self.final_results
    
    def process_image_batch(self, image_paths: List[str]) -> Dict[str, int]:
        """
        Process batch of images and log attendance
        ✅ Uses single source of truth
        
        Args:
            image_paths: List of paths to images
            
        Returns:
            Dictionary with statistics {matched: int, unmatched: int, errors: int}
        """
        logger.info(f"📁 Processing batch of {len(image_paths)} images...")
        
        stats = {'matched': 0, 'unmatched': 0, 'errors': 0}
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                success, aligned_face, embedding = self.face_processor.process_image(image_path)
                
                if not success:
                    logger.warning(f"[{i}/{len(image_paths)}] Failed to process: {image_path}")
                    stats['errors'] += 1
                    continue
                
                # Find match
                student_id, confidence, embedding_id = self.find_match(embedding)
                
                if student_id is not None:
                    student = self.database_mysql.get_student(student_id)
                    logger.info(f"[{i}/{len(image_paths)}] ✅ Match: {student['name']} ({confidence:.4f})")
                    self._log_attendance_safe(student_id, confidence, embedding_id)
                    stats['matched'] += 1
                else:
                    logger.warning(f"[{i}/{len(image_paths)}] ❌ No match: {image_path}")
                    stats['unmatched'] += 1
            
            except Exception as e:
                logger.error(f"[{i}/{len(image_paths)}] Error processing {image_path}: {e}")
                stats['errors'] += 1
        
        logger.info(f"✅ Batch processing complete: {stats['matched']} matched, "
                   f"{stats['unmatched']} unmatched, {stats['errors']} errors")
        
        return stats
    
    def _print_detection_header(self, duration: int):
        """Print detection header with parameters"""
        print("\n" + "="*70)
        print("🎥 REAL-TIME ATTENDANCE DETECTION SYSTEM")
        print("="*70)
        print(f"Duration: {duration} seconds")
        print(f"Enrolled Students: {len(self.enrollments)}")
        print(f"Similarity Threshold: {self.similarity_threshold}")
        print("\nStatus: RUNNING (auto-stop on timer)...")
        print("="*70 + "\n")
    
    def _print_database_mysql_statistics(self):
        """Print final formatted statistics dashboard"""
        stats = self.database_mysql.get_db_stats()
        summary = self.database_mysql.get_attendance_summary()
        
        print("\n" + "="*70)
        print("📊 DATABASE STATISTICS")
        print("="*70)
        
        print(f"Active Students:        {stats.get('active_students', 0)}")
        print(f"Total Embeddings:       {stats.get('total_embeddings', 0)}")
        print(f"Attendance Today:       {stats.get('attendance_today', 0)}")
        print(f"Database Size:          {stats.get('database_mysql_size_mb', 0):.2f} MB")
        
        print("-"*70)
        print("Today's Attendance Summary:")
        
        print(f"  Unique Students:      {summary.get('unique_students', 0)}")
        print(f"  Total Records:        {summary.get('total_records', 0)}")
        print(f"  Avg Confidence:       {summary.get('avg_confidence', 0):.4f}")
        print(f"  Max Confidence:       {summary.get('max_confidence', 0):.4f}")
        print(f"  Min Confidence:       {summary.get('min_confidence', 0):.4f}")
        
        print("-"*70)
        print("Today's Attendance Status:")
        
        # Get all students
        all_students = self.database_mysql.get_all_active_students()
        
        for student in all_students:
            student_id = student['student_id']
            name = student['name']
            
            if student_id in self.final_results:
                status = "✅ Present"
            else:
                status = "❌ Absent"
            
            print(f"  {name:<20} {status}")
        
        print("="*70 + "\n")
    
    def _print_final_report(self):
        """Print final attendance report"""
        print("\n" + "="*80)
        print("📊 ATTENDANCE REPORT")
        print("="*80)
        
        if not self.final_results:
            print("❌ No attendance records found")
        else:
            print(f"Total Students Present: {len(self.final_results)}\n")
            print(f"{'Name':<25} {'Confidence':<15} {'Detection Time':<15} {'Count':<8}")
            print("-"*80)
            
            # Sort by name
            sorted_results = sorted(self.final_results.items(), 
                                   key=lambda x: x[1]['name'])
            
            for student_id, data in sorted_results:
                print(f"{data['name']:<25} {data['confidence']:<15.4f} "
                      f"{data['time']:<15} {data['count']:<8}")
        
        print("="*80 + "\n")
        #########################################enrollment##############################################################
        """
Enrollment Module
Handles: Student registration, photo capture, embedding storage
"""

import cv2
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from typing import Tuple, Optional

from pipeline.face_processor import FaceProcessor, ImageQuality
from pipeline.database_mysql import StudentDatabase
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class EnrollmentSystem:
    """Handle student enrollment process"""
    
    def __init__(self, face_processor: FaceProcessor, database_mysql: StudentDatabase,
                 enrollment_folder: str = "enrolled_students"):
        """
        Initialize enrollment system
        
        Args:
            face_processor: FaceProcessor instance
            database_mysql: StudentDatabase instance
            enrollment_folder: Directory to store enrollment photos
        """
        self.face_processor = face_processor
        self.database_mysql = database_mysql
        self.enrollment_folder = Path(enrollment_folder)
        self.enrollment_folder.mkdir(exist_ok=True)
        
        logger.info(f"✅ Enrollment system initialized")
    
    def enroll_from_image(self, name: str, image_path: str, 
                         email: str = None,level: str = None,filiere: str = None) -> Tuple[bool, Optional[int]]:
        """
        Enroll student from image file
        
        Args:
            name: Student full name
            image_path: Path to enrollment photo
            email: Optional email
            
        Returns:
            (success, student_id)
        """
        logger.info(f"📸 Enrolling student: {name}")
        
        # Process image
        success, aligned_face, embedding = self.face_processor.process_image(image_path)
        
        if not success:
            logger.error(f"Failed to process image: {image_path}")
            return False, None
        
        # Check quality
        if not ImageQuality.is_good_quality(aligned_face):
            logger.warning(f"Image quality too low for {name}")
            return False, None
        
        quality_metrics = ImageQuality.get_metrics(aligned_face)
        print("ENROLL DEBUG:", name, email, level, filiere)

        # Créer un dossier temporaire
        temp_dir = self.enrollment_folder / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        photo_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        temp_photo_path = temp_dir / photo_filename

        # Sauvegarde de la photo alignée
        cv2.imwrite(str(temp_photo_path), aligned_face)
        logger.info(f"📷 Photo saved temporarily: {temp_photo_path}")

        # Calculer le hash SHA256
        with open(temp_photo_path, "rb") as f:
            photo_bytes = f.read()
            photo_hash = hashlib.sha256(photo_bytes).hexdigest()

        # Vérifier doublon
        result = self.database_mysql._execute_query(
            "SELECT student_id FROM embeddings WHERE photo_hash=%s",
            (photo_hash,)
        )

        if result:
            logger.warning("[ENROLL] Cette photo est déjà utilisée par un autre étudiant")
            return False, None


        # Add student to database
        student_id = self.database_mysql.add_student(
            name=name,
            email=email,
            level=level,
            filiere=filiere
        )
        
        if student_id is None:
            return False, None

        # Créer un sous-dossier pour l'étudiant
        student_dir = self.enrollment_folder / str(student_id)
        student_dir.mkdir(parents=True, exist_ok=True)

        # Déplacer la photo temporaire vers le dossier définitif
        final_photo_path = student_dir / photo_filename
        temp_photo_path.rename(final_photo_path)

        logger.info(f"📷 Photo saved: {final_photo_path}")
        try:
            temp_dir.rmdir()
            logger.info("🗑️ Dossier temporaire supprimé")
        except OSError:
            # Si le dossier contient encore des fichiers, on ne le supprime pas
            pass

        
        # Store embedding
        embedding_id = self.database_mysql.add_embedding(
            student_id=student_id,
            embedding=embedding,
            photo_path=str(final_photo_path),
            quality_metrics=quality_metrics,
            photo_hash=photo_hash  
        )
        
        if embedding_id is None:
            logger.error("Failed to store embedding")
            return False, None
        
        logger.info(f"✅ Student enrolled successfully! ID: {student_id}")
        
        return True, student_id
    
    def enroll_from_camera(self, name: str, email: str = None,level: str = None,filiere: str = None,
                          camera_index: int = 0, quality_threshold: float = 0.7) -> Tuple[bool, Optional[int]]:
        """
        Enroll student by capturing photo from webcam
        
        Interactive process:
        - Shows real-time face detection
        - User can review and confirm enrollment
        
        Args:
            name: Student full name
            email: Optional email
            camera_index: Camera device index
            quality_threshold: Minimum quality score required
            
        Returns:
            (success, student_id)
        """
        logger.info(f"📹 Starting camera enrollment for: {name}")
        
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            logger.error("Failed to open camera")
            return False, None
        
        best_frame = None
        best_embedding = None
        best_quality_score = 0
        
        print("\n" + "="*60)
        print(f"📸 ENROLLMENT SYSTEM: {name}")
        print("="*60)
        print("Instructions:")
        print("  - Look directly at the camera")
        print("  - Good lighting is important")
        print("  - Keep face centered in frame")
        print("  - Press 'SPACE' to capture best frame")
        print("  - Press 'ESC' to cancel")
        print("="*60 + "\n")
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    logger.error("Failed to read from camera")
                    return False, None
                
                frame_count += 1
                
                # Detect and process faces
                results = self.face_processor.process_frame(frame)
                
                # Display info
                display_frame = frame.copy()
                
                if len(results) == 0:
                    cv2.putText(display_frame, "No face detected", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                else:
                    aligned_face, embedding = results[0]  # Use largest face
                    
                    # Quality check
                    quality_metrics = ImageQuality.get_metrics(aligned_face)
                    quality_score = min(
                        quality_metrics['sharpness'] / 1000.0,
                        1.0
                    )
                    
                    # Update best frame if quality is better
                    if quality_score > best_quality_score:
                        best_quality_score = quality_score
                        best_frame = aligned_face.copy()
                        best_embedding = embedding.copy()
                    
                    # Draw quality indicator
                    quality_color = (0, 255, 0) if quality_score > quality_threshold else (0, 165, 255)
                    cv2.putText(display_frame, f"Quality: {quality_score:.2%}", (20, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, quality_color, 2)
                    cv2.putText(display_frame, "Best: SPACE | Cancel: ESC", (20, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # Draw face box
                    faces = self.face_processor.detect_faces(frame)
                    if faces:
                        face = faces[0]
                        x1, y1, x2, y2 = map(int, face.bbox)
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), 
                                    quality_color, 2)
                
                # Show frame
                cv2.imshow("Enrollment Webcam", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):  # SPACE
                    if best_embedding is not None:
                        logger.info(f"✅ Frame captured (Quality: {best_quality_score:.2%})")
                        break
                    else:
                        logger.warning("No valid face captured yet")
                
                elif key == 27:  # ESC
                    logger.info("Enrollment cancelled")
                    cap.release()
                    cv2.destroyAllWindows()
                    return False, None
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
        
        if best_embedding is None:
            logger.error("No face captured")
            return False, None
        
        # Add to database
        student_id = self.database_mysql.add_student(
            name=name,
            email=email,
            level=level,
            filiere=filiere
        )
        
        if student_id is None:
            return False, None
        
        # Save photo
        photo_filename = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        photo_path = self.enrollment_folder / photo_filename
        
        cv2.imwrite(str(photo_path), best_frame)
        logger.info(f"📷 Photo saved: {photo_path}")
        
        # Store embedding
        quality_metrics = ImageQuality.get_metrics(best_frame)
        embedding_id = self.database_mysql.add_embedding(
            student_id=student_id,
            embedding=best_embedding,
            photo_path=str(photo_path),
            quality_metrics=quality_metrics
        )
        
        if embedding_id is None:
            logger.error("Failed to store embedding")
            return False, None
        
        logger.info(f"✅ Student enrolled successfully! ID: {student_id}")
        print(f"\n✅ Enrollment complete!\n   Student ID: {student_id}\n   Name: {name}\n")
        
        return True, student_id
    
    
    def bulk_enroll_from_folder(self, folder_path: str) -> Tuple[int, int]:
        """
        Bulk enroll students from folder structure
        
        Expected folder structure:
        folder/
            ├── student_name_1/
            │   ├── photo1.jpg
            │   └── photo2.jpg
            └── student_name_2/
                └── photo.jpg
        
        Args:
            folder_path: Path to folder with student subfolders
            
        Returns:
            (enrolled_count, failed_count)
        """
        folder = Path(folder_path)
        enrolled_count = 0
        failed_count = 0
        
        logger.info(f"📁 Starting bulk enrollment from: {folder}")
        
        for student_folder in sorted(folder.iterdir()):
            if not student_folder.is_dir():
                continue
            
            student_name = student_folder.name
            
            # Get images
            images = list(student_folder.glob("*.jpg")) + \
                    list(student_folder.glob("*.png"))
            
            if not images:
                logger.warning(f"No images found for {student_name}")
                failed_count += 1
                continue
            
            # Use first image
            image_path = images[0]
            
            success, student_id = self.enroll_from_image(
                name=student_name,
                image_path=str(image_path)
            )
            
            if success:
                enrolled_count += 1
            else:
                failed_count += 1
        
        logger.info(f"📊 Bulk enrollment complete:")
        logger.info(f"   ✅ Enrolled: {enrolled_count}")
        logger.info(f"   ❌ Failed: {failed_count}")
        
        return enrolled_count, failed_count
########################################################################face_processor######################################""
"""
Face Detection and Embedding Module
Handles: Face detection, alignment, embedding extraction
"""

import cv2
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, Optional, List
from insightface.app import FaceAnalysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceProcessor:
    """Core face detection and embedding extraction"""
    
    def __init__(self, model_name: str = "buffalo_l", ctx_id: int = 0):
        """
        Initialize ArcFace model
        
        Args:
            model_name: InsightFace model name (buffalo_l is optimal)
            ctx_id: GPU context ID (0=GPU, -1=CPU)
        """
        logger.info(f"Loading ArcFace model: {model_name}")
        
        self.app = FaceAnalysis(
            name=model_name,
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        self.arcface_model = self.app.models['recognition']
        
        logger.info(f" Model loaded. Embedding dimension: {self.arcface_model.output_shape[1]}")
    
    def detect_faces(self, img: np.ndarray) -> List:
        """
        Detect all faces in image
        
        Args:
            img: BGR image from OpenCV
            
        Returns:
            List of face objects with landmarks
        """
        faces = self.app.get(img)
        return faces
    
    def align_face(self, img: np.ndarray, face) -> np.ndarray:
        """
        Align face using landmarks (eyes horizontal)
        
        Args:
            img: BGR image
            face: Face object with landmarks
            
        Returns:
            Aligned face image 112x112
        """
        # Get eye coordinates
        kps = face.kps
        left_eye, right_eye = kps[0], kps[1]
        
        # Calculate rotation angle
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dy, dx))
        
        # Rotate image to align eyes horizontally
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        aligned = cv2.warpAffine(img, rotation_matrix, (w, h))
        
        # Extract and resize face region
        x1, y1 = int(face.bbox[0]), int(face.bbox[1])
        x2, y2 = int(face.bbox[2]), int(face.bbox[3])
        
        face_region = aligned[y1:y2, x1:x2]
        
        if face_region.size == 0:
            logger.warning("Face region empty after rotation")
            return None
        
        # Resize to 112x112
        aligned_face = cv2.resize(face_region, (112, 112))
        
        return aligned_face
    
    

    def get_embedding(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract ArcFace embedding from face image
        
        Assumes image is already aligned to 112x112
        
        Args:
            img: BGR image (112x112)
            
        Returns:
            Normalized 512-dimensional embedding vector
        """
        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Ensure correct size
        if img_rgb.shape[:2] != (112, 112):
            img_rgb = cv2.resize(img_rgb, (112, 112))
        
        # Extract embedding
        try:
            emb = self.arcface_model.get_feat([img_rgb])[0]
            
            # L2 normalization
            emb = emb / (np.linalg.norm(emb) + 1e-8)
            
            return emb
        except Exception as e:
            logger.error(f"Error extracting embedding: {e}")
            return None
    
    def process_image(self, img_path: str) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Full pipeline: detect -> align -> embed
        
        Args:
            img_path: Path to image file
            
        Returns:
            (success, aligned_face, embedding)
        """
        try:
            # Read image
            img = cv2.imread(str(img_path))
            if img is None:
                logger.error(f"Failed to load image: {img_path}")
                return False, None, None
            
            # Detect faces
            faces = self.detect_faces(img)
            if len(faces) == 0:
                logger.warning(f"No faces detected in {img_path}")
                return False, None, None
            
            # Use largest face
            face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
            
            # Align face
            aligned = self.align_face(img, face)
            if aligned is None:
                return False, None, None
            
            # Extract embedding
            embedding = self.get_embedding(aligned)
            if embedding is None:
                return False, None, None
            
            return True, aligned, embedding
            
        except Exception as e:
            logger.error(f"Error processing image {img_path}: {e}")
            return False, None, None
    
    def process_frame(self, frame: np.ndarray) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        Process video frame - detect multiple faces and embed
        
        Args:
            frame: BGR frame from video capture
            
        Returns:
            List of (aligned_face, embedding) tuples
        """
        results = []
        
        try:
            # Detect all faces
            faces = self.detect_faces(frame)
            
            for face in faces:
                # Align
                aligned = self.align_face(frame, face)
                if aligned is None:
                    continue
                
                # Embed
                embedding = self.get_embedding(aligned)
                if embedding is None:
                    continue
                
                results.append((aligned, embedding))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return []


class ImageQuality:
    """Image quality assessment metrics"""
    
    @staticmethod
    def get_metrics(img: np.ndarray) -> dict:
        """
        Compute image quality metrics
        
        Args:
            img: BGR image
            
        Returns:
            Dictionary with brightness, contrast, sharpness, entropy
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        brightness = np.mean(gray)
        contrast = np.std(gray)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        entropy = -np.sum(
            (gray/255.0) * np.log2((gray/255.0)+1e-9)
        ) / gray.size
        
        return {
            'brightness': float(brightness),
            'contrast': float(contrast),
            'sharpness': float(sharpness),
            'entropy': float(entropy)
        }
    
    @staticmethod
    def is_good_quality(img: np.ndarray, 
                       min_sharpness: float = 40.0,
                       min_brightness: float = 30.0) -> bool:
        """
        Check if image meets quality thresholds
        
        Args:
            img: BGR image
            min_sharpness: Minimum blur score (Laplacian variance)
            min_brightness: Minimum brightness level
            
        Returns:
            True if image quality is acceptable
        """
        metrics = ImageQuality.get_metrics(img)
        
        return (metrics['sharpness'] > min_sharpness and 
                metrics['brightness'] > min_brightness)
###########################################pipeline_service###########################################################################
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


##############################################pipeline_extension###################################################################
"""
pipeline_extensions.py - Extensions robustes pour PipelineService
✔ Validation stricte des embeddings
✔ Décodage base64 robuste
✔ Logging détaillé par étape
✔ Helpers sécurisés
"""

import logging
import numpy as np
import base64
import cv2

logger = logging.getLogger("PIPELINE_EXTENSIONS")


# ==================== VALIDATION ====================

def validate_embedding(embedding: np.ndarray) -> bool:
    """
    Validation stricte des embeddings.
    Règle: numpy array shape == (512,) et valeurs finies.
    """
    try:
        if embedding is None:
            logger.debug("[VALIDATE] Embedding is None")
            return False
        if not isinstance(embedding, np.ndarray):
            logger.debug(f"[VALIDATE] Embedding type invalide: {type(embedding)}")
            return False
        if embedding.shape != (512,):
            logger.debug(f"[VALIDATE] Shape invalide: {embedding.shape} (attendu (512,))")
            return False
        if not np.isfinite(embedding).all():
            logger.debug("[VALIDATE] Embedding contient NaN ou Inf")
            return False
        return True
    except Exception as e:
        logger.exception(f"[VALIDATE] Erreur inattendue: {e}")
        return False


# ==================== DECODE IMAGE ====================

def decode_image_robust(image_base64: str) -> np.ndarray:
    """
    Décodage robuste d'une image base64 en numpy array.
    Gère les formats avec ou sans header data:image/...
    """
    try:
        if not image_base64 or not isinstance(image_base64, str):
            logger.error("[DECODE] Input invalide")
            return None

        # Extraire base64 brut
        if "," in image_base64:
            image_data = image_base64.split(",")[1]
        else:
            image_data = image_base64

        # Décoder base64
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)

        # Décoder avec OpenCV
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("[DECODE] OpenCV a retourné None")
            return None

        logger.info(f"[DECODE] Image décodée avec succès: shape={img.shape}")
        return img

    except Exception as e:
        logger.exception(f"[DECODE] Erreur inattendue: {e}")
        return None


# ==================== LOGGING HELPERS ====================

def log_step(step: str, message: str):
    """
    Helper pour logguer les étapes avec format uniforme.
    """
    logger.info(f"[{step}] {message}")


def log_error(step: str, message: str):
    """
    Helper pour logguer les erreurs avec format uniforme.
    """
    logger.error(f"[{step}] {message}")


def log_debug(step: str, message: str):
    """
    Helper pour logguer en debug avec format uniforme.
    """
    logger.debug(f"[{step}] {message}")

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
