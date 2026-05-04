import mysql.connector
from mysql.connector import Error, pooling
import numpy as np
import json
import logging
import time
import traceback
import threading
from typing import Optional, List, Dict, Tuple, Any
from django.utils import timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StudentDatabase:
    """
    Database manager singleton pour l'application attendance.
    Version durcie : Correctifs sur les commits, la levée d'exceptions et la fermeture du pool.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 host: str = "127.0.0.1",
                 user: str = "root",
                 password: str = "",
                 database: str = "attendance_db",
                 port: int = 3306,
                 pool_name: str = "attendance_pool",
                 pool_size: int = 15):
        if getattr(self, "_initialized", False):
            return
            
        self.config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "autocommit": False,
            "connection_timeout": 10,
            "time_zone": "+00:00",
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci"
        }
        self.pool_name = pool_name
        self.pool_size = pool_size
        self.pool = None
        self._init_pool()
        self._init_db()
        self._initialized = True
        logger.info("StudentDatabase singleton initialisé avec succès")

    def _init_pool(self):
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name=self.pool_name,
                pool_size=self.pool_size,
                pool_reset_session=True,
                **self.config
            )
            logger.info(f"[SUCCESS] Pool initialisé ({self.pool_size} connexions)")
        except Error as e:
            logger.error(f"[CRITICAL] Pool init failed: {e}")
            raise

    def _get_connection(self, retries: int = 3):
        for attempt in range(retries):
            try:
                conn = self.pool.get_connection()
                conn.ping(reconnect=True, attempts=2, delay=0.5)
                if conn.is_connected():
                    return conn
            except Error as e:
                logger.warning(f"[WARNING] Connexion attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(0.4 * (2 ** attempt))
        raise Error("Impossible d'obtenir une connexion valide")

    # ============ CORE QUERY EXECUTION (Production Hardened) ============
    def _execute_query(self,
                       query: str,
                       params: Tuple = None,
                       fetch: str = None,
                       commit: bool = True) -> Any:
        
        max_attempts = 2
        last_exception = None

        for attempt in range(max_attempts):
            conn = None
            cursor = None
            start_time = time.perf_counter()
            
            try:
                conn = self._get_connection()
                cursor = conn.cursor(dictionary=True, buffered=True)
                cursor.execute(query, params or ())

                if fetch == 'one':
                    result = cursor.fetchone()
                    if cursor.with_rows: cursor.fetchall()
                    return result
                elif fetch == 'all':
                    return cursor.fetchall()
                else:
                    rowcount = cursor.rowcount
                    lastrowid = getattr(cursor, 'lastrowid', None)
                    if commit:
                        conn.commit()
                    
                    query_type = query.strip().split()[0].upper()
                    if query_type == "INSERT" and lastrowid:
                        return lastrowid
                    return rowcount

            except Error as e:
                last_exception = e
                error_str = str(e).lower()
                if conn and conn.is_connected():
                    try: conn.rollback()
                    except: pass
                
                transient_errors = ["gone away", "lost connection", "broken pipe", "2006", "2013", "2055", "deadlock"]
                if any(err in error_str for err in transient_errors) and attempt < max_attempts - 1:
                    logger.warning(f"[TRANSIENT ERROR] {e} → Retry {attempt + 1}")
                    time.sleep(0.35)
                    continue
                
                logger.error(f"[MYSQL ERROR] {type(e).__name__}: {e} | Query: {query[:100]}")
                # On ne raise pas ici pour laisser la boucle finir ou raise last_exception à la fin
            except Exception as e:
                last_exception = e
                if conn and conn.is_connected():
                    try: conn.rollback()
                    except: pass
                logger.error(f"[UNEXPECTED] {type(e).__name__}: {e}\n{traceback.format_exc()}")
                break # Erreur non-MySQL, on sort de la boucle de retry
            finally:
                if cursor:
                    try:
                        if cursor.with_rows: cursor.fetchall()
                        cursor.close()
                    except: pass
                if conn:
                    try: conn.close()
                    except: pass
                
                duration = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[TIMING] query took {duration:.1f}ms")

        # Correction 1 : Lever l'exception si aucune tentative n'a abouti
        raise last_exception if last_exception else Exception("Query failed after retries")

    # ============ INIT DB ============
    def _init_db(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(buffered=True)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    level VARCHAR(50),      
                    filiere VARCHAR(100),
                    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE,
                    INDEX idx_name (name),
                    INDEX idx_active (active)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    embedding_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    embedding LONGBLOB NOT NULL,
                    enrollment_photo_path VARCHAR(500),
                    quality_metrics JSON,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    INDEX idx_student (student_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence FLOAT,
                    matched_embedding_id INT,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    INDEX idx_student (student_id),
                    INDEX idx_date (timestamp)
                )
            """)
            conn.commit()
            logger.info("[SUCCESS] Tables initialized successfully")
        except Error as e:
            logger.error(f"[ERROR] _init_db failed: {e}")
            raise
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    # ============ STUDENTS ============
    def add_student(self, name: str, email: str = None, level: str = None, filiere: str = None) -> Optional[int]:
        name = str(name).strip()
        email = str(email).strip() if email else None
        level = str(level).strip() if level else None
        filiere = str(filiere).strip() if filiere else None
        try:
            return self._execute_query(
                "INSERT INTO students (name, email, level, filiere, active) VALUES (%s, %s, %s, %s, TRUE)",
                (name, email, level, filiere),
                commit=True
            )
        except Exception as e:
            if "Duplicate entry" in str(e):
                row = self._execute_query("SELECT student_id FROM students WHERE name = %s", (name,), fetch='one')
                return row["student_id"] if row else None
            return None

    def get_student(self, student_id: int) -> Optional[Dict]:
        return self._execute_query("SELECT * FROM students WHERE student_id = %s", (int(student_id),), fetch='one')

    def get_all_students(self, active_only: bool = True) -> List[Dict]:
        query = "SELECT * FROM students" + (" WHERE active = TRUE" if active_only else "")
        return self._execute_query(query, (), fetch='all')
    
        
    def log_attendance(self, student_id: int, confidence: float, embedding_id: Optional[int]):
        try:
            student_id = int(student_id) if student_id is not None else None
            confidence = float(confidence) if confidence is not None else None
            embedding_id = int(embedding_id) if embedding_id is not None else None

            current_time = timezone.now()  # ✅ source unique

            return self._execute_query(
                """
                INSERT INTO attendance (student_id, confidence, matched_embedding_id, timestamp)
                VALUES (%s, %s, %s, %s)
                """,
                (student_id, confidence, embedding_id, current_time),
                commit=True
            )
        except Exception as e:
            logger.error(f"[ERROR] log_attendance failed: {e}")
            return None
    


    # ============ EMBEDDINGS ============
    def add_embedding(self, student_id: int, embedding: np.ndarray, photo_path: str = None, quality_metrics: Dict = None,photo_hash: str = None ) -> Optional[int]:
        try:
            emb_blob = embedding.astype(np.float32).tobytes()
            q_json = json.dumps(quality_metrics) if quality_metrics else None
            return self._execute_query(
                "INSERT INTO embeddings (student_id, embedding, enrollment_photo_path, quality_metrics, photo_hash) VALUES (%s, %s, %s, %s, %s)",
                (int(student_id), emb_blob, photo_path, q_json,photo_hash),
                commit=True
            )
        
        except mysql.connector.IntegrityError as e:
            if "Duplicate entry" in str(e) and "photo_hash" in str(e):
                logger.warning("[EMBEDDING] Cette photo est déjà utilisée")
                return None
            else:
                logger.error(f"[ERROR] add_embedding IntegrityError: {e}")
                return None
        except Exception as e:
            logger.error(f"[ERROR] add_embedding: {e}")
            return None

    def get_embeddings_for_student(self, student_id: int) -> List[np.ndarray]:
        rows = self._execute_query("SELECT embedding FROM embeddings WHERE student_id = %s", (int(student_id),), fetch='all')
        # Correction 4 : Sécurisation si rows est vide ou None
        if not rows:
            return []
        return [np.frombuffer(r["embedding"], dtype=np.float32).copy() for r in rows]
    
    def get_all_enrollments(self):
        """
        Récupère tous les étudiants enrôlés avec leurs embeddings et photo associée.
        """
        try:
            rows = self._execute_query(
                "SELECT embedding_id, student_id, embedding, enrollment_photo_path FROM embeddings",
                fetch="all"
            )

            return rows if rows else []
        except Exception as e:
            logger.error(f"[ERROR] get_all_enrollments: {e}")
            return []
        

    def get_attendance_today(self, student_id: Optional[int] = None) -> List[Dict]:
        query = "SELECT a.*, s.name FROM attendance a JOIN students s ON a.student_id = s.student_id WHERE DATE(a.timestamp) = CURDATE()"
        params = ()
        if student_id:
            query += " AND a.student_id = %s"
            params = (int(student_id),)
        return self._execute_query(query + " ORDER BY a.timestamp DESC", params, fetch='all')

    # ============ STATS & MAINTENANCE ============
    def get_db_stats(self) -> Dict:
        try:
            row = self._execute_query("""SELECT 
                (SELECT COUNT(*) FROM students WHERE active=TRUE) as active_students,
                (SELECT COUNT(*) FROM embeddings) as embeddings,
                (SELECT COUNT(*) FROM attendance WHERE DATE(timestamp)=CURDATE()) as today_attendance""", fetch='one') or {}
            return {k: int(v or 0) for k, v in row.items()}
        except: return {}

    def export_data(self, path: str) -> bool:
        try:
            data = {
                "students": self._execute_query("SELECT * FROM students", fetch='all'),
                "embeddings": self._execute_query("SELECT * FROM embeddings", fetch='all'),
                "attendance": self._execute_query("SELECT * FROM attendance", fetch='all')
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2, ensure_ascii=False)
            return True
        except: return False

    def cleanup_old_records(self, days: int = 90) -> int:
        # Correction 2 : commit=True explicite pour le DELETE
        return self._execute_query(
            "DELETE FROM attendance WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)",
            (int(days),),
            commit=True
        )

    def health_check(self) -> bool:
        try:
            return self._execute_query("SELECT 1", fetch='one') is not None
        except: return False

    def close_pool(self):
        """Ferme proprement le pool en vidant toutes les connexions actives."""
        if self.pool:
            # Correction 5 : Libération robuste des connexions sans méthode privée
            try:
                for _ in range(self.pool_size):
                    try:
                        conn = self.pool.get_connection()
                        conn.close() # Retourne au pool et se ferme si session_reset=True
                    except: break
                logger.info("[INFO] Connection pool connections cleared")
            except Exception as e:
                logger.error(f"[ERROR] Pool cleanup error: {e}")
            finally:
                self.pool = None