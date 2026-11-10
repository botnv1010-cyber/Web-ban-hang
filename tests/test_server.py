import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.password = secrets.token_urlsafe(24)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.process = subprocess.Popen([sys.executable, str(ROOT/'server.py'), '--port', str(cls.port)], env={**os.environ, 'ADMIN_PASSWORD': cls.password, 'CATALOG_DB': cls.temp.name+'/db.sqlite'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                cls.request('GET', '/api/plans')
                break
            except OSError:
                time.sleep(.05)
        else:
            raise RuntimeError('Server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.temp.cleanup()

    @classmethod
    def request(cls, method, path, data=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=5)
        body = json.dumps(data) if data is not None else None
        conn.request(method, path, body, {'Content-Type':'application/json', **(headers or {})})
        res = conn.getresponse()
        status, cookie, raw = res.status, res.getheader('Set-Cookie'), res.read()
        conn.close()
        try:
            result = json.loads(raw)
        except ValueError:
            result = None
        return status, cookie, result

    def login(self):
        status, cookie, data = self.request('POST', '/api/login', {'password':self.password})
        self.assertEqual(status, 200)
        return {'Cookie':cookie.split(';')[0], 'X-CSRF-Token':data['csrf']}

    def test_auth_and_logout(self):
        self.assertEqual(self.request('POST', '/api/login', {'password':'incorrect'})[0], 401)
        self.assertEqual(self.request('POST', '/api/plans', {})[0], 401)
        headers = self.login()
        self.assertEqual(self.request('GET', '/api/session', headers=headers)[0], 200)
        self.assertEqual(self.request('POST', '/api/plans', {}, {'Cookie':headers['Cookie']})[0], 403)
        self.assertEqual(self.request('POST', '/api/logout', {}, headers)[0], 200)
        self.assertEqual(self.request('GET', '/api/session', headers=headers)[0], 401)

    def test_catalog_crud_validation_and_conflict(self):
        headers = self.login()
        data = self.request('GET', '/api/plans')[2]
        original = data['plans']
        plan = {'id':'test-package','category':'tendoo','name':'Gói kiểm thử','duration':'12 tháng','price':123000,'details':'Chi tiết mới','active':True}
        updated = original + [plan]
        saved = self.request('POST', '/api/plans', {'plans':updated,'version':data['version']}, headers)
        self.assertEqual(saved[0], 200)
        public = self.request('GET', '/api/plans')[2]
        self.assertEqual(public['plans'][-1], plan)
        self.assertEqual(self.request('POST', '/api/plans', {'plans':original,'version':data['version']}, headers)[0], 409)
        plan['price'] = -1
        self.assertEqual(self.request('POST', '/api/plans', {'plans':updated,'version':public['version']}, headers)[0], 400)
        self.assertEqual(self.request('POST', '/api/plans', {'plans':original,'version':public['version']}, headers)[0], 200)
        self.assertEqual(self.request('GET', '/api/plans')[2]['plans'], original)

    def test_private_files_and_cross_origin(self):
        for path in ['/.git/config','/server.py','/tests/test_server.py','/assets/../../server.py']:
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('POST','/api/login', {'password':self.password}, {'Origin':'https://other.example'})[0],403)
