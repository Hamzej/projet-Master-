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
