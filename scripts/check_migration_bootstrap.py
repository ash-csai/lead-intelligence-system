import os
import tempfile
from pathlib import Path
from alembic.config import Config
from alembic import command
from app import create_app
import database.db_connection

root = Path(tempfile.mkdtemp())
db_path = root / 'test.db'
db_url = f'sqlite:///{db_path}'
os.environ['DATABASE_URL'] = db_url
database.db_connection.DB_NAME = db_url
app = create_app()
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = db_url

with app.app_context():
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option('sqlalchemy.url', db_url)
    command.upgrade(alembic_cfg, 'head')

print('database:', db_path)
print('seeded users:', app.extensions['sqlalchemy'].db.session.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="users"'))
