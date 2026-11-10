"""Static storefront and authenticated catalog API. Python 3.12+, no dependencies."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('CATALOG_DB', str(ROOT.parent / '.web-ban-hang' / 'catalog.sqlite3')))
CATEGORIES = {'tendoo', 'devices', 'ca', 'invoice', 'bh', 'contract'}
SESSIONS = {}
ATTEMPTS = {}
LOCK = threading.Lock()
CREDENTIAL_FILE = Path(os.environ.get('ADMIN_CREDENTIAL_FILE', str(ROOT.parent / '.web-ban-hang' / 'admin.json')))
# Environment configuration takes precedence over the private local account file.
ACCOUNT = {}
if not os.environ.get('ADMIN_PASSWORD') and CREDENTIAL_FILE.is_file():
    ACCOUNT = json.loads(CREDENTIAL_FILE.read_text())
USERNAME = os.environ.get('ADMIN_USERNAME', ACCOUNT.get('username', 'admin'))
PASSWORD = os.environ.get('ADMIN_PASSWORD', ACCOUNT.get('password', ''))
PASSWORD_DIGEST = hashlib.sha256(PASSWORD.encode()).digest()


def connect():
    return sqlite3.connect(DB)


def validate(plans):
    if not isinstance(plans, list) or len(plans) > 2000:
        raise ValueError('Danh sách tối đa 2000 gói.')
    ids = set()
    for p in plans:
        if not isinstance(p, dict) or set(p) != {'id', 'category', 'name', 'duration', 'price', 'details', 'active'}:
            raise ValueError('Cấu trúc gói không hợp lệ.')
        for field, maximum in [('id', 100), ('name', 250), ('duration', 200), ('details', 10000)]:
            if not isinstance(p[field], str) or len(p[field]) > maximum:
                raise ValueError('Nội dung gói quá dài hoặc sai định dạng.')
        if not p['id'] or p['id'] in ids or not p['name'].strip() or p['category'] not in CATEGORIES:
            raise ValueError('Mã, tên hoặc nhóm gói không hợp lệ.')
        if type(p['price']) is not int or not 0 <= p['price'] <= 10**12 or type(p['active']) is not bool:
            raise ValueError('Giá hoặc trạng thái gói không hợp lệ.')
        ids.add(p['id'])
    return plans


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        super().end_headers()

    def reply(self, status, data, cookie=None):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(raw)))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(raw)

    def session(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            token = cookie['catalog_session'].value
        except (KeyError, ValueError):
            return None
        with LOCK:
            for key in list(SESSIONS):
                if SESSIONS[key]['expires'] < time.time():
                    del SESSIONS[key]
            return SESSIONS.get(token)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/plans':
            with connect() as db:
                row = db.execute('SELECT body, version FROM catalog WHERE id=1').fetchone()
            self.reply(200, {'plans': json.loads(row[0]), 'version': row[1]})
        elif path == '/api/session':
            session = self.session()
            self.reply(200 if session else 401, {'csrf': session['csrf']} if session else {'error': 'Vui lòng đăng nhập.'})
        elif path.startswith('/api/'):
            self.reply(404, {'error': 'Không tìm thấy.'})
        else:
            # Serve only application files, never source, database, Git metadata or directory indexes.
            target = (ROOT / path.lstrip('/')).resolve()
            if path == '/':
                self.path = '/index.html'
            elif not target.is_relative_to(ROOT) or any(part.startswith('.') for part in Path(path).parts) or not (path in ['/index.html', '/admin.html', '/admin.js', '/catalog.js', '/admin.css'] or path.startswith('/assets/') or path == '/data/plans.json') or not target.is_file():
                self.send_error(404)
                return
            super().do_GET()

    def do_HEAD(self):
        self.send_error(405)

    def do_POST(self):
        # Same-origin JSON requests plus a per-session CSRF token for mutations.
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            self.reply(403, {'error': 'Nguồn yêu cầu không hợp lệ.'})
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self.reply(415, {'error': 'Yêu cầu JSON.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 3_000_000:
                raise ValueError('Yêu cầu quá lớn hoặc trống.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Dữ liệu không hợp lệ.')
        except (ValueError, UnicodeDecodeError) as e:
            self.reply(400, {'error': str(e)})
            return
        path = urlsplit(self.path).path
        if path == '/api/login':
            ip = self.client_address[0]
            now = time.time()
            with LOCK:
                recent = [t for t in ATTEMPTS.get(ip, []) if t > now - 300]
                ATTEMPTS[ip] = recent
                limited = len(recent) >= 10
                recent.append(now)
            if limited:
                self.reply(429, {'error': 'Thử quá nhiều lần. Vui lòng đợi 5 phút.'})
                return
            supplied = data.get('password', '')
            username = data.get('username', 'admin')
            if not isinstance(username, str) or not hmac.compare_digest(username.encode(), USERNAME.encode()) or not isinstance(supplied, str) or not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(), PASSWORD_DIGEST):
                self.reply(401, {'error': 'Tên đăng nhập hoặc mật khẩu không đúng.'})
                return
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            with LOCK:
                SESSIONS[token] = {'csrf': csrf, 'expires': now + 8 * 3600}
                ATTEMPTS.pop(ip, None)
            secure = '; Secure' if os.environ.get('COOKIE_SECURE') == '1' else ''
            self.reply(200, {'csrf': csrf}, f'catalog_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800{secure}')
            return
        session = self.session()
        if not session:
            self.reply(401, {'error': 'Phiên đăng nhập hết hạn.'})
            return
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), session['csrf']):
            self.reply(403, {'error': 'Vui lòng đăng nhập lại.'})
            return
        if path == '/api/logout':
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            with LOCK:
                SESSIONS.pop(cookie['catalog_session'].value, None)
            self.reply(200, {}, 'catalog_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        elif path == '/api/plans':
            try:
                plans = validate(data.get('plans'))
                with connect() as db:
                    changed = db.execute('UPDATE catalog SET body=?, version=version+1 WHERE id=1 AND version=?', (json.dumps(plans, ensure_ascii=False), data.get('version'))).rowcount
                    version = db.execute('SELECT version FROM catalog WHERE id=1').fetchone()[0]
                if not changed:
                    self.reply(409, {'error': 'Danh sách đã được sửa ở phiên khác. Tải lại trang trước khi sửa tiếp.'})
                else:
                    self.reply(200, {'version': version})
            except (ValueError, sqlite3.Error) as e:
                self.reply(400, {'error': str(e)})
        else:
            self.reply(404, {'error': 'Không tìm thấy.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--bind', default='127.0.0.1')
    args = parser.parse_args()
    if len(PASSWORD) < 12:
        parser.error('Đặt ADMIN_PASSWORD ít nhất 12 ký tự qua biến môi trường trước khi chạy.')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS catalog (id INTEGER PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL)')
        db.execute('INSERT OR IGNORE INTO catalog VALUES (1, ?, 1)', (json.dumps(validate(json.loads((ROOT / 'data/plans.json').read_text()))),))
    os.chmod(DB, 0o600)
    print(f'Server on port {args.port}; database: {DB}', flush=True)
    ThreadingHTTPServer((args.bind, args.port), Handler).serve_forever()
