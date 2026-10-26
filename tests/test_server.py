import json
import os
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import ai_server as app

class ClassifierTests(unittest.TestCase):
    def test_fixtures(self):
        fixtures = json.loads((app.ROOT / 'tests/videos.json').read_text())
        self.assertGreaterEqual(len(fixtures), 20)
        for fixture in fixtures:
            with self.subTest(title=fixture['title']):
                v = app.classify(fixture['title'])
                if fixture['topic']:
                    self.assertIn(fixture['topic'], v['topics'])
                self.assertEqual(v['qualityScore'] >= .65 and v['qualityConfidence'] >= .55, fixture['quality'])
                self.assertEqual(v['method'], 'heuristic_text')

class DiscoveryTests(unittest.TestCase):
    def test_dedup_metadata_cache_and_hidden_subscribers(self):
        calls = []
        def api(endpoint, params):
            calls.append(endpoint)
            if endpoint == 'search':
                return {'items': [{'id': {'videoId': 'abcdefghijk'}}, {'id': {'videoId': 'abcdefghijk'}}]}
            if endpoint == 'videos':
                self.assertEqual(params['id'], 'abcdefghijk')
                return {'items': [{'id': 'abcdefghijk', 'snippet': {'channelId': 'channel', 'title': 'Bricolage tutoriel'}, 'statistics': {'viewCount': '400'}, 'contentDetails': {'duration': 'PT10M'}}]}
            return {'items': [{'id': 'channel', 'statistics': {'hiddenSubscriberCount': True}}]}
        d = app.Discovery(api)
        first = d.discover(['bricolage', 'science'])
        self.assertEqual(len(first['videos']), 1)
        self.assertIsNone(first['videos'][0]['subscriberCount'])
        self.assertEqual(first['videos'][0]['viewCount'], 400)
        self.assertTrue(d.discover(['bricolage', 'science'], True)['cached'])
        self.assertEqual(calls, ['search', 'search', 'videos', 'channels'])
    def test_empty_quota_missing_key(self):
        d = app.Discovery(lambda *args: {'items': []})
        self.assertEqual(d.discover(['bricolage'])['videos'], [])
        self.assertIn('Aucun', d.discover(['bricolage'])['message'])
        d.calls = [app.time.time()] * 12
        with self.assertRaisesRegex(app.DiscoveryError, 'Plafond'):
            d.discover(['science'])
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': ''}):
            with self.assertRaisesRegex(app.DiscoveryError, 'absente'):
                app.Discovery().discover(['bricolage'])
    def test_api_failure_not_faked(self):
        def fail(*args):
            raise app.DiscoveryError('quota épuisé')
        with self.assertRaisesRegex(app.DiscoveryError, 'quota'):
            app.Discovery(fail).discover(['sport'])

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
    def test_classify_and_health(self):
        with urlopen(self.base) as r:
            self.assertEqual(json.load(r)['status'], 'ok')
        req = Request(self.base + '/classify', data=json.dumps({'title': 'Football analyse tactique'}).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(req) as r:
            self.assertIn('sport', json.load(r)['topics'])
    def test_untrusted_origin_and_bad_payload(self):
        with self.assertRaises(HTTPError) as exc:
            urlopen(Request(self.base, headers={'Origin': 'https://evil.example'}))
        self.assertEqual(exc.exception.code, 403)
        with self.assertRaises(HTTPError) as exc:
            urlopen(Request(self.base + '/classify', data=b'[]'))
        self.assertEqual(exc.exception.code, 400)

if __name__ == '__main__':
    unittest.main()
