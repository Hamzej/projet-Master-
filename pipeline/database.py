"""
Database Module - MySQL Version
Handles: Student enrollment, embedding storage, similarity matching
Compatible with XAMPP MySQL
"""

import mysql.connector
from mysql.connector import Error
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StudentDatabase:
    """MySQL database for student enrollment and embeddings"""
    
    def __init__(self, host: str = "127.0.0.1", 
                 user: str = "root", 
                 password: str = "", 
                 database: str = "attendance_db", 
                 port: int = 3306):
        """
        Initialize MySQL database connection
        
        Args:
            host: MySQL host (127.0.0.1 for localhost/XAMPP)
            user: MySQL username (root by default)
            password: MySQL password (empty by default in XAMPP)
            database: Database name
            port: MySQL port (3306 by default)
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None
        self.cursor = None
        
        try:
            self.connect()
            self.init_db()
            logger.info(f"✅ Database initialized: {host}:{port}/{database}")
        except Error as e:
            logger.error(f"❌ Database error: {e}")
            raise
    
    def connect(self):
        """Open MySQL database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                autocommit=False
            )
            self.cursor = self.connection.cursor(dictionary=True, buffered=True)
            logger.info("✅ Connected to MySQL")
        except Error as e:
            logger.error(f"Connection error: {e}")
            raise

    
    def disconnect(self):
        """Close MySQL database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from MySQL")
    
    def init_db(self):
        """Create tables if they don't exist"""
        try:
            # Students table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    email VARCHAR(255) UNIQUE,
                    enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE,
                    INDEX idx_active (active),
                    INDEX idx_name (name)
                )
            """)
            
            # Embeddings table (normalized 512-dim vectors)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    embedding_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    embedding LONGBLOB NOT NULL,
                    enrollment_photo_path VARCHAR(500),
                    quality_metrics JSON,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    INDEX idx_student_id (student_id)
                )
            """)
            
            # Attendance log
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence FLOAT,
                    matched_embedding_id INT,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (matched_embedding_id) REFERENCES embeddings(embedding_id),
                    INDEX idx_student_id (student_id),
                    INDEX idx_timestamp (timestamp)
                )
            """)

            
            self.connection.commit()
            logger.info("✅ Database tables created")
        except Error as e:
            logger.error(f"Error creating tables: {e}")
            self.connection.rollback()
            raise
    
    # ============ STUDENT OPERATIONS ============
    
    def add_student(self, name: str, email: str = None) -> Optional[int]:
        """
        Add new student to database
        
        Args:
            name: Student full name
            email: Optional email address
            
        Returns:
            student_id of newly created student, or None if failed
        """
        try:
            self.cursor.execute("""
                INSERT INTO students (name, email, active)
                VALUES (%s, %s, TRUE)
            """, (name, email))
            
            self.connection.commit()
            student_id = self.cursor.lastrowid
            logger.info(f"✅ Student added: {name} (ID: {student_id})")
            
            return student_id
        
        except mysql.connector.errors.IntegrityError:
            logger.error(f"Student already exists: {name}")
            self.connection.rollback()
            return None
        except Error as e:
            logger.error(f"Error adding student: {e}")
            self.connection.rollback()
            return None
    
    def get_student(self, student_id: int) -> Optional[Dict]:
        """Get student information"""
        try:
            self.cursor.execute(
                "SELECT * FROM students WHERE student_id = %s", 
                (student_id,)
            )
            result = self.cursor.fetchone()
            return result if result else None
        except Error as e:
            logger.error(f"Error getting student: {e}")
            return None
    
    def get_all_active_students(self) -> List[Dict]:
        """Get list of all active students"""
        try:
            self.cursor.execute(
                "SELECT * FROM students WHERE active = TRUE ORDER BY enrollment_date DESC"
            )
            results = self.cursor.fetchall()
            return results if results else []
        except Error as e:
            logger.error(f"Error getting students: {e}")
            return []
    
    def deactivate_student(self, student_id: int) -> bool:
        """Mark student as inactive (don't delete, for history)"""
        try:
            self.cursor.execute(
                "UPDATE students SET active = FALSE WHERE student_id = %s", 
                (student_id,)
            )
            self.connection.commit()
            success = self.cursor.rowcount > 0
            
            if success:
                logger.info(f"✅ Student deactivated: {student_id}")
            
            return success
        except Error as e:
            logger.error(f"Error deactivating student: {e}")
            self.connection.rollback()
            return False
    
    def search_students(self, search_term: str) -> List[Dict]:
        """Search students by name or email"""
        try:
            search = f"%{search_term}%"
            self.cursor.execute("""
                SELECT * FROM students
                WHERE (name LIKE %s OR email LIKE %s) AND active = TRUE
                LIMIT 20
            """, (search, search))
            
            results = self.cursor.fetchall()
            return results if results else []
        except Error as e:
            logger.error(f"Error searching students: {e}")
            return []
    
    # ============ EMBEDDING OPERATIONS ============
    
    def add_embedding(self, student_id: int, embedding: np.ndarray, 
                     photo_path: str = None, quality_metrics: Dict = None) -> Optional[int]:
        """
        Store face embedding for student
        
        Args:
            student_id: Student database ID
            embedding: 512-dimensional numpy array
            photo_path: Path to enrollment photo
            quality_metrics: Dictionary of image quality metrics
            
        Returns:
            embedding_id or None if failed
        """
        try:
            # Convert numpy array to bytes
            embedding_blob = embedding.astype(np.float32).tobytes()
            
            # Convert quality metrics to JSON
            quality_json = json.dumps(quality_metrics) if quality_metrics else None
            
            self.cursor.execute("""
                INSERT INTO embeddings 
                (student_id, embedding, enrollment_photo_path, quality_metrics)
                VALUES (%s, %s, %s, %s)
            """, (student_id, embedding_blob, photo_path, quality_json))
            
            self.connection.commit()
            embedding_id = self.cursor.lastrowid
            
            logger.info(f"✅ Embedding stored: Student {student_id} (ID: {embedding_id})")
            return embedding_id
        
        except Error as e:
            logger.error(f"Error storing embedding: {e}")
            self.connection.rollback()
            return None
    
    def get_embeddings_for_student(self, student_id: int) -> List[np.ndarray]:
        """
        Retrieve all embeddings for a student
        
        Args:
            student_id: Student database ID
            
        Returns:
            List of embedding numpy arrays
        """
        try:
            self.cursor.execute("""
                SELECT embedding FROM embeddings 
                WHERE student_id = %s
                ORDER BY created_date DESC
            """, (student_id,))
            
            results = self.cursor.fetchall()
            
            embeddings = []
            for row in results:
                emb = np.frombuffer(row['embedding'], dtype=np.float32)
                embeddings.append(emb)
            
            return embeddings
        except Error as e:
            logger.error(f"Error getting embeddings: {e}")
            return []
    
    def get_all_enrollments(self) -> List[Tuple[int, int, np.ndarray]]:
        """
        Get all active student embeddings for recognition
        
        Returns:
            List of (student_id, embedding_id, embedding) tuples
        """
        try:
            self.cursor.execute("""
                SELECT s.student_id, e.embedding_id, e.embedding
                FROM embeddings e
                JOIN students s ON e.student_id = s.student_id
                WHERE s.active = TRUE
                ORDER BY e.created_date DESC
            """)
            
            results = self.cursor.fetchall()
            
            enrollments = []
            for row in results:
                emb = np.frombuffer(row['embedding'], dtype=np.float32)
                enrollments.append((
                    row['student_id'],
                    row['embedding_id'],
                    emb
                ))
            
            return enrollments
        except Error as e:
            logger.error(f"Error getting enrollments: {e}")
            return []
    
    def delete_embedding(self, embedding_id: int) -> bool:
        """Delete specific embedding"""
        try:
            self.cursor.execute(
                "DELETE FROM embeddings WHERE embedding_id = %s", 
                (embedding_id,)
            )
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Error as e:
            logger.error(f"Error deleting embedding: {e}")
            self.connection.rollback()
            return False
    
    # ============ ATTENDANCE OPERATIONS ============

    def log_attendance(self, student_id: int, confidence: float, embedding_id: int = None) -> bool:
        """Log student attendance in database"""
        try:
            self.cursor.execute("""
                INSERT INTO attendance 
                (student_id, confidence, matched_embedding_id)
                VALUES (%s, %s, %s)
            """, (int(student_id), float(confidence), int(embedding_id) if embedding_id is not None else None))

            self.connection.commit()

            logger.info(
                f"✅ Attendance logged: Student {student_id} (Confidence: {confidence:.4f})"
            )

            return True

        except Error as e:
            logger.error(f"Error logging attendance: {e}")
            self.connection.rollback()
            return False

    def get_attendance_today(self, student_id: int = None) -> List[Dict]:
        """Get today's attendance (all students or specific student)"""
        try:
            if student_id is not None:
                self.cursor.execute("""
                    SELECT 
                        s.student_id,
                        a.student_id,
                        a.timestamp,
                        a.confidence,
                        s.name
                    FROM attendance a
                    JOIN students s ON a.student_id = s.student_id
                    WHERE a.student_id = %s
                      AND DATE(a.timestamp) = CURDATE()
                    ORDER BY a.timestamp DESC
                """, (student_id,))
            else:
                self.cursor.execute("""
                    SELECT 
                        s.student_id,
                        a.student_id,
                        a.timestamp,
                        a.confidence,
                        s.name
                    FROM attendance a
                    JOIN students s ON a.student_id = s.student_id
                    WHERE DATE(a.timestamp) = CURDATE()
                    ORDER BY a.timestamp DESC
                """)

            results = self.cursor.fetchall()
            return results if results else []

        except Error as e:
            logger.error(f"Error getting today's attendance: {e}")
            return []

    def get_attendance_stats(self, student_id: int, days: int = 30) -> Optional[Dict]:
        """Get attendance statistics for a student"""
        try:
            # Get student name
            self.cursor.execute(
                "SELECT name FROM students WHERE student_id = %s",
                (student_id,)
            )
            student = self.cursor.fetchone()

            if not student:
                return None

            # Count attendance
            self.cursor.execute("""
                SELECT COUNT(*) as count
                FROM attendance
                WHERE student_id = %s
                  AND timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (student_id, days))

            result = self.cursor.fetchone()
            count = result["count"] if result else 0

            return {
                "student_id": student_id,
                "student_name": student["name"],
                "attendances_last_days": count,
                "analysis_period_days": days
            }

        except Error as e:
            logger.error(f"Error getting attendance stats: {e}")
            return None

    def get_attendance_range(
        self,
        start_date: str,
        end_date: str,
        student_id: int = None
    ) -> List[Dict]:
        """Get attendance records between two dates"""
        try:
            if student_id is not None:
                self.cursor.execute("""
                    SELECT a.*, s.name
                    FROM attendance a
                    JOIN students s ON a.student_id = s.student_id
                    WHERE a.student_id = %s
                      AND DATE(a.timestamp) BETWEEN %s AND %s
                    ORDER BY a.timestamp DESC
                """, (student_id, start_date, end_date))
            else:
                self.cursor.execute("""
                    SELECT a.*, s.name
                    FROM attendance a
                    JOIN students s ON a.student_id = s.student_id
                    WHERE DATE(a.timestamp) BETWEEN %s AND %s
                    ORDER BY a.timestamp DESC
                """, (start_date, end_date))

            results = self.cursor.fetchall()
            return results if results else []

        except Error as e:
            logger.error(f"Error getting attendance range: {e}")
            return []

    # ============ STATISTICS & REPORTING ============
    
    def get_db_stats(self) -> Dict:
        """Get database statistics"""
        try:
            stats = {}
            
            # Active students
            self.cursor.execute("SELECT COUNT(*) as count FROM students WHERE active = TRUE")
            stats['active_students'] = self.cursor.fetchone()['count']
            
            # Total embeddings
            self.cursor.execute("SELECT COUNT(*) as count FROM embeddings")
            stats['total_embeddings'] = self.cursor.fetchone()['count']
            
            # Today's attendance
            self.cursor.execute("""
                SELECT COUNT(*) as count FROM attendance 
                WHERE DATE(timestamp) = CURDATE()
            """)
            stats['attendance_today'] = self.cursor.fetchone()['count']
            
            # Database size
            self.cursor.execute("""
                SELECT 
                    SUM(ROUND(((data_length + index_length) / 1024 / 1024), 2)) as size_mb
                FROM information_schema.TABLES 
                WHERE table_schema = %s
            """, (self.database,))
            result = self.cursor.fetchone()
            stats['database_size_mb'] = result['size_mb'] if result['size_mb'] else 0
            
            return stats
        except Error as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def get_attendance_summary(self) -> Dict:
        """Get overall attendance summary"""
        try:
            self.cursor.execute("""
                SELECT 
                    COUNT(DISTINCT student_id) as unique_students,
                    COUNT(*) as total_records,
                    AVG(confidence) as avg_confidence,
                    MAX(confidence) as max_confidence,
                    MIN(confidence) as min_confidence
                FROM attendance
                WHERE DATE(timestamp) = CURDATE()
            """)
            
            result = self.cursor.fetchone()
            return result if result else {}
        except Error as e:
            logger.error(f"Error getting summary: {e}")
            return {}
    
    # ============ MAINTENANCE OPERATIONS ============
    
    def export_data(self, export_path: str) -> bool:
        """Export all data to JSON file"""
        try:
            # Get all students with embeddings
            self.cursor.execute("""
                SELECT s.*, GROUP_CONCAT(e.embedding_id) as embedding_ids
                FROM students s
                LEFT JOIN embeddings e ON s.student_id = e.student_id
                GROUP BY s.student_id
            """)
            
            students = self.cursor.fetchall()
            
            data = {
                'students': students,
                'export_date': datetime.now().isoformat()
            }
            
            with open(export_path, 'w') as f:
                json.dump(data, f, default=str, indent=2)
            
            logger.info(f"Data exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Delete attendance records older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted records
        """
        try:
            self.cursor.execute("""
                DELETE FROM attendance
                WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)
            """, (days,))
            
            self.connection.commit()
            
            deleted = self.cursor.rowcount
            logger.info(f"Deleted {deleted} old attendance records")
            
            return deleted
        except Error as e:
            logger.error(f"Error cleaning up records: {e}")
            self.connection.rollback()
            return 0