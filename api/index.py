"""Vercel Python function; shared PostgreSQL persists catalog and login sessions."""
import os
from pathlib import Path
import sys
import threading
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

_READY = False
_LOCK = threading.Lock()


class handler(server.Handler):
    def dispatch(self, method):
        global _READY
        if len(server.PASSWORD) < 12 or not server.DATABASE_URL:
            self.reply(503, {'error': 'Chưa cấu hình máy chủ. Trong Vercel Settings → Environment Variables, đặt ADMIN_PASSWORD (ít nhất 12 ký tự) và DATABASE_URL của PostgreSQL, sau đó Redeploy.'})
            return
        try:
            with _LOCK:
                if not _READY:
                    server.initialize()
                    _READY = True
            route = parse_qs(urlsplit(self.path).query).get('route', [''])[0]
            if route:
                self.path = '/api/' + route
            os.environ['COOKIE_SECURE'] = '1'
            # Use only Vercel's platform-provided client IP for shared throttling.
            self.client_address = (self.headers.get('x-vercel-forwarded-for', self.client_address[0]).split(',')[0].strip(), 0)
            if self.path == '/api/admin':
                self.path='/admin'
            if self.path != '/admin' and not urlsplit(self.path).path.startswith('/api/'):
                self.reply(404, {'error': 'Không tìm thấy API.'})
                return
            method(self)
        except Exception:
            # Never return database URLs or credential-bearing driver errors.
            self.reply(503, {'error': 'Không kết nối được cơ sở dữ liệu quản trị. Kiểm tra DATABASE_URL, quyền truy cập PostgreSQL và nhật ký Functions trên Vercel.'})

    def do_GET(self):
        self.dispatch(server.Handler.do_GET)

    def do_POST(self):
        self.dispatch(server.Handler.do_POST)
