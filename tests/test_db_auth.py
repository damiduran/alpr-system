import unittest
import os
from unittest.mock import patch
from alpr_data.db_manager import DBManager
import alpr_web.app as web_app


class TestDBAndGoogleAuth(unittest.TestCase):
    def setUp(self):
        self.test_db_path = 'data/test_auth.db'
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        os.environ['GOOGLE_CLIENT_ID'] = 'test-google-client-id.apps.googleusercontent.com'
        os.environ['ALLOWED_ADMIN_EMAILS'] = 'admin@evergrand.com'
        os.environ['ALLOWED_MANAGER_EMAILS'] = 'manager@evergrand.com'
        os.environ['ALLOWED_VIEWER_EMAILS'] = 'viewer@evergrand.com'

        self.db = DBManager(db_path=self.test_db_path)
        web_app.db = self.db
        web_app.app.config['TESTING'] = True
        self.client = web_app.app.test_client()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_auth_config_endpoint(self):
        res = self.client.get('/api/auth/config')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['google_client_id'], 'test-google-client-id.apps.googleusercontent.com')

    @patch('alpr_web.app.verify_google_id_token')
    def test_tier3_admin_role_and_user_management(self, mock_verify):
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "admin@evergrand.com",
            "email_verified": "true"
        }
        res = self.client.post('/api/auth/google', json={"credential": "valid_admin_token"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['role'], 'admin')

        # Admin can list users
        list_res = self.client.get('/api/users')
        self.assertEqual(list_res.status_code, 200)
        emails = [u['email'] for u in list_res.get_json()]
        self.assertIn('admin@evergrand.com', emails)

        # Admin can add a new manager user
        add_res = self.client.post('/api/users', json={"email": "newboss@evergrand.com", "role": "manager"})
        self.assertEqual(add_res.status_code, 200)
        self.assertEqual(self.db.get_email_role('newboss@evergrand.com'), 'manager')

        # Admin can promote/demote that user to viewer
        upd_res = self.client.post('/api/users', json={"email": "newboss@evergrand.com", "role": "viewer"})
        self.assertEqual(upd_res.status_code, 200)
        self.assertEqual(self.db.get_email_role('newboss@evergrand.com'), 'viewer')

        # Self-lockout protection: Admin cannot demote or delete themselves
        self_demote = self.client.post('/api/users', json={"email": "admin@evergrand.com", "role": "viewer"})
        self.assertEqual(self_demote.status_code, 400)
        self_del = self.client.delete('/api/users', json={"email": "admin@evergrand.com"})
        self.assertEqual(self_del.status_code, 400)

        # Admin can remove another user
        del_res = self.client.delete('/api/users', json={"email": "newboss@evergrand.com"})
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(self.db.get_email_role('newboss@evergrand.com'))

    @patch('alpr_web.app.verify_google_id_token')
    def test_tier2_manager_can_delete_sightings_but_cannot_manage_users(self, mock_verify):
        id1 = self.db.insert_detection(plate_number="MGR123", confidence=92.0)
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "manager@evergrand.com",
            "email_verified": True
        }
        res = self.client.post('/api/auth/google', json={"credential": "valid_manager_token"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['role'], 'manager')

        # Manager CAN delete detections (200)
        del_res = self.client.post('/api/detections/delete', json={"ids": [id1]})
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(len(self.db.get_all_detections()), 0)

        # Manager CANNOT access /api/users (403)
        users_res = self.client.get('/api/users')
        self.assertEqual(users_res.status_code, 403)
        add_user_res = self.client.post('/api/users', json={"email": "x@y.com", "role": "viewer"})
        self.assertEqual(add_user_res.status_code, 403)

    @patch('alpr_web.app.verify_google_id_token')
    def test_tier1_viewer_cannot_delete_sightings_or_manage_users(self, mock_verify):
        id1 = self.db.insert_detection(plate_number="VWR123", confidence=88.0)
        mock_verify.return_value = {
            "aud": "test-google-client-id.apps.googleusercontent.com",
            "email": "viewer@evergrand.com",
            "email_verified": True
        }
        res = self.client.post('/api/auth/google', json={"credential": "valid_viewer_token"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['role'], 'viewer')

        # Viewer is forbidden (403) from deleting detections
        del_res = self.client.post('/api/detections/delete', json={"ids": [id1]})
        self.assertEqual(del_res.status_code, 403)

        # Viewer is forbidden (403) from managing users
        users_res = self.client.get('/api/users')
        self.assertEqual(users_res.status_code, 403)

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


if __name__ == '__main__':
    unittest.main()
