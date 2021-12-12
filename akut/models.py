import pprint

from flask_login import UserMixin

from akut import login_db, extensions


class Association(login_db.Model):
    # id = login_db.Column(login_db.Integer, primary_key=True)
    user_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), primary_key=True)


class User(login_db.Model, UserMixin):
    id = login_db.Column(login_db.Integer, primary_key=True)
    username = login_db.Column(login_db.String(20), unique=True, nullable=False)
    email = login_db.Column(login_db.String(120), unique=True, nullable=False)
    image_file = login_db.Column(login_db.String(20), nullable=False, default='default.jpg')
    password = login_db.Column(login_db.String(60), nullable=False)
    regions = login_db.relationship('Association', backref='user',
                                    cascade="all,delete", lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Region(login_db.Model):
    id = login_db.Column(login_db.Integer, primary_key=True)
    name = login_db.Column(login_db.String(50), unique=True, nullable=False)
    users = login_db.relationship('Association', backref='region',
                                  cascade="all,delete", lazy=True)

    def __repr__(self):
        return f"Region('{self.name}')"


class LoggingMiddleware(object):
    def __init__(self, app):
        self._app = app

    def __call__(self, environ, resp):
        errorlog = environ['wsgi.errors']
        pprint.pprint(('REQUEST', environ['REQUEST_URI']), stream=errorlog)

        def log_response(status, headers, *args):
            pprint.pprint(('RESPONSE', status), stream=errorlog)
            return resp(status, headers, *args)

        return self._app(environ, log_response)


def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions
