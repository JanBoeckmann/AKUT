import pprint

from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime

from akut import login_db, extensions, app


def allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


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


class User_Region(login_db.Model):
    __tablename__ = 'user_region'
    user_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), primary_key=True)
    access = login_db.Column(login_db.Text, nullable=False, default='All')
    provided_by = login_db.Column(login_db.Text, nullable=False, default='None')
    date_associated = login_db.Column(login_db.DateTime, nullable=False, default=datetime.utcnow)


class User(login_db.Model, UserMixin):
    id = login_db.Column(login_db.Integer, primary_key=True)
    username = login_db.Column(login_db.String(20), unique=True, nullable=False)
    email = login_db.Column(login_db.String(120), unique=True, nullable=False)
    image_file = login_db.Column(login_db.String(20), nullable=False, default='default.jpg')
    password = login_db.Column(login_db.String(60), nullable=False)
    regions = login_db.relationship('User_Region', backref='user', cascade='all, delete', lazy=True)  # backref = region
    admin_regions = login_db.relationship('Region', backref='admin', lazy=True)

    """
    def deleteUser(self):
        # Wenn ein Admin einer Region:
            Admin an User übergeben, der die Region am längsten hat
        User löschen
    """

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"


class Region(login_db.Model):
    id = login_db.Column(login_db.Integer, primary_key=True)
    name = login_db.Column(login_db.String(50), unique=True, nullable=False)
    users = login_db.relationship('User_Region', backref='region', cascade='all, delete', lazy=True)
    admin_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Region('{self.name}')"


class GlobalToAkteur(login_db.Model):
    __tablename__ = 'globalGebaeudeklasseToAkteur'
    gebaeudeklasse = login_db.Column(login_db.Integer, primary_key=True)
    akteur = login_db.Column(login_db.Text, primary_key=True)


class GlobalToSchadensklasse(login_db.Model):
    __tablename__ = 'globalGebaeudeklasseToSchadensklasse'
    gebaeudeklasse = login_db.Column(login_db.Integer, primary_key=True)
    schadensklasse = login_db.Column(login_db.Integer, primary_key=True)


class GlobalForGefahrensklasse(login_db.Model):
    __tablename__ = 'globalThreshholdForGefahrensklasse'
    gefahrenklasse = login_db.Column(login_db.Integer, primary_key=True)
    threshhold = login_db.Column(login_db.Integer, primary_key=True)


class DGMI1(login_db.Model):
    __tablename__ = 'regionsDGM1'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Numeric)
    yCoord = login_db.Column(login_db.Numeric)
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    resolveFurther = login_db.Column(login_db.Integer)
    willBeInGraph = login_db.Column(login_db.Integer)


class DGMI5(login_db.Model):
    __tablename__ = 'regionsDGM5'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Numeric)
    yCoord = login_db.Column(login_db.Numeric)
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    resolveFurther = login_db.Column(login_db.Integer)
    willBeInGraph = login_db.Column(login_db.Integer)


class DGMI25(login_db.Model):
    __tablename__ = 'regionsDGM25'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Numeric)
    yCoord = login_db.Column(login_db.Numeric)
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    resolveFurther = login_db.Column(login_db.Integer)
    willBeInGraph = login_db.Column(login_db.Integer)


class Auffangbecken(login_db.Model):
    __tablename__ = 'regionsAuffangbecken'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    depth = login_db.Column(login_db.Numeric)
    cost = login_db.Column(login_db.Numeric)
    costAnreize = login_db.Column(login_db.Numeric)


class Data(login_db.Model):
    __tablename__ = 'regionsData'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    utmRight = login_db.Column(login_db.Integer)
    utmUp = login_db.Column(login_db.Integer)
    posRight = login_db.Column(login_db.Integer)
    posUp = login_db.Column(login_db.Integer)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Float)  # Numeric in DGM
    yCoord = login_db.Column(login_db.Float)  # Numeric in DGM
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    # resolveFurther = login_db.Column(login_db.Integer)
    # willBeInGraph = login_db.Column(login_db.Integer)


class DataBuildings(login_db.Model):
    __tablename__ = 'regionsDataBuildings'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    propertis = login_db.Column(login_db.Text)
    active = login_db.Column(login_db.Integer)
    akteuer = login_db.Column(login_db.Text)
    gebaeudeklasse = login_db.Column(login_db.Integer)
    schadensklasse = login_db.Column(login_db.Integer)
    objektschutzActive = login_db.Column(login_db.Integer)
    objektschutzCost = login_db.Column(login_db.Numeric)


class Einzugsgebiete(login_db.Model):
    __tablename__ = 'regionsEinzugsgebiete'
    region = login_db.Column(login_db.Integer, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    xCoord = login_db.Column(login_db.Numeric)
    yCoord = login_db.Column(login_db.Numeric)


class Header(login_db.Model):
    __tablename__ = 'regionsHeader'
    region = login_db.Column(login_db.Text, primary_key=True)
    uploaded = login_db.Column(login_db.Integer)
    date_uploaded = login_db.Column(login_db.Text)
    solved = login_db.Column(login_db.Integer)
    data_solved = login_db.Column(login_db.Text)
    timeHorizon = login_db.Column(login_db.Integer)
    gridSize = login_db.Column(login_db.Numeric)
    rainAmont = login_db.Column(login_db.Numeric)
    rainDuration = login_db.Column(login_db.Numeric)
    center_lat = login_db.Column(login_db.Numeric)
    center_lon = login_db.Column(login_db.Numeric)


class Kataster(login_db.Model):
    __tablename__ = 'regionsKataster'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    additionalCost = login_db.Column(login_db.Numeric)
    cooperation = login_db.Column(login_db.Integer)
    akteur = login_db.Column(login_db.Text)


class Leitgraeben(login_db.Model):
    __tablename__ = 'regionsLeitgraeben'
    region = login_db.Column(login_db.Text, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    depth = login_db.Column(login_db.Numeric)
    cost = login_db.Column(login_db.Numeric)
    costAnreize = login_db.Column(login_db.Numeric)
    leitgrabenOderBoeschung = login_db.Column(login_db.Text)


class MassnahmenKatasterMapping(login_db.Model):
    __tablename__ = 'regionsMassnahmenKatasterMapping'
    region = login_db.Column(login_db.Text, primary_key=True)
    artMassnahme = login_db.Column(login_db.Text, primary_key=True)
    massnahmeId = login_db.Column(login_db.Integer, primary_key=True)
    katasterId = login_db.Column(login_db.Integer, primary_key=True)


class OptimizationParameters(login_db.Model):
    __tablename__ = 'regionsOptimizationParameters'
    region = login_db.Column(login_db.Text, primary_key=True)
    parameterId = login_db.Column(login_db.Text, primary_key=True)
    parameterName = login_db.Column(login_db.Text, primary_key=True)
    parameterValue = login_db.Column(login_db.Numeric)


class Solutions(login_db.Model):
    __tablename__ = 'regionsSolution'
    region = login_db.Column(login_db.Text, primary_key=True)
    variableName = login_db.Column(login_db.Text, primary_key=True)
    timeStep = login_db.Column(login_db.Integer, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    nodeXCoord = login_db.Column(login_db.Integer)
    nodeYCoord = login_db.Column(login_db.Integer)
    variableVale = login_db.Column(login_db.Float)
