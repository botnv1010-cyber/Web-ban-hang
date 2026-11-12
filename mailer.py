"""Validated consultation notification via Resend; credentials stay server-side."""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request


class MailError(Exception):
    def __init__(self, message, code='send_failed'):
        super().__init__(message)
        self.code = code


def provider_error(error):
    # Inspect provider text for classification only; never expose its body or headers.
    try:
        body=json.loads(error.read(16384))
        message=str(body.get('message','')).lower()
    except (ValueError, OSError, AttributeError):
        message=''
    if error.code == 401:
        return MailError('RESEND_API_KEY không hợp lệ hoặc đã bị thu hồi. Kiểm tra key trong Vercel rồi Redeploy.', 'invalid_api_key')
    if error.code == 403:
        if any(word in message for word in ['testing emails', 'your own email', 'test emails']):
            return MailError('Resend đang ở chế độ thử nghiệm, chỉ gửi được tới email chủ tài khoản. Xác minh tên miền và dùng địa chỉ gửi thuộc tên miền đó.', 'resend_test_mode')
        if 'domain' in message and any(word in message for word in ['verif', 'not allowed']):
            return MailError('Tên miền của RESEND_FROM_EMAIL chưa được xác minh hoặc key không có quyền dùng tên miền này. Kiểm tra Domains trong Resend.', 'sender_domain')
        return MailError('Resend từ chối quyền gửi. Kiểm tra quyền API key, tên miền gửi và giới hạn tài khoản.', 'resend_forbidden')
    if error.code == 429:
        return MailError('Resend đang giới hạn tốc độ hoặc hạn mức gửi. Kiểm tra quota trong Resend.', 'resend_rate_limit')
    if error.code in (400,422):
        return MailError('Resend từ chối định dạng email. Kiểm tra RESEND_FROM_EMAIL và MAIL_TO trên Vercel.', 'email_validation')
    return MailError('Dịch vụ email trả lỗi HTTP '+str(error.code)+'. Kiểm tra Resend Logs và thử một yêu cầu mới sau khi khắc phục.', 'resend_http_'+str(error.code))


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
    if not isinstance(products, list) or not 1 <= len(products) <= 51 or any(not isinstance(p, str) or not 1 <= len(p) <= 150 for p in products):
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
    key = (os.environ.get('RESEND_API_KEY') or '').strip()
    sender = (os.environ.get('RESEND_FROM_EMAIL') or '').strip()
    recipient = item['email']
    if not key or not sender:
        raise MailError('Chức năng gửi email chưa được cấu hình. Vui lòng gọi 0975005123 để được hỗ trợ.')
    payload = {'from': sender, 'to': [recipient], 'reply_to': item['email'], 'subject': 'Đăng ký gói Viettel Đồng Nai — '+item['request_id'], 'text': item['text']}
    # A private copy notifies the business without exposing its inbox to customers.
    owner = os.environ.get('MAIL_TO', '').strip()
    if owner:
        if not re.fullmatch(r'[^\s@<>\r\n,;]+@[^\s@<>\r\n,;]+\.[^\s@<>\r\n,;]+', owner):
            raise MailError('MAIL_TO phải là một địa chỉ email, không kèm tên hiển thị hoặc danh sách dấu phẩy.', 'invalid_mail_to')
        if owner.casefold() != recipient.casefold():
            payload['bcc'] = [owner]
    raw = json.dumps(payload, ensure_ascii=False).encode()
    # Provider deduplication prevents a retry of the same submission sending twice.
    fingerprint = hashlib.sha256(raw).hexdigest()
    req = urllib.request.Request('https://api.resend.com/emails', data=raw, headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json', 'Accept':'application/json', 'User-Agent':'ViettelConsultations/1.0', 'Idempotency-Key': 'registration-'+fingerprint}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.load(response)
            if response.status not in (200, 201) or not isinstance(result, dict) or not isinstance(result.get('id'),str) or not result['id']:
                raise ValueError('Invalid provider response')
        return result['id']
    except urllib.error.HTTPError as error:
        raise provider_error(error) from None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        # Never expose API keys, provider response bodies or personal data in errors.
        raise MailError('Không kết nối được Resend hoặc phản hồi không hợp lệ. Kiểm tra trạng thái dịch vụ và kết nối của Vercel.', 'resend_connection') from None
