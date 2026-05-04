"""
Unit Tests and Validation Examples
Test the system components individually and together
"""

import unittest
import tempfile
from pathlib import Path
import numpy as np

from face_processor import FaceProcessor, ImageQuality
from database import StudentDatabase
from enrollment import EnrollmentSystem


class TestFaceProcessor(unittest.TestCase):
    """Test FaceProcessor module"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize processor once for all tests"""
        cls.processor = FaceProcessor(model_name="buffalo_l", ctx_id=-1)  # CPU for testing
    
    def test_processor_initialization(self):
        """Test that processor initializes without error"""
        self.assertIsNotNone(self.processor.app)
        self.assertIsNotNone(self.processor.arcface_model)
    
    def test_embedding_dimension(self):
        """Test embedding has correct dimension"""
        # Create dummy image (112x112 BGR)
        dummy_img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
        
        embedding = self.processor.get_embedding(dummy_img)
        
        self.assertEqual(embedding.shape[0], 512)
        self.assertAlmostEqual(np.linalg.norm(embedding), 1.0, places=5)  # L2 norm = 1


class TestDatabase(unittest.TestCase):
    """Test StudentDatabase module"""
    
    def setUp(self):
        """Create temporary database for each test"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = StudentDatabase(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database"""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_add_student(self):
        """Test adding student to database"""
        student_id = self.db.add_student("Test Student", "test@example.com")
        
        self.assertIsNotNone(student_id)
        self.assertGreater(student_id, 0)
    
    def test_get_student(self):
        """Test retrieving student from database"""
        student_id = self.db.add_student("Test Student", "test@example.com")
        student = self.db.get_student(student_id)
        
        self.assertIsNotNone(student)
        self.assertEqual(student['name'], "Test Student")
        self.assertEqual(student['email'], "test@example.com")
    
    def test_add_embedding(self):
        """Test storing embedding"""
        student_id = self.db.add_student("Test Student")
        
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        embedding_id = self.db.add_embedding(student_id, embedding)
        
        self.assertIsNotNone(embedding_id)
        self.assertGreater(embedding_id, 0)
    
    def test_get_embeddings(self):
        """Test retrieving embeddings"""
        student_id = self.db.add_student("Test Student")
        
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        self.db.add_embedding(student_id, embedding)
        
        embeddings = self.db.get_embeddings_for_student(student_id)
        
        self.assertEqual(len(embeddings), 1)
        np.testing.assert_array_almost_equal(embeddings[0], embedding, decimal=5)
    
    def test_log_attendance(self):
        """Test logging attendance"""
        student_id = self.db.add_student("Test Student")
        
        success = self.db.log_attendance(student_id, confidence=0.95)
        
        self.assertTrue(success)
    
    def test_duplicate_student_name(self):
        """Test that duplicate student names are rejected"""
        self.db.add_student("Test Student")
        
        student_id = self.db.add_student("Test Student")
        
        self.assertIsNone(student_id)  # Should fail
    
    def test_database_stats(self):
        """Test getting database statistics"""
        self.db.add_student("Student 1")
        self.db.add_student("Student 2")
        
        stats = self.db.get_db_stats()
        
        self.assertEqual(stats['active_students'], 2)
        self.assertGreater(stats['database_size_mb'], 0)


class TestImageQuality(unittest.TestCase):
    """Test ImageQuality assessment"""
    
    def test_quality_metrics(self):
        """Test that quality metrics are computed"""
        img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
        
        metrics = ImageQuality.get_metrics(img)
        
        self.assertIn('brightness', metrics)
        self.assertIn('contrast', metrics)
        self.assertIn('sharpness', metrics)
        self.assertIn('entropy', metrics)
    
    def test_quality_check(self):
        """Test quality check function"""
        # Good quality image (high contrast)
        good_img = np.zeros((112, 112, 3), dtype=np.uint8)
        good_img[40:70, 40:70] = 255
        
        # Poor quality image (low contrast, blurry)
        poor_img = np.ones((112, 112, 3), dtype=np.uint8) * 128
        
        good_quality = ImageQuality.is_good_quality(good_img)
        poor_quality = ImageQuality.is_good_quality(poor_img)
        
        self.assertTrue(good_quality)
        self.assertFalse(poor_quality)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple modules"""
    
    def setUp(self):
        """Setup for integration tests"""
        self.processor = FaceProcessor(ctx_id=-1)  # CPU
        
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = StudentDatabase(self.db_path)
    
    def tearDown(self):
        """Cleanup"""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_enrollment_workflow(self):
        """Test complete enrollment workflow"""
        # 1. Add student
        student_id = self.db.add_student("Test Student")
        self.assertIsNotNone(student_id)
        
        # 2. Create mock embedding
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        # 3. Store embedding
        embedding_id = self.db.add_embedding(student_id, embedding)
        self.assertIsNotNone(embedding_id)
        
        # 4. Retrieve and verify
        embeddings = self.db.get_embeddings_for_student(student_id)
        self.assertEqual(len(embeddings), 1)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFaceProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestImageQuality))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
