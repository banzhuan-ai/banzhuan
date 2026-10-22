import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banzhuan import client


class YototecAuthTests(unittest.TestCase):
    def test_key_storage_is_private_atomic_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / '.banzhuan'
            path = folder / 'api-key.json'
            with patch.object(client, 'CREDENTIALS_DIR', folder), patch.object(client, 'CREDENTIALS_FILE', path):
                client.save_stored_api_key('ytk_fixture')
                self.assertEqual(client.load_stored_api_key(), 'ytk_fixture')
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
                self.assertEqual(json.loads(path.read_text()), {'api_key': 'ytk_fixture'})
                path.chmod(0o644)
                with self.assertRaises(ValueError):
                    client.load_stored_api_key()

    def test_bearer_auth_and_no_legacy_token_or_cross_origin_redirect(self):
        session = Mock()
        response = Mock(status_code=200, headers={'content-type': 'application/json'})
        response.json.return_value = {'balance': 1000000}
        session.request.return_value = response
        api = client.BanzhuanClient(api_key='ytk_fixture', session=session)
        self.assertEqual(api._request('GET', '/backtests'), {'balance': 1000000})
        options = session.request.call_args.kwargs
        self.assertEqual(options['headers'], {'Authorization': 'Bearer ytk_fixture'})
        self.assertFalse(options['allow_redirects'])
        with self.assertRaises(ValueError):
            api._request('GET', 'https://another.example/key')
        with self.assertRaises(ValueError):
            client.BanzhuanClient(api_key='old-session-token', session=session)
        self.assertEqual(session.request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
