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
