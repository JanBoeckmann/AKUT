from flask import url_for, request, render_template, redirect, jsonify, flash
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.utils import secure_filename
from datetime import *

from akut import app, LoginForm, bcrypt, RegistrationForm, login_db, folder, RequestResetForm, ResetPasswordForm, mail
from akut.databaseHandler import *
from akut.models import User, Region, User_Region, allowed

from flask_mail import Message


@app.route("/")
@login_required
def index():
    return "Hello, this is still under construction"


@app.route("/landingPage")
@login_required
def landingPage():
    return render_template("landingPage.html")


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
    return render_template("login.html", form=form)


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
    return render_template("register.html", form=form)


@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    for region in current_user.regions:
        print(region.name)
    return render_template("account.html")


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',sender='noreply@akut.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
Wenn Sie keine Anfrage gesendet haben, können Sie diese Mail ignorieren.'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    user = User.query.filter_by(email=form.email.data).first()
    if form.validate_on_submit():
        if user:
            send_reset_email(user)
        flash(f'Wenn für "{form.email.data}" ein Account existiert,wurde eine E-Mail zum Zurücksetzen des Passworts gesendet.','info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        login_db.session.commit()
        flash('Passwort aktualisiert!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route("/upload", methods=['GET', 'POST'])
@login_required
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
        if (request.form.get("reuseFile") is None):
            file.save(os.path.join(folder, filename))
        # myDatabaseHandler.writeUploadedDataToDatabase(folder, filename, float(request.form.get("gridSize")))
        myDatabaseHandler.writeUploadedDataToDGM1(folder, filename, 1,
                                                  request.form.get("reuseFile"))
        myDatabaseHandler.initialize_optimization_parameters("init")
        print("data written to DB successfully")
    return render_template("upload.html")


@app.route("/delete", methods=['GET', 'POST'])
@login_required
def delete():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
        myDatabaseHandler.deleteRegion()
    return render_template("delete.html")


@app.route("/deleteWholeData", methods=['GET', 'POST'])
@login_required
def deleteWholeData():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler("dummyRegion", "database.db")
        myDatabaseHandler.deleteWholeData()
    return render_template("deleteWholeData.html")


@app.route("/uploadBuildings", methods=['GET', 'POST'])
@login_required
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
@login_required
def modifyGraph():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0], "buttonDraw_" + header[0])
        handledHeaders.append(newHeader)
    return render_template("modifyGraph.html", headers=handledHeaders)


@app.route("/modifyGraphDraw_process", methods=["POST"])
@login_required
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
@login_required
def modifyGraphSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateAuffangbeckenFromFrontend(returnedData["Auffangbecken"])
            myDatabaseHandler.updateLeitgraebenFromFrontend(returnedData["Leitgraeben"])
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyBuildings")
@login_required
def modifyBuildings():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDraw_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("modifyBuildings.html", headers=handledHeaders)


@app.route("/modifyBuildingsDraw_process", methods=["GET", "POST"])
@login_required
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
@login_required
def modifyBuildingsSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateBuildingsFromFrontend(returnedData["Buildings"])
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/uploadKataster", methods=['GET', 'POST'])
@login_required
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
@login_required
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
        if filename.rsplit('.', 1)[1].lower() in ["xml", "zip"]:
            myDatabaseHandler.writeUploadedKatasterAsXmlToDatabase(folder, filename)
        elif filename.rsplit('.', 1)[1].lower() == "shp":
            myDatabaseHandler.writeUploadedKatasterAsShpToDatabase(folder, filename)
    return render_template("uploadKatasterAsXml.html")


@app.route("/uploadEinzugsgebiete", methods=['GET', 'POST'])
@login_required
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
        region_upload = request.form.get("region")
        myDatabaseHandler = databaseHandler(region_upload, "database.db")
        file.save(os.path.join(folder, filename))
        myDatabaseHandler.writeUploadedEinzugsgebieteToDatabase(folder, filename)

        # Neue Regionen hochladen
        region_current = Region.query.filter_by(name=region_upload).first()
        if not region_current:
            region_new = Region(name=region_upload)
            login_db.session.add(region_new)
            region_current = Region.query.filter_by(name=region_upload).first()
            admin_user = User.query.filter_by(username='admin').first()
            region_current.users.append(User_Region(user=admin_user))
            login_db.session.commit()

        # User hinzufuegen
        association_exists = User_Region.query.filter_by(user_id=current_user.id).filter_by(region_id=region_current.id).first()
        if not association_exists:
            region_current.users.append(User_Region(user=current_user))
            login_db.session.commit()

    return render_template("uploadEinzugsgebiete.html")


@app.route("/showKataster")
@login_required
def showKataster():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("showKataster.html", headers=handledHeaders)


@app.route("/modifyKatasterSaveToDatabase_process", methods=["POST"])
@login_required
def modifyKatasterSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateKatasterFromFrontend(returnedData["Kataster"])
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showKatasterDisplay_process", methods=["POST"])
@login_required
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
@login_required
def showGrid():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("showGrid.html", headers=handledHeaders)


@app.route("/showGridDisplay_process", methods=["POST"])
@login_required
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
@login_required
def computeMitMassnahme():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeMitMassnahme.html", headers=handledHeaders)


@app.route('/computeMitMassnahme_process', methods=['GET', 'POST'])
@login_required
def computeMitMassnahmeProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateMitMassnahme()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len(
                "buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeGraphOfRelevantNodes")
@login_required
def computeGraphOfRelevantNodes():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeGraphOfRelevantNodes.html", headers=handledHeaders)


@app.route('/computeGraphOfRelevantNodes_process', methods=['GET', 'POST'])
@login_required
def computeGraphOfRelevantNodesProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateRelevant()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len(
                "buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showGridSaveToDatabase_process", methods=["POST"])
@login_required
def showGridSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = returnedData["region"]
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateRelevantFromFrontend(returnedData)
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeOptimalSolution")
@login_required
def computeOptimalSolution():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeOptimalSolution.html", headers=handledHeaders)


@app.route('/computeOptimalSolution_process', methods=['GET', 'POST'])
@login_required
def computeOptimalSolutionProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.computeOptimalSolution()

            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len(
                "buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showOptimalSolution")
@login_required
def showOptimalSolution():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showOptimalSolution.html", headers=handledHeadersSolved)


@app.route('/showOptimalSolutionDisplay_process', methods=['GET', 'POST'])
@login_required
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
@login_required
def showHandlungsbedarf():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showHandlungsbedarf.html", headers=handledHeadersSolved)


@app.route('/showHandlungsbedarfDisplay_process', methods=['GET', 'POST'])
@login_required
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
@login_required
def modifyHeaderData():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    jsonToReturnToFrontend = {}
    handledHeadersSolved = []
    for header in headers:
        jsonToReturnToFrontend[header[0]] = {"amount": header[7], "duration": header[8]}
        newHeader = header + ("buttonDisplay_" + header[0],)
        handledHeadersSolved.append(newHeader)
    # jsonToReturnToFrontend = json.dumps(jsonToReturnToFrontend)
    return render_template("modifyHeaderData.html", headers=handledHeadersSolved, headersAsJson=jsonToReturnToFrontend)


@app.route("/modifyHeaderDataSaveToDatabase_process", methods=["POST"])
@login_required
def modifyHeaderDataSaveToDatabaseProcess():
    if request.method == "POST":
        returnedData = json.loads(request.form.get("dataset"))
        if returnedData is not None:
            region = "someRegion"
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.updateHeaderDataFromFrontend(returnedData)
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyOptimizationParameters")
@login_required
def modifyOptimizationParameters():
    myDatabaseHandler = databaseHandler("None", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    parameters = myDatabaseHandler.read_all_optimization_parameters()
    parameter_names = []
    some_region = list(parameters.keys())[0]
    parameters_for_some_region = parameters[some_region]
    for param in parameters_for_some_region[list(parameters_for_some_region.keys())[0]].keys():
        parameter_names.append(param)
    return render_template("modifyOptimizationParameters.html", headers=headers, parameters=parameters,
                           parameterNames=parameter_names)


@app.route("/modifyOptimizationParametersSaveToDatabase_process", methods=["POST"])
@login_required
def modifyOptimizationParametersSaveToDatabaseProcess():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            myDatabaseHandler = databaseHandler("None", "database.db")
            myDatabaseHandler.update_optimization_parameters_from_frontend(returned_data)
            jsonToReturnToFrontend = jsonify({
                                                 'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                                                     datetime.datetime.now())})
            return jsonToReturnToFrontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showMassnahmenSolution")
@login_required
def showMassnahmenSolution():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showMassnahmenSolution.html", headers=handledHeadersSolved)


@app.route('/showMassnahmenDisplay_process', methods=['GET', 'POST'])
@login_required
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
@login_required
def copyRegion():
    return render_template("copyRegion.html")


@app.route("/copyRegion_process", methods=['GET', 'POST'])
@login_required
def copyRegion_process():
    if request.method == "POST":
        dataset = json.loads(request.form.get("dataset"))
        myDatabaseHandler = databaseHandler(dataset["from"], "database.db")
        myDatabaseHandler.copy_region_to(dataset["to"])
        return jsonify(
            {'success': 'Die Daten wurden erfolgreich in die Datenbank kopiert am ' + str(datetime.datetime.now())})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeMassnahmenKataster")
@login_required
def computeMassnahmenKataster():
    myDatabaseHandler = databaseHandler("anyRegion", "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeaders = []
    for header in headers:
        newHeader = header + ("buttonBerechnen_" + header[0],)
        handledHeaders.append(newHeader)
    return render_template("computeMassnahmenKataster.html", headers=handledHeaders)


@app.route('/computeMassnahmenKataster_process', methods=['GET', 'POST'])
@login_required
def computeMassnahmenKatasterProcess():
    if request.method == "POST":
        buttonPressed = request.form.get("dataset")
        region = buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len("buttonBerechnen_"):]
        if buttonPressed is not None:
            myDatabaseHandler = databaseHandler(region, "database.db")
            myDatabaseHandler.compute_massnahmen_kataster()
            return jsonify({'dataset': buttonPressed[buttonPressed.startswith("buttonBerechnen_") and len(
                "buttonBerechnen_"):] + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showFliesswege")
@login_required
def showFliesswege():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("showFliesswege.html", headers=handledHeadersSolved)


@app.route('/showFliesswegeDisplay_process', methods=['GET', 'POST'])
@login_required
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
            # jsonToReturnToFrontend["Relevant"] = myGrid["Relevant"]
            # jsonToReturnToFrontend["MitMassnahme"] = myGrid["MitMassnahme"]
            # jsonToReturnToFrontend["connectedToRelevantNode"] = myGrid["connectedToRelevantNode"]
            # jsonToReturnToFrontend["GeodesicHeight"] = myGrid["GeodesicHeight"]
            jsonToReturnToFrontend["flow_through_nodes"] = mySolution["flow_through_nodes"]
            jsonToReturnToFrontend["center_lat"] = header[9]
            jsonToReturnToFrontend["center_lon"] = header[10]
            return jsonify(jsonToReturnToFrontend)
    return jsonify({'error': 'Something Went Wrong!'})
