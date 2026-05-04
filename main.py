"""
Main Example Script
Demonstrates: enrollment, database operations, and real-time attendance
"""

import logging
from pathlib import Path

from pipeline.face_processor import FaceProcessor
from pipeline.database_mysql import StudentDatabase
from pipeline.enrollment import EnrollmentSystem
from pipeline.attendance import AttendanceDetector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():

    print("\n" + "="*70)
    print("🎓 SMART ATTENDANCE SYSTEM - FACE RECOGNITION")
    print("="*70 + "\n")

    # ================= INITIALIZATION =================
    logger.info("Initializing system components...")

    face_processor = FaceProcessor(model_name="buffalo_l", ctx_id=0)

    database_mysql = StudentDatabase(
        host="127.0.0.1",
        user="root",
        password="",
        database="attendance_db"
    )

    enrollment = EnrollmentSystem(
        face_processor=face_processor,
        database_mysql=database_mysql,
        enrollment_folder="enrolled_students"
    )

    detector = AttendanceDetector(
        face_processor=face_processor,
        database_mysql=database_mysql,
        similarity_threshold=0.35
    )

    logger.info("✅ All components initialized\n")

    # ================= MENU =================
    while True:

        print("\n" + "-"*70)
        print("MAIN MENU")
        print("-"*70)
        print("1. Ajouter un étudiant à partir d’une photo")
        print("2. Inscrire un étudiant depuis la webcam (mode interactif)")
        print("3. Inscription en lot depuis un dossier")
        print("4. Démarrer la détection de présence en temps réel")
        print("5. Consulter les statistiques de la base de données")
        print("6. Consulter la présence des étudiants")
        print("7. Quitter")
        print("-"*70)

        choice = input("Select option (1-7): ").strip()

        # ================= 1 =================
        if choice == "1":
            name = input("Student name: ").strip()
            email = input("Email (optional): ").strip() or None
            image_path = input("Path to image: ").strip()

            student_id = enrollment.enroll_from_image(
                name=name,
                image_path=image_path,
                email=email
            )

            print(
                f"\n✅ Enrollment successful! Student ID: {student_id}\n"
                if student_id
                else "\n❌ Enrollment failed\n"
            )

        # ================= 2 =================
        elif choice == "2":
            name = input("Student name: ").strip()
            email = input("Email (optional): ").strip() or None

            student_id = enrollment.enroll_from_camera(
                name=name,
                email=email,
                camera_index=0
            )

            print(
                f"\n✅ Enrollment successful! Student ID: {student_id}\n"
                if student_id
                else "\n❌ Enrollment failed\n"
            )

        # ================= 3 =================
        elif choice == "3":
            folder_path = input("Path to folder: ").strip()
            enrolled, failed = enrollment.bulk_enroll_from_folder(folder_path)
            print(f"\n✅ Enrolled: {enrolled}, ❌ Failed: {failed}\n")

        # ================= 4 =================
        elif choice == "4":
            save_video = input("Save video? (y/n): ").strip().lower() == 'y'
            output_path = input("Output video path: ").strip() if save_video else None

            try:
                detector.process_video_stream(
                    camera_index=0,
                    output_video=output_path,
                    duration=7
                )
            except Exception as e:
                logger.error(f"Attendance detection crashed: {e}")
                print("\n❌ Detection error - check logs\n")

        # ================= 5 =================
        elif choice == "5":
            print("\n" + "="*70)
            print("📊 DATABASE STATISTICS")
            print("="*70)

            try:
                stats = database_mysql.get_db_stats()
            except Exception as e:
                logger.error(f"get_db_stats failed: {e}")
                stats = {}

            print(f"Active Students:        {stats.get('active_students', 0)}")
            print(f"Total Embeddings:       {stats.get('total_embeddings', 0)}")
            print(f"Today's Attendance:     {stats.get('attendance_today', 0)}")
            print(f"Database Size:          {stats.get('database_size_mb', 0):.2f} MB")
            print("="*70 + "\n")

        # ================= 6 =================
        elif choice == "6":
            student_id = input("Student ID (or 'all'): ").strip()

            if student_id.lower() == 'all':
                attendance = database_mysql.get_attendance_today()

                print("\n" + "="*70)
                print("📋 TODAY ATTENDANCE")
                print("="*70)

                if attendance and len(attendance) > 0:
                    for record in attendance:
                        print(
                            f"{record['timestamp']} | "
                            f"{record['name']:20s} | "
                            f"Confidence: {record['confidence']:.4f}"
                        )
                else:
                    print("❌ No attendance records found")

                print("="*70 + "\n")

            else:
                try:
                    student_id = int(student_id)
                    stats = database_mysql.get_attendance_stats(student_id, days=30)

                    if stats:
                        print("\n" + "="*70)
                        print(f"📈 ATTENDANCE - {stats['student_name']}")
                        print("="*70)
                        print(f"Student ID:        {stats['student_id']}")
                        print(f"Attendances (30d): {stats['attendances_last_30_days']}")
                        print("="*70 + "\n")
                    else:
                        print("Student not found\n")

                except ValueError:
                    print("Invalid student ID\n")

        # ================= 7 =================
        elif choice == "7":
            print("\n👋 Goodbye!\n")
            break

        else:
            print("Invalid option\n")


# ================= ENTRY POINT =================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
