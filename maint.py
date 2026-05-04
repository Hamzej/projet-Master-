"""
main.py - VERSION LÉGÈRE POUR TEST PIPELINE
"""

import cv2
import logging
from pipeline.pipeline_service import get_pipeline_service



logging.basicConfig(level=logging.INFO)

def main():
    pipeline = get_pipeline_service()
    print("\n✅ PipelineService ready (test mode)")

    while True:
        print("\n" + "-"*70)
        print("MAIN MENU (TEST PIPELINE)")
        print("-"*70)
        print("1. Enroll student from image")
        print("2. Enroll student from camera")
        print("3. Bulk enrollment folder")
        print("4. Real-time attendance detection")
        print("5. Test recognition")
        print("6. Quit")
        print("-"*70)

        choice = input("Select option (1-6): ").strip()

        # ================= ENROLL IMAGE =================
        if choice == "1":
            name = input("Student name: ").strip()
            path = input("Image path: ").strip()
            student_id = pipeline.enroll_student(name=name, image_path=path, email=None)
            print(f"✅ Enrolled ID: {student_id}" if student_id else "❌ Enrollment failed")


        # ================= ENROLL CAMERA =================
        elif choice == "2":
            name = input("Student name: ").strip()
            print("📸 Starting camera enrollment...")
            success, student_id = pipeline.enrollment().enroll_from_camera(name)
            print(f"Result: {success}, ID: {student_id}")

        # ================= BULK =================
        elif choice == "3":
            folder = input("Folder path: ").strip()
            enrolled, failed = pipeline.enrollment().bulk_enroll_from_folder(folder)
            print(f"✅ Enrolled: {enrolled}, ❌ Failed: {failed}")

        # ================= LIVE =================
        elif choice == "4":
            print("\n🎥 Starting real-time attendance...")
            pipeline.detector().process_video_stream(camera_index=0, duration=5)

        # ================= TEST =================
        elif choice == "5":
            path = input("Image path: ").strip()
            emb = pipeline.process_image(path)
            if emb is None:
                print("❌ Failed to process image")
            else:
                student_id, confidence, _, photo_path = pipeline.recognize_face(emb)
                if student_id:
                    student = pipeline.get_student(student_id)
                    print(f"✅ Match: {student['name']} (Confidence: {confidence:.2f})")
                else:
                    print(f"❌ No match (Confidence: {confidence:.2f})")

        # ================= EXIT =================
        elif choice == "6":
            print("👋 Exiting test pipeline...")
            break

        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()
