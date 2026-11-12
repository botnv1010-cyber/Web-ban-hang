"""Publish an explicit allowlist; never copy backend source or private files."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
output = root / 'public'
output.mkdir(exist_ok=True)
for name in ['index.html', 'admin.html', 'admin.css', 'admin.js', 'catalog.js', 'content.js', 'cms-admin.js', 'site-sync.js', 'image-upload.js']:
    shutil.copy2(root / name, output / name)
for name in ['assets', 'data']:
    shutil.copytree(root / name, output / name, dirs_exist_ok=True)
