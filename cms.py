"""Persistent site content, consultation inbox and private banner upload."""
import base64
import io
import json
import os
import secrets
import time
import urllib.request
from pathlib import Path


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS site_content (id INTEGER PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL)')
    seed = (Path(__file__).parent/'data/content.json').read_text()
    db.execute('INSERT INTO site_content VALUES (1, ?, 1) ON CONFLICT (id) DO NOTHING', (seed,))
    db.execute('CREATE TABLE IF NOT EXISTS consultations (id TEXT PRIMARY KEY, body TEXT NOT NULL, status TEXT NOT NULL, email_status TEXT NOT NULL, email_id TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)')


def content(db):
    row = db.execute('SELECT body, version FROM site_content WHERE id=1').fetchone()
    return {'content': json.loads(row[0]), 'version': row[1]}


def validate(value):
    if not isinstance(value, dict) or set(value) != {'hotline', 'sections', 'footer'}:
        raise ValueError('Cấu trúc nội dung không hợp lệ.')
    if not isinstance(value['footer'],str) or len(value['footer'])>3000: raise ValueError('Footer không hợp lệ.')
    import re
    if not isinstance(value['hotline'], str) or not re.fullmatch(r'\+?[0-9]{9,15}', value['hotline']):
        raise ValueError('Hotline không hợp lệ.')
    if not isinstance(value['sections'], list) or len(value['sections']) > 50:
        raise ValueError('Quá nhiều mục.')
    ids = set()
    for section in value['sections']:
        if not isinstance(section.get('id'), str) or section['id'] in ids or not isinstance(section.get('title'), str):
            raise ValueError('Mục không hợp lệ.')
        ids.add(section['id'])
        if not isinstance(section.get('fields'), list) or len(section['fields']) > 500:
            raise ValueError('Danh sách nội dung không hợp lệ.')
        fields = set()
        for f in section['fields']:
            if type(f.get('id')) is not int or not 0<=f['id']<50000 or f['id'] in fields or f.get('tag') not in ['H1','H2','H3','P','A','SUMMARY','DIV','IMG','BUTTON','LI','SPAN','IFRAME']:
                raise ValueError('Trường nội dung không hợp lệ.')
            fields.add(f['id'])
            if f.get('answer') is not None and (not isinstance(f['answer'],str) or len(f['answer'])>10000): raise ValueError('Câu trả lời không hợp lệ.')
            if f.get('templateId') is not None and (type(f['templateId']) is not int or not 0<=f['templateId']<50000): raise ValueError('Mẫu không hợp lệ.')
            if type(f.get('active')) is not bool or type(f.get('order')) is not int or not isinstance(f.get('text'), str) or len(f['text']) > 10000:
                raise ValueError('Nội dung quá dài hoặc sai kiểu.')
            for key in ['href','mobile','desktop']:
                url=f.get(key)
                if url and (not isinstance(url,str) or not url.startswith(('https://','http://','/','#','tel:','mailto:','assets/'))):
                    raise ValueError('Liên kết không hợp lệ.')
            if f['tag']=='IFRAME' and not f['text'].startswith(('https://www.youtube.com/embed/','https://www.youtube-nocookie.com/embed/')): raise ValueError('Video cần liên kết YouTube embed.')
            if f['tag']=='IMG' and not f['text'].startswith(('https://','/','assets/')):
                raise ValueError('Ảnh không hợp lệ.')
    return value


def upload(data):
    from PIL import Image, ImageOps, UnidentifiedImageError
    token = os.environ.get('BLOB_READ_WRITE_TOKEN')
    if not token:
        raise ValueError('Chưa cấu hình Vercel Blob.')
    try:
        raw=base64.b64decode(data.get('image',''), validate=True)
        if len(raw)>2_500_000: raise ValueError()
        with Image.open(io.BytesIO(raw)) as original:
            if original.width*original.height>25000000: raise ValueError()
            image=ImageOps.exif_transpose(original).convert('RGB')
    except (ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValueError('Ảnh không hợp lệ; tối đa 2.5 MB và 25 megapixel.') from None
    result={}; prefix=secrets.token_hex(16)
    for kind,width in [('mobile',768),('desktop',1920)]:
        resized=image.copy();resized.thumbnail((width,1920))
        output=io.BytesIO();resized.save(output,'WEBP',quality=85)
        req=urllib.request.Request('https://blob.vercel-storage.com/banners/'+prefix+'-'+kind+'.webp',data=output.getvalue(),method='PUT',headers={'Authorization':'Bearer '+token,'Content-Type':'image/webp','x-api-version':'7','x-content-type':'image/webp','x-add-random-suffix':'0'})
        try:
            with urllib.request.urlopen(req,timeout=20) as response:
                result[kind]=json.load(response)['url']
        except Exception:
            raise ValueError('Không tải ảnh lên Blob được. Kiểm tra cấu hình và kết nối.') from None
    return result
