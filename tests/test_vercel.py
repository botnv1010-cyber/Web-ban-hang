import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

class VercelTest(unittest.TestCase):
    def test_missing_configuration_is_json(self):
        with tempfile.TemporaryDirectory() as temp, socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
            sock.close()
            env = {k:v for k,v in os.environ.items() if k not in ['ADMIN_PASSWORD','DATABASE_URL','POSTGRES_URL']}
            env['ADMIN_CREDENTIAL_FILE'] = temp+'/absent.json'
            code = "from api.index import handler; from http.server import HTTPServer; HTTPServer(('127.0.0.1', " + str(port) + "),handler).serve_forever()"
            process = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        urllib.request.urlopen(f'http://127.0.0.1:{port}/api/index?route=session')
                    except urllib.error.HTTPError as response:
                        self.assertEqual(response.code,503)
                        self.assertIn('application/json',response.headers['Content-Type'])
                        self.assertIn('DATABASE_URL',json.load(response)['error'])
                        break
                    except OSError:
                        time.sleep(.05)
                else:
                    self.fail('Function did not start')
            finally:
                process.terminate()
                process.wait(timeout=5)
