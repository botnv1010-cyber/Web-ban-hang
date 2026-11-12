"""Validated consultation notification via Resend; credentials stay server-side."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request


class MailError(Exception):
    pass


def registration(data, plans):
    def text(key, limit, required=True):
        value = data.get(key, '')
        if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
            raise ValueError('Vui lòng kiểm tra thông tin đăng ký.')
        return value.strip()
    name = text('name', 100)
    phone = text('phone', 20, False)
    email = text('email', 200)
    request_id = text('requestId', 100)
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', request_id):
        raise ValueError('Mã đăng ký không hợp lệ.')
    if phone and (not re.fullmatch(r'[+0-9 ()-]{9,20}', phone) or len(re.sub(r'\D', '', phone)) < 9):
        raise ValueError('Số điện thoại không hợp lệ.')
    if not re.fullmatch(r'[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+', email):
        raise ValueError('Email không hợp lệ.')
    if data.get('consent') is not True:
        raise ValueError('Vui lòng đồng ý để bộ phận tư vấn liên hệ.')
    products = data.get('products')
    if not isinstance(products, list) or not 1 <= len(products) <= 6 or any(not isinstance(p, str) or not 1 <= len(p) <= 150 for p in products):
        raise ValueError('Vui lòng chọn giải pháp cần tư vấn.')
    selected = None
    plan_id = data.get('planId')
    if plan_id:
        selected = next((p for p in plans if p['id'] == plan_id and p['active']), None)
        if selected is None:
            raise ValueError('Gói đã thay đổi hoặc ngừng hiển thị. Vui lòng chọn lại gói.')
    lines = [f'Mã đăng ký: {request_id}', f'Họ và tên: {name}', f'Số điện thoại: {phone}', f'Email: {email}', 'Giải pháp quan tâm: '+', '.join(products), 'Đồng ý liên hệ tư vấn: Có']
    if selected:
        lines.extend([f"Mã gói: {selected['id']}", f"Gói đăng ký: {selected['name']}", f"Giá: {selected['price']:,} VNĐ".replace(',', '.'), f"Thời hạn / Bảo hành: {selected['duration']}", 'Chi tiết gói:', selected['details']])
    return {'request_id': request_id, 'email': email, 'text': '\n'.join(lines)}


def send_registration_email(item):
    key = os.environ.get('RESEND_API_KEY')
    sender = os.environ.get('RESEND_FROM_EMAIL')
    recipient = item['email']
    if not key or not sender:
        raise MailError('Chức năng gửi email chưa được cấu hình. Vui lòng gọi 0975005123 để được hỗ trợ.')
    payload = {'from': sender, 'to': [recipient], 'reply_to': item['email'], 'subject': 'Đăng ký gói Viettel Đồng Nai — '+item['request_id'], 'text': item['text']}
    raw = json.dumps(payload, ensure_ascii=False).encode()
    # Provider deduplication prevents a retry of the same submission sending twice.
    fingerprint = hashlib.sha256(raw).hexdigest()
    req = urllib.request.Request('https://api.resend.com/emails', data=raw, headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json', 'Idempotency-Key': 'registration-'+fingerprint}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.load(response)
            if response.status not in (200, 201) or not isinstance(result, dict) or not result.get('id'):
                raise ValueError('Invalid provider response')
        return result['id']
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        # Never expose API keys, provider response bodies or personal data in errors.
        raise MailError('Chưa xác nhận được kết quả gửi email. Vui lòng thử lại hoặc gọi 0975005123.') from None
