import json
import unittest
from unittest.mock import patch

import requests

from banzhuan.client import BanzhuanClient


class RecordingSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def request(self, **kwargs):
        self.calls.append(kwargs)
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"success": True, "data": []}).encode()
        return response


class ObservationReadRoutes(unittest.TestCase):
    def test_venue_paths_preserve_auth_and_hype_query_arguments(self):
        for exchange, prefix in [(None, "/backtests"), ("hype", "/backtests"),
                                 ("poly", "/observations/backtests")]:
            with self.subTest(exchange=exchange), patch(
                "banzhuan.client.load_stored_session_token",
                side_effect=AssertionError("stored credentials must not be read"),
            ):
                session = RecordingSession()
                client = BanzhuanClient(
                    session_token="generated-test-token", exchange=exchange,
                    base_url="http://127.0.0.1:1", session=session,
                )
                client.get_backtest("generated-job", include="trades")
                client.list_backtests(limit=7)
                self.assertEqual([c["url"] for c in session.calls], [
                    "http://127.0.0.1:1" + prefix + "/generated-job",
                    "http://127.0.0.1:1" + prefix,
                ])
                self.assertEqual(session.calls[0]["params"], {"include": "trades"})
                self.assertEqual(session.calls[1]["params"], {"limit": 7})
                for call in session.calls:
                    self.assertEqual(call["method"], "GET")
                    self.assertEqual(call["headers"], {"x-banzhuan-session": "generated-test-token"})


if __name__ == "__main__":
    unittest.main()
