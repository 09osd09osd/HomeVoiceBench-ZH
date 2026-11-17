"""Exercise the read-only server, including WAV seeking and private-path denial."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from scripts.serve_review import allowed_data_path, byte_range, make_server, resolve_data


class ReviewServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        files = {
            'review/index.html': '<!doctype html><title>Review</title>',
            'reports/summary.json': '{}', 'reports/case_overview.json': '[]',
            'reports/scene_overview.json': '[]', 'reports/run_overview.json': '[]',
            'data/manifest.json': '{}', 'data/cases/T06_003.json': '{"case_id":"T06_003"}',
            'assets/audio/edge/abcdef.wav': '0123456789', '.local/keys.json': 'private-fixture',
        }
        for name, body in files.items():
            path = cls.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding='utf-8')
        cls.server = make_server(cls.root, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, path, method='GET', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_index_and_html(self):
        status, headers, body = self.request('/api/index')
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data['run_overview'], [])
        self.assertEqual(len(data['manifest_sha256']), 64)
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(self.request('/review/')[0], 200)
        self.assertEqual(self.request('/api/health')[0], 200)
        for path in ('/', '/review'):
            status, headers, _ = self.request(path)
            self.assertEqual((status, headers['Location']), (302, '/review/'))

    def test_seek_and_head(self):
        path = '/files/assets/audio/edge/abcdef.wav'
        self.assertEqual(self.request(path)[2], b'0123456789')
        status, headers, body = self.request(path, headers={'Range':'bytes=2-5'})
        self.assertEqual((status, body), (206, b'2345'))
        self.assertEqual(headers['Content-Range'], 'bytes 2-5/10')
        self.assertEqual(headers['Content-Type'], 'audio/wav')
        self.assertEqual(self.request(path, headers={'Range':'bytes=-3'})[2], b'789')
        self.assertEqual(self.request(path, headers={'Range':'bytes=7-'})[2], b'789')
        status, headers, body = self.request(path, 'HEAD')
        self.assertEqual((status, headers['Content-Length'], body), (200, '10', b''))
        status, headers, body = self.request(path, headers={'Range':'bytes=99-'})
        self.assertEqual((status, headers['Content-Range'], body), (416, 'bytes */10', b''))

    def test_private_paths_unknown_routes_and_host_are_blocked(self):
        for path in ['/files/.local/keys.json','/files/data/cases/../../.local/keys.json','/files/%2e%2e/.local/keys.json','/.local/keys.json','/files/assets/audio/edge/abcdef.wav%0a','/review/../.local/keys.json']:
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertEqual(status, 403)
                self.assertNotIn(b'private-fixture', body)
        self.assertEqual(self.request('/api/index', headers={'Host':'example.org'})[0], 403)
        self.assertEqual(self.request('/files/data/cases/T01_001.json')[0], 404)
        self.assertEqual(self.request('/api/index', method='POST')[0], 501)

    def test_helpers(self):
        self.assertTrue(allowed_data_path('runs/qwen35_2b/T06_003.json'))
        self.assertFalse(allowed_data_path('data/cases/T06_003.json\n'))
        with self.assertRaises(PermissionError):
            resolve_data(self.root, '../.local/keys.json')
        for header in ['bytes=','bytes=-0','bytes=5-2','bytes=0-1,3-4']:
            with self.subTest(header=header), self.assertRaises(ValueError):
                byte_range(header, 10)
        self.assertEqual(byte_range('bytes=-100', 10), (0, 9))


if __name__ == '__main__':
    unittest.main()
