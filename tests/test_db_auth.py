import unittest
import os
from unittest.mock import patch
from alpr_data.db_manager import DBManager
from alpr_web.app import app


class TestDBAndGoogleAuth(unittest.TestCase):
    def setUp(self):
        self.test_db_path = 'data/test_auth.db'
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = DBManager(db_path=self.test_db_path)

        app.config['TESTING'] = True
        self.client = app.test_client()

        os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client-id.apps.googleusercontent.com'
        os.environ['ALLOWED_ADMIN_EMAILS'] = 'admin@evergrand.com'
        os.environ['ALLOWED_VIEWER_EMAILS'] = 'viewer@evergrand.com'

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_auth_config_endpoint(self):
        res = self.client.get('/api/auth/config')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['google_client_id'], 'test-google-client-id.apps.googleusercontent.com')

    @patch('alpr_web.app.verify_google_id_token')
    def test_google_auth_admin_role(self, mock_verify):
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "admin@evergrand.com",
            "email_verified": "true"
        }
        res = self.client.post('/api/auth/google', json={"credential": "valid_admin_token"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body['user']['username'], 'admin@evergrand.com')
        self.assertEqual(body['user']['role'], 'admin')

        me_res = self.client.get('/api/auth/me')
        self.assertTrue(me_res.get_json()['authenticated'])
        self.assertEqual(me_res.get_json()['user']['role'], 'admin')

    @patch('alpr_web.app.verify_google_id_token')
    def test_google_auth_viewer_role_and_delete_restriction(self, mock_verify):
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "viewer@evergrand.com",
            "email_verified": True
        }
        res = self.client.post('/api/auth/google', json={"credential": "valid_viewer_token"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body['user']['role'], 'viewer')

        # Viewer should be forbidden (403) from deleting detections
        del_res = self.client.post('/api/detections/delete', json={"ids": [1]})
        self.assertEqual(del_res.status_code, 403)

    @patch('alpr_web.app.verify_google_id_token')
    def test_google_auth_unauthorized_email_rejected(self, mock_verify):
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "stranger@example.com",
            "email_verified": "true"
        }
        res = self.client.post('/api/auth/google', json={"credential": "stranger_token"})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Unauthorized email address", res.get_json()['error'])

    @patch('alpr_web.app.verify_google_id_token')
    def test_google_auth_invalid_token_rejected(self, mock_verify):
        mock_verify.side_effect = ValueError("Invalid Google credential token.")
        res = self.client.post('/api/auth/google', json={"credential": "bad_token"})
        self.assertEqual(res.status_code, 400)

    def test_detections_deletion(self):
        id1 = self.db.insert_detection(plate_number="PLATE1", confidence=90.0)
        id2 = self.db.insert_detection(plate_number="PLATE2", confidence=85.0)
        id3 = self.db.insert_detection(plate_number="PLATE3", confidence=95.0)

        self.assertEqual(len(self.db.get_all_detections()), 3)
        success = self.db.delete_detections([id1, id2])
        self.assertTrue(success)

        remaining = self.db.get_all_detections()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['id'], id3)


if __name__ == '__main__':
    unittest.main()
