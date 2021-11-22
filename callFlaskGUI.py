from flask import Flask, url_for, request, render_template, redirect, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from werkzeug.utils import secure_filename
import pprint
import os
import json
from datetime import *
from gisDataToInstance import *
from ipEquilibriumWaterLevels import *
from databaseHandler import *

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv")
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

class User(login_db.Model, UserMixin):
    id = login_db.Column(login_db.Integer, primary_key=True)
    username = login_db.Column(login_db.String(20), unique=True, nullable=False)
    email = login_db.Column(login_db.String(120), unique=True, nullable=False)
    image_file = login_db.Column(login_db.String(20), nullable=False, default='default.jpg')
    password = login_db.Column(login_db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from forms import RegistrationForm, LoginForm # circular import

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

@app.route("/")
def index():
    return "Hello, this is still under construction"

@app.route("/landingPage")
def landingPage():
    return render_template("landingPage.html", title='Das Beratungstool', landing='true')

# <- TODO ->
# - !Templates "aufraeumen" mit Vererbung (mehrfach), ansonsten flash-messages andere templates; kein title; nicht weniger templates
# - 1x datenbank-erstellung mit login_db.create_all() nötig gewesen? > passt
# - landing page ohne zurueck -> über templates (landingpage_layout oder so)
# - !url_for bei links > macht sinn
# - account-seite (Vid-7) erstmal nich
# - remember me funktion > egal
# - welche seiten nur mit login zugreifbar? > alles außer register/login // regionen nur für nutzer, die hochgeladen haben & filter // admin-user; exra tabelle user_region (rastergr. 1 hardcoden) in login..db
# - Bar oben einheitlich (erstmal lassen), stylesheet-version
# - !circular imports / package -> packacge!

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landingPage'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('landingPage'))
        else:
            flash('Login fehlgeschlagen. Bitte überprüfe E-Mail and Passwort.', 'danger')
    return render_template("login.html", title='Login', landing='false', form=form)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('landingPage'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_pw)
        login_db.session.add(user)
        login_db.session.commit()
        flash(f'Account erstellt für {form.username.data}!', 'success')
        return redirect(url_for('login'))
    return render_template("register.html", title='Registrierung', landing='false', form=form)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('landingPage'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    return render_template("account.html", title='Account', landing='false')

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if allowed(file.filename):
            filename = secure_filename(file.filename)
        else:
            return redirect(request.url)
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        if(request.form.get("reuseFile") is None):
            file.save(os.path.join(folder, filename))
        #myDatabaseHandler.writeUploadedDataToDatabase(folder, filename, float(request.form.get("gridSize")))
        myDatabaseHandler.writeUploadedDataToDGM1(folder, filename, float(request.form.get("gridSize")), request.form.get("reuseFile"))
        myDatabaseHandler.initialize_optimization_parameters("init")
        print("data written to DB successfully")
    return render_template("upload.html")

@app.route("/delete", methods=['GET', 'POST'])
def delete():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        myDatabaseHandler.deleteRegion()
    return render_template("delete.html")

@app.route("/deleteBuildings", methods=['GET', 'POST'])
def deleteBuildings():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        myDatabaseHandler.deleteBuildings()
    return render_template("deleteBuildings.html")

@app.route("/deleteWholeData", methods=['GET', 'POST'])
def deleteWholeData():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler("dummyRegion", "database.db")
        myDatabaseHandler.deleteWholeData()
    return render_template("deleteWholeData.html")


@app.route("/uploadBuildings", methods=['GET', 'POST'])
def uploadBuildings():
    if request.method == 'POST':
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if allowed(file.filename):
            filename = secure_filename(file.filename)
        else:
            return redirect(request.url)
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        myDatabaseHandler.initializeTablesInDatabase()
        file.save(os.path.join(folder, filename))
        myDatabaseHandler.writeUploadedBuildingsToDatabase(folder, filename)
    return render_template("uploadBuildings.html")

@app.route("/modifyGraph")
def modifyGraph():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0], "buttonDraw_" + header[0])
        handledHeaders.append(newHeader)
    return render_template("modifyGraph.html", headers=handledHeaders)

@app.route("/modifyGraphDraw_process", methods=["POST"])
def modifyGraphDrawProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        if buttonPressed is not None:
            region = buttonPressed[buttonPressed.startswith("buttonDraw_") and len("buttonDraw_"):]
            myDatabaseHandler = databaseHandler(region, "database.db")
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend = dict()
            jsonToReturnToFrontend["region"] = region
            jsonToReturnToFrontend["Auffangbecken"] = myDatabaseHandler.readAuffangbecken()
            jsonToReturnToFrontend["Leitgraeben"] = myDatabaseHandler.read_leitgraeben()
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/modifyGraphSaveToDatabase_process", methods=["POST"])
def modifyGraphSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateAuffangbeckenFromFrontend(returnedData["Auffangbecken"])
            myDatabaseHandler.updateLeitgraebenFromFrontend(returnedData["Leitgraeben"])
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/modifyBuildings")
def modifyBuildings():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDraw_" + header[0], )
        handledHeaders.append(newHeader)
    return render_template("modifyBuildings.html", headers=handledHeaders)

@app.route("/modifyBuildingsDraw_process", methods=["GET", "POST"])
def modifyBuildingsDrawProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        if buttonPressed is not None:
            region = buttonPressed[buttonPressed.startswith("buttonDraw_") and len("buttonDraw_"):]
            myDatabaseHandler = databaseHandler(region, "database.db")
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend = dict()
            jsonToReturnToFrontend["region"] = region
            jsonToReturnToFrontend["Buildings"] = myDatabaseHandler.readBuildingsForDisplay()
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/modifyBuildingsSaveToDatabase_process", methods=["POST"])
def modifyBuildingsSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateBuildingsFromFrontend(returnedData["Buildings"])
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/uploadKataster", methods=['GET', 'POST'])
def uploadKataster():
    if request.method == 'POST':
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if allowed(file.filename):
            filename = secure_filename(file.filename)
        else:
            return redirect(request.url)
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        file.save(os.path.join(folder, filename))
        myDatabaseHandler.writeUploadedKatasterToDatabase(folder, filename)
    return render_template("uploadKataster.html")

@app.route("/uploadKatasterAsXml", methods=['GET', 'POST'])
def uploadKatasterAsXml():
    if request.method == 'POST':
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if allowed(file.filename):
            filename = secure_filename(file.filename)
        else:
            return redirect(request.url)
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        file.save(os.path.join(folder, filename))
        if filename.rsplit('.', 1)[1].lower() == "xml":
            myDatabaseHandler.writeUploadedKatasterAsXmlToDatabase(folder, filename)
        elif filename.rsplit('.', 1)[1].lower() == "shp":
            myDatabaseHandler.writeUploadedKatasterAsShpToDatabase(folder, filename)
    return render_template("uploadKatasterAsXml.html")

@app.route("/uploadEinzugsgebiete", methods=['GET', 'POST'])
def uploadEinzugsgebiete():
    if request.method == 'POST':
        if "file" not in request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)
        if allowed(file.filename):
            filename = secure_filename(file.filename)
        else:
            return redirect(request.url)
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        file.save(os.path.join(folder, filename))
        myDatabaseHandler.writeUploadedEinzugsgebieteToDatabase(folder, filename)
    return render_template("uploadEinzugsgebiete.html")

@app.route("/showKataster")
def showKataster():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("showKataster.html", headers=handledHeaders)

@app.route("/modifyKatasterSaveToDatabase_process", methods=["POST"])
def modifyKatasterSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateKatasterFromFrontend(returnedData["Kataster"])
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/showKatasterDisplay_process", methods=["POST"])
def showKatasterDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        if buttonPressed is not None:
            region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
            myDatabaseHandler = databaseHandler(region, "database.db")
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            myKataster = myDatabaseHandler.readKatasterForDisplay()
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend["Kataster"] = myKataster["Kataster"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/showGrid")
def showGrid():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("showGrid.html", headers=handledHeaders)

@app.route("/showGridDisplay_process", methods=["POST"])
def showGridDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        if buttonPressed is not None:
            region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
            myDatabaseHandler = databaseHandler(region, "database.db")
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            myGrid = myDatabaseHandler.readGridForDisplay()
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend["Grid"] = myGrid["Grid"]
            jsonToReturnToFrontend["Relevant"] = myGrid["Relevant"]
            jsonToReturnToFrontend["MitMassnahme"] = myGrid["MitMassnahme"]
            jsonToReturnToFrontend["connectedToRelevantNode"] = myGrid["connectedToRelevantNode"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/computeMitMassnahme")
def computeMitMassnahme():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeMitMassnahme.html", headers=handledHeaders)

@app.route('/computeMitMassnahme_process', methods=['GET','POST'])
def computeMitMassnahmeProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateMitMassnahme()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error' : 'Something Went Wrong!'})

@app.route("/computeGraphOfRelevantNodes")
def computeGraphOfRelevantNodes():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeGraphOfRelevantNodes.html", headers=handledHeaders)

@app.route('/computeGraphOfRelevantNodes_process', methods=['GET','POST'])
def computeGraphOfRelevantNodesProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateRelevant()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error' : 'Something Went Wrong!'})

@app.route("/showGridSaveToDatabase_process", methods=["POST"])
def showGridSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateRelevantFromFrontend(returnedData)
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/computeOptimalSolution")
def computeOptimalSolution():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeOptimalSolution.html", headers=handledHeaders)

@app.route('/computeOptimalSolution_process', methods=['GET','POST'])
def computeOptimalSolutionProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.computeOptimalSolution()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error' : 'Something Went Wrong!'})

@app.route("/showOptimalSolution")
def showOptimalSolution():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showOptimalSolution.html", headers=handledHeadersSolved)

@app.route('/showOptimalSolutionDisplay_process', methods=['GET','POST'])
def showOptimalSolutionDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            mySolution = myDatabaseHandler.readOptimalSolution()
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            myGrid = myDatabaseHandler.readGridForDisplay()
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend["Grid"] = myGrid["Grid"]
            jsonToReturnToFrontend["Relevant"] = myGrid["Relevant"]
            jsonToReturnToFrontend["MitMassnahme"] = myGrid["MitMassnahme"]
            jsonToReturnToFrontend["connectedToRelevantNode"] = myGrid["connectedToRelevantNode"]
            jsonToReturnToFrontend["GeodesicHeight"] = myGrid["GeodesicHeight"]
            jsonToReturnToFrontend["Flooded"] = mySolution["Flooded"]
            jsonToReturnToFrontend["waterHeight"] = mySolution["waterHeight"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/showHandlungsbedarf")
def showHandlungsbedarf():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showHandlungsbedarf.html", headers=handledHeadersSolved)

@app.route('/showHandlungsbedarfDisplay_process', methods=['GET','POST'])
def showHandlungsbedarfDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            mySolution = myDatabaseHandler.readOptimalSolution()
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            myGrid = myDatabaseHandler.readGridForDisplay()
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend["Grid"] = myGrid["Grid"]
            jsonToReturnToFrontend["Relevant"] = myGrid["Relevant"]
            jsonToReturnToFrontend["MitMassnahme"] = myGrid["MitMassnahme"]
            jsonToReturnToFrontend["connectedToRelevantNode"] = myGrid["connectedToRelevantNode"]
            jsonToReturnToFrontend["GeodesicHeight"] = myGrid["GeodesicHeight"]
            jsonToReturnToFrontend["Flooded"] = mySolution["Flooded"]
            jsonToReturnToFrontend["waterHeight"] = mySolution["waterHeight"]
            jsonToReturnToFrontend["handlungsbedarf"] = mySolution["handlungsbedarf"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            jsonToReturnToFrontend["Buildings"] = myDatabaseHandler.readBuildingsForDisplay()
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/modifyHeaderData")
def modifyHeaderData():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    jsonToReturnToFrontend = {}
    handledHeadersSolved = []
    for header in headers:
        jsonToReturnToFrontend[header[0]] = {"amount": header[7], "duration": header[8]}
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeadersSolved.append(newHeader)
    #jsonToReturnToFrontend = json.dumps(jsonToReturnToFrontend)
    return render_template("modifyHeaderData.html", headers=handledHeadersSolved, headersAsJson=jsonToReturnToFrontend)

@app.route("/modifyHeaderDataSaveToDatabase_process", methods=["POST"])
def modifyHeaderDataSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = "someRegion"
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateHeaderDataFromFrontend(returnedData)
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/modifyOptimizationParameters")
def modifyOptimizationParameters():
    myDatabaseHandler = databaseHandler("None", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    parameters = myDatabaseHandler.read_all_optimization_parameters()
    parameter_names = []
    some_region = list(parameters.keys())[0]
    parameters_for_some_region = parameters[some_region]
    for param in parameters_for_some_region[list(parameters_for_some_region.keys())[0]].keys():
        parameter_names.append(param)
    return render_template("modifyOptimizationParameters.html", headers=headers, parameters=parameters, parameterNames=parameter_names)


@app.route("/modifyOptimizationParametersSaveToDatabase_process", methods=["POST"])
def modifyOptimizationParametersSaveToDatabaseProcess():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            myDatabaseHandler = databaseHandler("None", "database.db")
            myDatabaseHandler.update_optimization_parameters_from_frontend(returned_data)
            jsonToReturnToFrontend = jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/showMassnahmenSolution")
def showMassnahmenSolution():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showMassnahmenSolution.html", headers=handledHeadersSolved)

@app.route('/showMassnahmenDisplay_process', methods=['GET','POST'])
def showMassnahmenDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            mySolution = myDatabaseHandler.readOptimalSolution()
            header = myDatabaseHandler.readRegionHeader()
            all_auffangbecken = myDatabaseHandler.readAuffangbecken()
            all_leitgraeben = myDatabaseHandler.read_leitgraeben()
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            jsonToReturnToFrontend["auffangbeckenInOptimalSolution"] = mySolution["auffangbecken"]
            jsonToReturnToFrontend["leitgraebenInOptimalSolution"] = mySolution["leitgraeben"]
            jsonToReturnToFrontend["auffangbecken"] = all_auffangbecken
            jsonToReturnToFrontend["leitgraeben"] = all_leitgraeben
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/copyRegion")
def copyRegion():
    return render_template("copyRegion.html")

@app.route("/copyRegion_process", methods=['GET','POST'])
def copyRegion_process():
    if request.method == "POST":
        dataset = json.loads(request.form.get("dataset"))
        myDatabaseHandler = databaseHandler(dataset["from"], "database.db")
        myDatabaseHandler.copy_region_to(dataset["to"])
        return jsonify({'success': 'Die Daten wurden erfolgreich in die Datenbank kopiert am ' + str(datetime.datetime.now())})
    return jsonify({'error': 'Something Went Wrong!'})

@app.route("/computeMassnahmenKataster")
def computeMassnahmenKataster():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeMassnahmenKataster.html", headers=handledHeaders)

@app.route('/computeMassnahmenKataster_process', methods=['GET','POST'])
def computeMassnahmenKatasterProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.compute_massnahmen_kataster()
            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error' : 'Something Went Wrong!'})

@app.route("/showFliesswege")
def showFliesswege():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showFliesswege.html", headers=handledHeadersSolved)

@app.route('/showFliesswegeDisplay_process', methods=['GET','POST'])
def showFliesswegeDisplayProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonDisplay_") and len("buttonDisplay_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            mySolution = myDatabaseHandler.readOptimalSolution()
            header = myDatabaseHandler.readRegionHeader()
            jsonToReturnToFrontend = myDatabaseHandler.readEinzugsgebieteForDisplay()
            myGrid = myDatabaseHandler.readGridForDisplay()
            jsonToReturnToFrontend["Grid"] = myGrid["Grid"]
            #jsonToReturnToFrontend["Relevant"] = myGrid["Relevant"]
            #jsonToReturnToFrontend["MitMassnahme"] = myGrid["MitMassnahme"]
            #jsonToReturnToFrontend["connectedToRelevantNode"] = myGrid["connectedToRelevantNode"]
            #jsonToReturnToFrontend["GeodesicHeight"] = myGrid["GeodesicHeight"]
            jsonToReturnToFrontend["flow_through_nodes"] = mySolution["flow_through_nodes"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=True, host='0.0.0.0', threaded=False)