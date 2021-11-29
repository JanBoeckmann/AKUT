import pprint

from flask_login import UserMixin

from akut import login_db, extensions


class User(login_db.Model, UserMixin):
    id = login_db.Column(login_db.Integer, primary_key=True)
    username = login_db.Column(login_db.String(20), unique=True, nullable=False)
    email = login_db.Column(login_db.String(120), unique=True, nullable=False)
    image_file = login_db.Column(login_db.String(20), nullable=False, default='default.jpg')
    password = login_db.Column(login_db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


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
