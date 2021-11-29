from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from werkzeug.utils import secure_filename
import pprint
from datetime import *
from akut.databaseHandler import *

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "akut/csv")
extensions = set(['txt', 'csv', 'geojson', 'dxf', 'xml', 'shp', 'xyz'])
geosteps = 25
timeSteps = 6
rain = 0.6

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zZ~AutfD*%ay#7AfxSMn'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.db'
login_db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
from akut.models import User
from akut.forms import RegistrationForm, LoginForm
from akut import routes


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
