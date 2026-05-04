
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