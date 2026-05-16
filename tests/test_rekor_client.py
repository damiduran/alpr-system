import unittest
from unittest.mock import patch, MagicMock
from alpr_perception.rekor_client import RekorClient

class TestRekorClient(unittest.TestCase):
    def setUp(self):
        self.client = RekorClient(secret_key="sk_test_key")

    def test_parse_best_result_valid(self):
        mock_response = {
            "epoch_time": 1684152000,
            "results": [
                {
                    "plate": "ABC1234",
                    "confidence": 94.2,
                    "vehicle": {
                        "make": [{"name": "honda", "confidence": 99.8}],
                        "model": [{"name": "accord", "confidence": 98.2}],
                        "color": [{"name": "silver", "confidence": 92.1}]
                    }
                }
            ]
        }
        parsed = self.client.parse_best_result(mock_response)
        self.assertEqual(parsed["plate"], "ABC1234")
        self.assertEqual(parsed["make"], "honda")
        self.assertEqual(parsed["color"], "silver")

    def test_parse_best_result_no_results(self):
        mock_response = {"results": []}
        parsed = self.client.parse_best_result(mock_response)
        self.assertIsNone(parsed)

    @patch('requests.post')
    def test_recognize_file_error(self, mock_post):
        mock_post.side_effect = Exception("Network Error")
        # Need a dummy file to avoid FileNotFoundError
        with open('assets/dummy.txt', 'w') as f: f.write('test')
        
        result = self.client.recognize_file('assets/dummy.txt')
        self.assertIn("error", result)

if __name__ == "__main__":
    unittest.main()
