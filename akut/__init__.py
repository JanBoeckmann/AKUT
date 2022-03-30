from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
import os

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")
extensions = set(['txt', 'csv', 'geojson', 'dxf', 'xml', 'shp', 'xyz', "zip"])
geosteps = 25
timeSteps = 6
rain = 0.6

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zZ~AutfD*%ay#7AfxSMn'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///login.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
# TODO: Mailserver
# app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
# app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
mail = Mail(app)
from akut.models import *
from akut.forms import RegistrationForm, LoginForm, RequestResetForm, ResetPasswordForm
from akut.LoginDbHandler import *
from akut.databaseHandler import *
from akut import routes


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
