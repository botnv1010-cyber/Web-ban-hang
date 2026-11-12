import http.client
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from http.server import ThreadingHTTPServer
import urllib.error
import mailer
import server


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = patch.object(server, 'DB', Path(self.temp.name)/'catalog.sqlite')
        self.url = patch.object(server, 'DATABASE_URL', None)
        self.db.start()
        self.url.start()
        server.initialize()
        self.http = ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.data = {'requestId':'test-request-1234','name':'Khách kiểm thử','phone':'0975005123','email':'customer@example.com','products':['Tendoo'],'planId':'tendoo-plans-0','consent':True,'website':''}

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.url.stop()
        self.db.stop()
        self.temp.cleanup()

    def post(self,data):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        conn.request('POST','/api/registrations',json.dumps(data),{'Content-Type':'application/json'})
        res=conn.getresponse()
        status, body=res.status,json.load(res)
        conn.close()
        return status,body

    def test_selected_package_and_provider_success(self):
        with patch.dict(os.environ,{'RESEND_API_KEY':'test','RESEND_FROM_EMAIL':'sender@example.com'}), patch('mailer.send_registration_email',return_value='email-id') as send:
            status,result=self.post({**self.data,'price':1,'details':'fake price'})
            self.assertEqual(status,200)
            self.assertTrue(result['success'])
            text=send.call_args.args[0]['text']
            self.assertIn('5.248.800 VNĐ',text)
            self.assertIn('Khách kiểm thử',text)
            self.assertNotIn('fake price',text)

    def test_failure_preserves_request(self):
        with patch.dict(os.environ,{'RESEND_API_KEY':'test','RESEND_FROM_EMAIL':'sender@example.com'}), patch('mailer.send_registration_email',side_effect=mailer.MailError('Không gửi được email.')):
            status,result=self.post(self.data)
            self.assertEqual(status,200)
            self.assertTrue(result['success'])
            self.assertEqual(result['emailStatus'],'Gửi lỗi')
            with server.connect() as db:
                self.assertEqual(db.execute('SELECT email_status FROM consultations').fetchone()[0],'Gửi lỗi')
                self.assertEqual(db.execute('SELECT code,message FROM consultation_email_errors').fetchone(),('send_failed','Không gửi được email.'))
            self.assertNotIn('emailError',result)

    def test_invalid_and_hidden_packages_do_not_send(self):
        with patch('mailer.send_registration_email') as send:
            for updates in [{'consent':False},{'email':'bad\r\naddress'},{'planId':'removed'},{'website':'spam'}]:
                self.assertEqual(self.post({**self.data,**updates})[0],400)
            with server.connect() as db:
                plans=json.loads(db.execute('SELECT body FROM catalog WHERE id=1').fetchone()[0])
                for p in plans:
                    if p['id']==self.data['planId']:p['active']=False
                db.execute('UPDATE catalog SET body=? WHERE id=1',(json.dumps(plans),))
            self.assertEqual(self.post(self.data)[0],400)
            send.assert_not_called()

    def test_rate_limit(self):
        with patch('mailer.send_registration_email'):
            for _ in range(5):self.assertEqual(self.post(self.data)[0],200)
            self.assertEqual(self.post(self.data)[0],429)


class ProviderTest(unittest.TestCase):
    def test_provider_errors_are_classified_without_exposing_body(self):
        cases=[(401,'API key invalid secret123','invalid_api_key'),(403,'You can only send testing emails to your own email secret123','resend_test_mode'),(403,'Domain secret123 is not verified','sender_domain'),(422,'invalid secret123','email_validation'),(429,'limit secret123','resend_rate_limit'),(503,'outage secret123','resend_http_503')]
        for status,message,code in cases:
            with self.subTest(status=status,code=code):
                error=urllib.error.HTTPError('https://api.resend.com/emails',status,'error',{},io.BytesIO(json.dumps({'message':message}).encode()))
                with patch.dict(os.environ,{'RESEND_API_KEY':'test','RESEND_FROM_EMAIL':'sender@example.com','MAIL_TO':'owner@example.com'}),patch('urllib.request.urlopen',side_effect=error):
                    with self.assertRaises(mailer.MailError) as failure:
                        mailer.send_registration_email({'email':'customer@example.com','request_id':'test-request','text':'Consultation'})
                self.assertEqual(failure.exception.code,code)
                self.assertNotIn('secret123',str(failure.exception))

    def test_provider_payload_and_idempotency(self):
        item={'request_id':'test-request-1234','email':'customer@example.com','text':'Thông tin gói'}
        response=MagicMock()
        response.status=200
        response.read.return_value=b'{"id":"provider-message-id"}'
        context=MagicMock()
        context.__enter__.return_value=response
        with patch.dict(os.environ,{'RESEND_API_KEY':'test-not-a-real-key','RESEND_FROM_EMAIL':'sender@example.com','MAIL_TO':'admin@example.com'}),patch('urllib.request.urlopen',return_value=context) as send:
            mailer.send_registration_email(item)
            mailer.send_registration_email(item)
            first, second=[call.args[0] for call in send.call_args_list]
            self.assertEqual(first.get_header('Idempotency-key'),second.get_header('Idempotency-key'))
            payload=json.loads(first.data)
            self.assertEqual(payload['to'],['customer@example.com'])
            self.assertEqual(payload['bcc'],['admin@example.com'])
            self.assertEqual(payload['reply_to'],'customer@example.com')
        with patch.dict(os.environ,{'RESEND_API_KEY':'test','RESEND_FROM_EMAIL':'sender@example.com','MAIL_TO':''}),patch('urllib.request.urlopen',return_value=context) as send:
            mailer.send_registration_email(item)
            self.assertNotIn('bcc',json.loads(send.call_args.args[0].data))
        with patch.dict(os.environ,{'RESEND_API_KEY':'test','RESEND_FROM_EMAIL':'sender@example.com','MAIL_TO':'bad\r\naddress'}),patch('urllib.request.urlopen') as send:
            with self.assertRaises(mailer.MailError):mailer.send_registration_email(item)
            send.assert_not_called()
        with patch.dict(os.environ,{'RESEND_API_KEY':'','RESEND_FROM_EMAIL':''}):
            with self.assertRaises(mailer.MailError):mailer.send_registration_email(item)
