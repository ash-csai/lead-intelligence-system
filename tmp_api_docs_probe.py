
from flask import Flask
from flask_smorest import Api
from routes.api import api_bp
from database.db_connection import configure_db
from database.models import db
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///tmp_api.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['API_TITLE']='x'
app.config['API_VERSION']='v1'
app.config['OPENAPI_VERSION']='3.0.2'
app.config['OPENAPI_URL_PREFIX']='/api/v1/docs'
app.config['OPENAPI_JSON_PATH']='openapi.json'
app.config['OPENAPI_SWAGGER_UI_PATH']='/swagger'
app.config['OPENAPI_SWAGGER_UI_URL']='https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
configure_db(app)
api = Api(app)
api.register_blueprint(api_bp)
with app.test_client() as c:
    r = c.get('/api/v1/docs', follow_redirects=True)
    print(r.status_code)
    print(r.get_data(as_text=True))
