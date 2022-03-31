import pprint

from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from datetime import datetime

from akut import login_db, app


class LoggingMiddleware(object):
    def __init__(self, application):
        self._app = application

    def __call__(self, environ, resp):
        errorlog = environ['wsgi.errors']
        pprint.pprint(('REQUEST', environ['REQUEST_URI']), stream=errorlog)

        def log_response(status, headers, *args):
            pprint.pprint(('RESPONSE', status), stream=errorlog)
            return resp(status, headers, *args)

        return self._app(environ, log_response)


class User_Region(login_db.Model):
    __tablename__ = 'user_region'
    access = login_db.Column(login_db.Text, nullable=False, default='All')
    date_associated = login_db.Column(login_db.DateTime, nullable=False, default=datetime.utcnow)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), primary_key=True)
    user_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), primary_key=True)
    provided_by_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), default=None)


class Messages(login_db.Model):
    id = login_db.Column(login_db.Integer, primary_key=True)
    user_to_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), nullable=False)
    user_from_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), nullable=False)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False)
    date_associated = login_db.Column(login_db.DateTime, nullable=False, default=datetime.utcnow)
    type = login_db.Column(login_db.String, nullable=False)
    text = login_db.Column(login_db.String, default="")

    def __str__(self):
        region = Region.query.filter_by(id=self.region_id).first()
        if not region:  # Gelöschte Region
            return 'Ignore Message'
        region_name = region.name
        user_name = User.query.filter_by(id=self.user_from_id).first().username
        if not user_name:
            user_name = '[Gelöschter User]'
        if self.type == "Freigegeben":
            return f'User "{user_name}" hat Ihnen die Region "{region_name}" am {str(self.date_associated)[0:9]}' \
                   f' freigegeben! {self.text}'
        elif self.type == "Admin abgegeben":
            return f'User "{user_name}" hat Ihnen den Admin der Region "{region_name}" am ' \
                   f'{str(self.date_associated)[0:9]} abgegeben! {self.text}'


class User(login_db.Model, UserMixin):
    id = login_db.Column(login_db.Integer, primary_key=True)
    username = login_db.Column(login_db.String(20), unique=True, nullable=False)
    email = login_db.Column(login_db.String(120), unique=True, nullable=False)
    image_file = login_db.Column(login_db.String(20), nullable=False, default='default.jpg')
    password = login_db.Column(login_db.String(60), nullable=False)
    admin_regions = login_db.relationship('Region', backref='admin', lazy=True)
    regions = login_db.relationship('User_Region', backref='user', foreign_keys=User_Region.user_id,
                                    cascade='all, delete', lazy=True)
    provided = login_db.relationship('User_Region', backref='provider', foreign_keys=User_Region.provided_by_id,
                                     lazy=True)
    messages_recieved = login_db.relationship('Messages', backref='recipient', foreign_keys=Messages.user_to_id,
                                              lazy=True)
    messages_sent = login_db.relationship('Messages', backref='transmitter', foreign_keys=Messages.user_from_id,
                                          lazy=True)

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
    admin_id = login_db.Column(login_db.Integer, login_db.ForeignKey('user.id'), default=None)

    messages = login_db.relationship('Messages', backref='region', lazy=True)
    dgm1s = login_db.relationship('DGM1', backref='region_dgm1s', lazy=True)
    dgm5s = login_db.relationship('DGM5', backref='region_dgm5s', lazy=True)
    dgm25s = login_db.relationship('DGM25', backref='region_dgm25s', lazy=True)
    auffangbecken = login_db.relationship('Auffangbecken', backref='region_auffangbecken', lazy=True)
    data = login_db.relationship('Data', backref='region_data', lazy=True)
    databuildings = login_db.relationship('DataBuildings', backref='region_databuildings', lazy=True)
    einzugsgebiete = login_db.relationship('Einzugsgebiete', backref='region_einzugsgebiete', lazy=True)
    header = login_db.relationship('Header', backref='region_header', lazy=True)
    kataster = login_db.relationship('Kataster', backref='region_kataster', lazy=True)
    leitgraeben = login_db.relationship('Leitgraeben', backref='region_leitgraeben', lazy=True)
    massnahme_kataster_mapping = login_db.relationship('MassnahmenKatasterMapping',
                                                       backref='region_massnahme_kataster_mapping', lazy=True)
    optimization_parameters = login_db.relationship('OptimizationParameters', backref='region_optimization_parameters',
                                                    lazy=True)
    solutions = login_db.relationship('Solutions', backref='region_solutions', lazy=True)

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


class DGM1(login_db.Model):
    __tablename__ = 'regionsDGM1'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Float)
    yCoord = login_db.Column(login_db.Float)
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    resolveFurther = login_db.Column(login_db.Integer)
    willBeInGraph = login_db.Column(login_db.Integer)


class DGM5(login_db.Model):
    __tablename__ = 'regionsDGM5'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Float)
    yCoord = login_db.Column(login_db.Float)
    gridPolyline = login_db.Column(login_db.Text)
    mitMassnahme = login_db.Column(login_db.Text)
    relevantForGraph = login_db.Column(login_db.Integer)
    connectedToRelevantNodes = login_db.Column(login_db.Integer)
    massnahmeOnNode = login_db.Column(login_db.Text)
    resolveFurther = login_db.Column(login_db.Integer)
    willBeInGraph = login_db.Column(login_db.Integer)


class DGM25(login_db.Model):
    __tablename__ = 'regionsDGM25'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer)
    xutm = login_db.Column(login_db.Integer, primary_key=True)
    yutm = login_db.Column(login_db.Integer, primary_key=True)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Float)
    yCoord = login_db.Column(login_db.Float)
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
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    depth = login_db.Column(login_db.Float)
    cost = login_db.Column(login_db.Float)
    costAnreize = login_db.Column(login_db.Float)


class Data(login_db.Model):
    __tablename__ = 'regionsData'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    utmRight = login_db.Column(login_db.Integer)
    utmUp = login_db.Column(login_db.Integer)
    posRight = login_db.Column(login_db.Integer)
    posUp = login_db.Column(login_db.Integer)
    geodesicHeight = login_db.Column(login_db.Integer)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    xCoord = login_db.Column(login_db.Float)  # Float in DGM
    yCoord = login_db.Column(login_db.Float)  # Float in DGM
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
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    properties = login_db.Column(login_db.Text)
    active = login_db.Column(login_db.Integer)
    akteur = login_db.Column(login_db.Text)
    gebaeudeklasse = login_db.Column(login_db.Integer)
    schadensklasse = login_db.Column(login_db.Integer)
    objektschutzActive = login_db.Column(login_db.Integer)
    objektschutzCost = login_db.Column(login_db.Float)


class Einzugsgebiete(login_db.Model):
    __tablename__ = 'regionsEinzugsgebiete'
    region = login_db.Column(login_db.Integer, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    xCoord = login_db.Column(login_db.Float)
    yCoord = login_db.Column(login_db.Float)


class Header(login_db.Model):
    __tablename__ = 'regionsHeader'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    uploaded = login_db.Column(login_db.Integer)
    date_uploaded = login_db.Column(login_db.Text)
    solved = login_db.Column(login_db.Integer)
    data_solved = login_db.Column(login_db.Text)
    timeHorizon = login_db.Column(login_db.Integer)
    gridSize = login_db.Column(login_db.Float)
    rainAmount = login_db.Column(login_db.Float)
    rainDuration = login_db.Column(login_db.Float)
    center_lat = login_db.Column(login_db.Float)
    center_lon = login_db.Column(login_db.Float)


class Kataster(login_db.Model):
    __tablename__ = 'regionsKataster'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    inEinzugsgebiete = login_db.Column(login_db.Integer)
    additionalCost = login_db.Column(login_db.Float)
    cooperation = login_db.Column(login_db.Integer)
    akteur = login_db.Column(login_db.Text)


class Leitgraeben(login_db.Model):
    __tablename__ = 'regionsLeitgraeben'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    position = login_db.Column(login_db.Text)
    depth = login_db.Column(login_db.Float)
    cost = login_db.Column(login_db.Float)
    costAnreize = login_db.Column(login_db.Float)
    leitgrabenOderBoeschung = login_db.Column(login_db.Text)


class MassnahmenKatasterMapping(login_db.Model):
    __tablename__ = 'regionsMassnahmenKatasterMapping'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    artMassnahme = login_db.Column(login_db.Text, primary_key=True)
    massnahmeId = login_db.Column(login_db.Integer, primary_key=True)
    katasterId = login_db.Column(login_db.Integer, primary_key=True)


class OptimizationParameters(login_db.Model):
    __tablename__ = 'regionsOptimizationParameters'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    parameterId = login_db.Column(login_db.Text, primary_key=True)
    parameterName = login_db.Column(login_db.Text, primary_key=True)
    parameterValue = login_db.Column(login_db.Float)


class Solutions(login_db.Model):
    __tablename__ = 'regionsSolution'
    region = login_db.Column(login_db.Text, primary_key=True)
    region_id = login_db.Column(login_db.Integer, login_db.ForeignKey('region.id'), nullable=False, primary_key=True)
    variableName = login_db.Column(login_db.Text, primary_key=True)
    timeStep = login_db.Column(login_db.Integer, primary_key=True)
    id = login_db.Column(login_db.Integer, primary_key=True)
    nodeXCoord = login_db.Column(login_db.Integer)
    nodeYCoord = login_db.Column(login_db.Integer)
    variableVale = login_db.Column(login_db.Float)


'''
class GraphNodes(login_db.Model):
    region = login_db.Column(login_db.Text, primary_key=True)
    nodeNumberXCoord = login_db.Column(login_db.Integer, primary_key=True)
    nodeNumberyCoord = login_db.Column(login_db.Integer, primary_key=True)


class GraphEdges(login_db.Model):
    region = login_db.Column(login_db.Text, primary_key=True)
    sourceNodeNumberXCoord = login_db.Column(login_db.Integer, primary_key=True)
    sourceNodeNumberyCoord = login_db.Column(login_db.Integer, primary_key=True)
    sinkNodeNumberXCoord = login_db.Column(login_db.Integer, primary_key=True)
    sinkNodeNumberyCoord = login_db.Column(login_db.Integer, primary_key=True)
'''
