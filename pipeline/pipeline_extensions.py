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
