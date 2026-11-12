"""Ordered service groups, shared by catalog validation and the storefront."""
import json
import re

SEED = [
    {'id': key, 'name': name, 'description': '', 'active': True}
    for key, name in [('tendoo', 'Tendoo'), ('devices', 'Thiết bị Tendoo'), ('ca', 'Chữ ký số Viettel-CA'), ('invoice', 'Hóa đơn điện tử'), ('bh', 'Kê khai BHXH'), ('contract', 'Hợp đồng điện tử vContract')]
]


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS service_groups (id INTEGER PRIMARY KEY, body TEXT NOT NULL, version INTEGER NOT NULL)')
    db.execute('INSERT INTO service_groups VALUES (1, ?, 1) ON CONFLICT (id) DO NOTHING', (json.dumps(SEED, ensure_ascii=False),))


def read(db):
    row = db.execute('SELECT body, version FROM service_groups WHERE id=1').fetchone()
    return {'groups': json.loads(row[0]), 'version': row[1]}


def validate(groups):
    if not isinstance(groups, list) or not 1 <= len(groups) <= 50:
        raise ValueError('Cần từ 1 đến 50 nhóm dịch vụ.')
    ids = set()
    for group in groups:
        if not isinstance(group, dict) or set(group) != {'id', 'name', 'description', 'active'}:
            raise ValueError('Cấu trúc nhóm không hợp lệ.')
        if not isinstance(group['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,49}', group['id']) or group['id'] in ids:
            raise ValueError('Mã nhóm phải duy nhất, dùng chữ thường, số và dấu gạch ngang.')
        if not isinstance(group['name'], str) or not group['name'].strip() or len(group['name']) > 150:
            raise ValueError('Tên nhóm cần từ 1 đến 150 ký tự.')
        if not isinstance(group['description'], str) or len(group['description']) > 2000 or type(group['active']) is not bool:
            raise ValueError('Mô tả hoặc trạng thái nhóm không hợp lệ.')
        ids.add(group['id'])
    return groups
