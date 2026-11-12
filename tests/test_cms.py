import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import cms
import server
import test_mailer


class ContentTest(unittest.TestCase):
    def test_seed_does_not_overwrite_edits(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(server,'DB',Path(folder)/'test.sqlite'),patch.object(server,'DATABASE_URL',None):
            server.initialize()
            with server.connect() as db:
                data=cms.content(db)['content'];cms.validate(data)
                data['hotline']='0901234567'
                db.execute('UPDATE site_content SET body=?,version=version+1 WHERE id=1',(json.dumps(data),))
            server.initialize()
            with server.connect() as db:self.assertEqual(cms.content(db)['content']['hotline'],'0901234567')

    def test_group_initialization_preserves_edits(self):
        import service_groups
        with tempfile.TemporaryDirectory() as folder, patch.object(server,'DB',Path(folder)/'test.sqlite'),patch.object(server,'DATABASE_URL',None):
            server.initialize()
            with server.connect() as db:
                data=service_groups.read(db)
                data['groups'][0]['name']='Nhóm đã sửa'
                db.execute('UPDATE service_groups SET body=?,version=version+1 WHERE id=1',(json.dumps(data['groups']),))
            server.initialize()
            with server.connect() as db:self.assertEqual(service_groups.read(db)['groups'][0]['name'],'Nhóm đã sửa')

    def test_corrupt_image_is_rejected_before_upload(self):
        with patch.dict(os.environ,{'BLOB_READ_WRITE_TOKEN':'fake-test'}),patch('urllib.request.urlopen') as send:
            with self.assertRaises(ValueError):cms.upload({'image':base64.b64encode(b'not an image').decode()})
            send.assert_not_called()

    def test_upload_produces_two_valid_webps(self):
        from PIL import Image
        source=io.BytesIO();Image.new('RGB',(2400,1200),'red').save(source,'PNG')
        response=MagicMock();response.read.return_value=b'{"url":"https://test.public.blob.vercel-storage.com/banner.webp"}'
        context=MagicMock();context.__enter__.return_value=response
        with patch.dict(os.environ,{'BLOB_READ_WRITE_TOKEN':'fake-test'}),patch('urllib.request.urlopen',return_value=context) as send:
            result=cms.upload({'image':base64.b64encode(source.getvalue()).decode()})
            self.assertEqual(set(result),{'mobile','desktop'})
            widths=[]
            for call in send.call_args_list:
                image=Image.open(io.BytesIO(call.args[0].data));self.assertEqual(image.format,'WEBP');widths.append(image.width)
            self.assertEqual(widths,[768,1920])


class InboxTest(unittest.TestCase):
    setUp=test_mailer.RegistrationTest.setUp
    tearDown=test_mailer.RegistrationTest.tearDown
    post=test_mailer.RegistrationTest.post
    def test_missing_email_config_keeps_request_and_optional_phone(self):
        with patch.dict(os.environ,{'RESEND_API_KEY':'','RESEND_FROM_EMAIL':''}):
            status,result=self.post({**self.data,'phone':''})
        self.assertEqual(status,200);self.assertEqual(result['emailStatus'],'Chưa cấu hình email')
        with server.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM consultations').fetchone()[0],1)
        self.assertEqual(self.post({**self.data,'phone':''})[0],200)
        with server.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM consultations').fetchone()[0],1)
