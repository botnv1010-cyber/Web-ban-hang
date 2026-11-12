"""Idempotent initialization. Requires DATABASE_URL for a non-production Neon branch."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if not (os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')):
    raise SystemExit('Set DATABASE_URL to your Neon connection string (sslmode=require).')
import server
server.initialize()
print('Initialized catalog, content, sessions and consultations; existing edits preserved.')
