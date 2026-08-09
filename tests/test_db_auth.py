import unittest
import os
import shutil
from alpr_data.db_manager import DBManager

class TestDBAuth(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.test_db_path = 'data/test_auth.db'
        # Ensure it starts fresh
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = DBManager(db_path=self.test_db_path)

    def tearDown(self):
        # Clean up database file
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_default_seeding(self):
        # Test default users exist
        admin_user = self.db.validate_user('admin', 'admin123')
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user['role'], 'admin')

        viewer_user = self.db.validate_user('viewer', 'viewer123')
        self.assertIsNotNone(viewer_user)
        self.assertEqual(viewer_user['role'], 'viewer')

        # Test invalid passwords fail
        invalid_admin = self.db.validate_user('admin', 'wrongpassword')
        self.assertIsNone(invalid_admin)

    def test_user_addition(self):
        # Add new user
        user_id = self.db.add_user('john_doe', 'securepass', 'viewer')
        self.assertIsNotNone(user_id)

        # Validate new user
        user_details = self.db.validate_user('john_doe', 'securepass')
        self.assertIsNotNone(user_details)
        self.assertEqual(user_details['role'], 'viewer')
        self.assertEqual(user_details['username'], 'john_doe')

        # Fetch user by ID
        fetched = self.db.get_user_by_id(user_details['id'])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched['username'], 'john_doe')
        self.assertEqual(fetched['role'], 'viewer')

    def test_get_all_users(self):
        users = self.db.get_all_users()
        # Seeded users should be there
        usernames = [u['username'] for u in users]
        self.assertIn('admin', usernames)
        self.assertIn('viewer', usernames)

    def test_detections_deletion(self):
        # Insert test detections
        id1 = self.db.insert_detection(plate_number="PLATE1", confidence=90.0)
        id2 = self.db.insert_detection(plate_number="PLATE2", confidence=85.0)
        id3 = self.db.insert_detection(plate_number="PLATE3", confidence=95.0)
        
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertIsNotNone(id3)
        
        # Verify they exist
        all_det = self.db.get_all_detections()
        self.assertEqual(len(all_det), 3)
        
        # Delete first two
        success = self.db.delete_detections([id1, id2])
        self.assertTrue(success)
        
        # Verify remaining
        remaining = self.db.get_all_detections()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['id'], id3)

if __name__ == '__main__':
    unittest.main()
