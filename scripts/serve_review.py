"""Read-only loopback server for the local human review application (stdlib only)."""
import argparse
import hashlib
import json
import mimetypes
import re
import threading
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_ID = 'homevoice-local-review-v1'
SYSTEMS = ('edge_native', 'qwen35_2b', 'qwen35_4b')
REPORTS = ('summary', 'case_overview', 'scene_overview', 'run_overview')

def allowed_data_path(value):
    return bool(re.fullmatch(r'(?:reports/(?:summary|case_overview|scene_overview|run_overview)\.json|data/manifest\.json|data/cases/[TC]\d{2}_\d{3}\.json|runs/(?:edge_native|qwen35_2b|qwen35_4b)/[TC]\d{2}_\d{3}\.json|assets/audio/(?:input|edge|baseline)/[a-f0-9]+\.wav)', value))

def resolve_data(root, value):
    if not allowed_data_path(value):
        raise PermissionError('This file is outside the review data allowlist')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise PermissionError('Path escapes the dataset directory')
    return path

def byte_range(header, size):
    if not header:
        return None
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
    if not match or not any(match.groups()) or size == 0:
        raise ValueError('Invalid range')
    start, end = match.groups()
    if not start:
        count = int(end)
        if count <= 0:
            raise ValueError('Invalid suffix range')
        return max(0, size - count), size - 1
    start = int(start)
    end = min(int(end), size - 1) if end else size - 1
    if start >= size or start > end:
        raise ValueError('Unsatisfiable range')
    return start, end

def make_server(root=ROOT, port=18787):
    root = Path(root).resolve()
    root_id = hashlib.sha256(str(root).encode()).hexdigest()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'HomeVoiceReview/1.0'
        def log_message(self, *_args):
            pass

        def review_headers(self, status, length, content_type, extra=None):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(length))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()

        def reply_json(self, data, status=200, head=False):
            content = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
            self.review_headers(status, len(content), 'application/json; charset=utf-8')
            if not head:
                self.wfile.write(content)

        def do_HEAD(self):
            self.serve(True)

        def do_GET(self):
            self.serve(False)

        def serve(self, head):
            port_number = self.server.server_port
            if self.headers_in_host() not in {f'127.0.0.1:{port_number}', f'localhost:{port_number}'}:
                self.reply_json({'error': 'Use the local server address'}, 403, head)
                return
            route = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            try:
                if route == '/api/health':
                    self.reply_json({'app': APP_ID, 'root_id': root_id}, head=head)
                    return
                if route == '/api/index':
                    data = {name: json.loads((root / 'reports' / (name + '.json')).read_text('utf-8')) for name in REPORTS}
                    data.update(root_name=root.name, manifest_sha256=hashlib.sha256((root / 'data/manifest.json').read_bytes()).hexdigest())
                    self.reply_json(data, head=head)
                    return
                if route in ('/', '/review'):
                    self.review_headers(302, 0, 'text/plain', {'Location': '/review/'})
                    return
                if route == '/review/':
                    path = root / 'review/index.html'
                elif route in ('/review/index.html', '/review/app.js', '/review/core.js', '/review/style.css'):
                    path = root / route.lstrip('/')
                elif route.startswith('/files/'):
                    path = resolve_data(root, route[len('/files/'):])
                else:
                    raise PermissionError('Unknown route')
                if not path.is_file():
                    raise FileNotFoundError(path.name)
                size = path.stat().st_size
                try:
                    selected = byte_range(self.headers.get('Range'), size)
                except ValueError:
                    self.review_headers(416, 0, 'text/plain', {'Content-Range': f'bytes */{size}'})
                    return
                start, end = selected if selected else (0, size - 1)
                length = max(0, end - start + 1)
                content_type = {'js': 'text/javascript; charset=utf-8', 'css': 'text/css; charset=utf-8', 'html': 'text/html; charset=utf-8', 'json': 'application/json; charset=utf-8', 'wav': 'audio/wav'}.get(path.suffix[1:], mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
                extra = {'Accept-Ranges': 'bytes'}
                if selected:
                    extra['Content-Range'] = f'bytes {start}-{end}/{size}'
                self.review_headers(206 if selected else 200, length, content_type, extra)
                if not head:
                    with path.open('rb') as stream:
                        stream.seek(start)
                        while length:
                            block = stream.read(min(length, 256 * 1024))
                            if not block:
                                break
                            self.wfile.write(block)
                            length -= len(block)
            except PermissionError:
                self.reply_json({'error': 'File not available to the review app'}, 403, head)
            except FileNotFoundError:
                self.reply_json({'error': 'Local file missing; extract the input and evaluation archives into the dataset root'}, 404, head)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except (OSError, ValueError):
                self.reply_json({'error': 'Unable to read the selected local data file'}, 500, head)

        def headers_in_host(self):
            return self.headers.get('Host', '').lower()

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18787)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    try:
        server = make_server(args.root, args.port)
    except OSError:
        root_id = hashlib.sha256(str(args.root.resolve()).encode()).hexdigest()
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/health', timeout=2) as response:
                health = json.load(response)
            if health == {'app': APP_ID, 'root_id': root_id}:
                address = f'http://127.0.0.1:{args.port}/review/'
                if args.open:
                    webbrowser.open(address)
                print(json.dumps({'already_running': True, 'url': address}), flush=True)
                return
        except (OSError, ValueError):
            pass
        server = make_server(args.root, 0)
    address = f'http://127.0.0.1:{server.server_port}/review/'
    print(json.dumps({'app': APP_ID, 'url': address, 'dataset': str(args.root.resolve()), 'read_only': True}), flush=True)
    if args.open:
        threading.Timer(0.5, webbrowser.open, args=(address,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
