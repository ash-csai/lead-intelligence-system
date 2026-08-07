import os
import sys
from werkzeug.test import Client
from werkzeug.wrappers import Response

sys.path.insert(0, os.path.abspath('.'))
from app import create_app

app = create_app()
client = Client(app, Response)
resp = client.get('/analytics')
print('status_code=', resp.status_code)
text = resp.get_data(as_text=True)
print('contains_analytics=', 'analytics' in text.lower())
print('contains_analytics_title=', '<title' in text.lower())
