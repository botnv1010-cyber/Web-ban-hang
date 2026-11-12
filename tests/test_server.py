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
        self.assertEqual(self.request('POST', '/api/login', {'username':'wrong','password':self.password})[0], 401)
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

    def test_catalog_cache_revalidates_after_admin_save(self):
        def get(etag=None):
            conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
            conn.request('GET', '/api/plans', headers={'If-None-Match': etag} if etag else {})
            response = conn.getresponse()
            result = response.status, response.getheader('ETag'), response.getheader('Cache-Control'), response.read()
            conn.close()
            return result
        status, etag, policy, raw = get()
        self.assertEqual(status, 200)
        self.assertIn('must-revalidate', policy)
        self.assertEqual(get(etag)[0], 304)
        self.assertEqual(get(etag)[3], b'')
        original = json.loads(raw)
        updated = [dict(plan) for plan in original['plans']]
        updated[0]['price'] += 1
        headers = self.login()
        saved = self.request('POST', '/api/plans', {'plans': updated, 'version': original['version']}, headers)
        self.assertEqual(saved[0], 200)
        status, new_etag, _, raw = get(etag)
        self.assertEqual(status, 200)
        self.assertNotEqual(etag, new_etag)
        self.assertEqual(json.loads(raw)['plans'], updated)
        restored = self.request('POST', '/api/plans', {'plans': original['plans'], 'version': saved[2]['version']}, headers)
        self.assertEqual(restored[0], 200)

    def test_content_and_inbox_require_admin_and_csrf(self):
        self.assertEqual(self.request('GET','/api/consultations')[0],401)
        self.assertEqual(self.request('POST','/api/content',{})[0],401)
        self.assertEqual(self.request('POST','/api/upload',{})[0],401)
        headers=self.login()
        self.assertEqual(self.request('GET','/api/consultations',headers=headers)[0],200)
        original=self.request('GET','/api/content')[2]
        changed=json.loads(json.dumps(original))
        changed['content']['hotline']='0901234567'
        self.assertEqual(self.request('POST','/api/content',changed,{'Cookie':headers['Cookie']})[0],403)
        self.assertEqual(self.request('POST','/api/content',changed,headers)[0],200)
        self.assertEqual(self.request('GET','/api/content')[2]['content']['hotline'],'0901234567')
        self.assertEqual(self.request('POST','/api/content',changed,headers)[0],409)
        restored={**original,'version':original['version']+1}
        self.assertEqual(self.request('POST','/api/content',restored,headers)[0],200)

    def test_revisions_follow_committed_changes(self):
        before=self.request('GET','/api/revisions')[2]
        original=self.request('GET','/api/content')[2]
        headers=self.login()
        changed=json.loads(json.dumps(original))
        changed['content']['footer']='Footer revision test'
        self.assertEqual(self.request('POST','/api/content',changed,headers)[0],200)
        after=self.request('GET','/api/revisions')[2]
        self.assertEqual(after['content'],before['content']+1)
        self.assertEqual(after['plans'],before['plans'])
        # Rejected writes must not invalidate data.
        self.assertEqual(self.request('POST','/api/content',changed,headers)[0],409)
        self.assertEqual(self.request('GET','/api/revisions')[2],after)
        original['version']+=1
        self.assertEqual(self.request('POST','/api/content',original,headers)[0],200)
        for path in ['/admin/plans','/admin/settings','/admin/content/section-1','/admin/consultations']:
            conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
            conn.request('GET',path)
            response=conn.getresponse()
            self.assertEqual(response.status,200)
            self.assertIn(b'/admin.js',response.read())
            conn.close()

    def test_service_groups_crud_assignment_and_cache_revision(self):
        original=self.request('GET','/api/groups')[2]
        headers=self.login()
        self.assertEqual(len(original['groups']),6)
        self.assertEqual(self.request('POST','/api/groups',original)[0],401)
        self.assertEqual(self.request('POST','/api/groups',original,{'Cookie':headers['Cookie']})[0],403)
        before=self.request('GET','/api/plans')[2]
        custom={'id':'mobile-test','name':'Gói di động','description':'Dữ liệu thật','active':True}
        updated={'groups':[custom]+original['groups'],'version':original['version']}
        saved=self.request('POST','/api/groups',updated,headers)
        self.assertEqual(saved[0],200)
        self.assertEqual(self.request('POST','/api/groups',updated,headers)[0],409)
        public=self.request('GET','/api/plans')[2]
        self.assertEqual(public['groups'][0],custom)
        self.assertEqual(public['version'],before['version']+1)
        plan={'id':'custom-group-test','category':custom['id'],'name':'Gói 5G','duration':'30 ngày','price':90000,'details':'Internet','active':True}
        self.assertEqual(self.request('POST','/api/plans',{'plans':public['plans']+[plan],'version':public['version']},headers)[0],200)
        # Referenced groups cannot be removed, even when hidden.
        self.assertEqual(self.request('POST','/api/groups',{'groups':original['groups'],'version':saved[2]['version']},headers)[0],400)
        current=self.request('GET','/api/groups')[2]
        current['groups'][0]['active']=False
        self.assertEqual(self.request('POST','/api/groups',current,headers)[0],200)
        registration={'requestId':'hidden-group-test','name':'Test','email':'test@example.com','phone':'','products':['Gói di động'],'planId':plan['id'],'consent':True}
        self.assertEqual(self.request('POST','/api/registrations',registration)[0],400)
        invalid={'groups':[custom,custom],'version':current['version']+1}
        self.assertEqual(self.request('POST','/api/groups',invalid,headers)[0],400)
        public=self.request('GET','/api/plans')[2]
        self.assertEqual(self.request('POST','/api/plans',{'plans':before['plans'],'version':public['version']},headers)[0],200)
        current=self.request('GET','/api/groups')[2]
        self.assertEqual(self.request('POST','/api/groups',{'groups':original['groups'],'version':current['version']},headers)[0],200)
        self.assertEqual(self.request('GET','/api/groups')[2]['groups'],original['groups'])

    def test_private_files_and_cross_origin(self):
        for path in ['/.git/config','/server.py','/tests/test_server.py','/assets/../../server.py']:
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('POST','/api/login', {'password':self.password}, {'Origin':'https://other.example'})[0],403)
