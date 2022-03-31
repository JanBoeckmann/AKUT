from flask import render_template, jsonify
from flask_login import login_required, logout_user
from flask_mail import Message
from difflib import SequenceMatcher
from werkzeug.utils import secure_filename

from akut import app, LoginForm, RegistrationForm, folder, RequestResetForm, ResetPasswordForm, mail, extensions
from akut.LoginDbHandler import *


# -----------------------------------------
# ---------- HOME/USERMANAGEMENT ----------
# -----------------------------------------
@app.route("/")
@login_required
def index():
    return "Hello, this is still under construction"


@app.route("/landingPage")
@login_required
def landing_page():
    return render_template("routes/landingPage.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landing_page'))
    form = LoginForm()
    if form.validate_on_submit():
        my_login_handler = LoginDbHandler(None)
        my_login_handler.login_user(form.email.data, form.password.data, form.remember.data)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('landing_page'))
    return render_template("routes/login.html", form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('landing_page'))
    form = RegistrationForm()
    if form.validate_on_submit():
        my_login_handler = LoginDbHandler(None)
        dumb_username = my_login_handler.register_user(form.username.data, form.email.data,
                                                       bcrypt.generate_password_hash(form.password.data).decode(
                                                           'utf-8'))
        if dumb_username:
            return redirect(url_for('easter_egg'))
        else:
            return redirect(url_for('login'))
    return render_template("routes/register.html", form=form)


@app.route("/41x4FU^U0op7f")
def easter_egg():
    return render_template("routes/easterEgg.html")


@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    if current_user == User.query.filter_by(username='admin').first():
        return redirect(url_for('panel'))

    my_login_handler = LoginDbHandler(None)
    if current_user.messages_recieved:
        my_login_handler.show_messages()
    region_list = my_login_handler.get_user_region_list()

    if request.method == 'POST':
        action, region = request.form.get("Aktion"), request.form.get("Region")
        if not region:
            flash('Füllen Sie bitte das Feld "Region auswählen" aus!', 'info')
            return redirect(url_for('account'))
        if not action:
            flash('Füllen Sie bitte das Feld "Aktion auswählen" aus!', 'info')
            return redirect(url_for('account'))
        my_login_handler = LoginDbHandler(region)

        if action == "Entfernen":
            my_login_handler.delete_region_association()
            region_list.remove(region)
        elif action == "Freigeben" or action == "Admin abgeben":
            user = request.form.get("User")
            if not user:
                flash('Füllen Sie Feld User aus!', 'info')
                return redirect(url_for('account'))
            user_manage = User.query.filter_by(username=user).first()
            if not user_manage:
                user_manage = User.query.filter_by(email=user).first()
            if not user_manage:
                flash(f'User/Email "{user}" nicht gefunden!', 'warning')
                return redirect(url_for('account'))
            if action == "Freigeben":
                my_login_handler.share_region(user_manage)
            if action == "Admin abgeben":
                my_login_handler.hand_over_region(user_manage)
            return redirect(url_for('account'))
    return render_template("routes/account.html", regions=region_list)


def send_reset_email(user):
    token = user.get_reset_token()
    message = Message('Password Reset Request', sender='noreply@akut.com', recipients=[user.email])
    message.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
Wenn Sie keine Anfrage gesendet haben, können Sie diese Mail ignorieren.'''
    mail.send(message)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('landing_page'))
    form = RequestResetForm()
    email = form.email.data
    user = User.query.filter_by(email=email).first()
    if form.validate_on_submit():
        if user:
            send_reset_email(user)
        flash(
            f'Wenn für "{email}" ein Account existiert,wurde eine E-Mail zum Zurücksetzen des Passworts gesendet.',
            'info')
        return redirect(url_for('login'))
    return render_template('routes/reset_request.html', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('landing_page'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        my_login_handler = LoginDbHandler(None)
        my_login_handler.change_pw(form.password.data)
        return redirect(url_for('login'))
    return render_template('routes/reset_token.html', title='Reset Password', form=form)


# --------------------------------
# ---------- ADMINPANEL ----------
# --------------------------------
def check_for_admin_user():
    admin_user = User.query.filter_by(username='admin').first()
    if not current_user == admin_user:
        abort(403)


@app.route("/adminpanel", methods=['GET', 'POST'])
@login_required
def panel():
    check_for_admin_user()
    my_login_db_handler = LoginDbHandler(None)
    all_regions_dict = my_login_db_handler.get_all_information(Region, 'name')
    all_users_dict = my_login_db_handler.get_all_information(User, 'username')
    return render_template("routes/adminpanel.html", region_info=all_regions_dict, user_info=all_users_dict)


@app.route("/adminpanel/edit_region/<int:regionid>", methods=['GET', 'POST'])
@login_required
def panel_edit_region(regionid):
    check_for_admin_user()
    my_login_db_handler = LoginDbHandler(None)
    region_info_dict = my_login_db_handler.get_information_for_admin_edit(Region, regionid)
    return render_template("routes/adminpanel_edit_region.html", region_info=region_info_dict)


@app.route("/adminpanel/update_region", methods=['GET', 'POST'])
@login_required
def panel_update_region():
    check_for_admin_user()
    returned_data_dict, returned_keys = dict(), ["name", "region_id", "change_admin", "remove_user[]", "insert_user[]"]
    for key in returned_keys:
        if "[]" in key:
            returned_data_dict[key] = request.form.getlist(key)
        else:
            returned_data_dict[key] = request.form.get(key)
    my_login_handler = LoginDbHandler(None)
    valid = my_login_handler.update_region(returned_data_dict)
    if valid:
        return redirect(url_for('panel'))
    else:
        return redirect(url_for('panel_edit_region', regionid=returned_data_dict["region_id"]))


@app.route("/adminpanel/delete_region/<int:regionid>", methods=['GET', 'POST'])
@login_required
def panel_delete_region(regionid):
    check_for_admin_user()
    my_login_handler = LoginDbHandler(Region.query.filter_by(id=regionid).first().name)
    my_login_handler.delete_region()
    return redirect(url_for('panel'))


@app.route("/adminpanel/edit_user/<int:userid>", methods=['GET', 'POST'])
@login_required
def panel_edit_user(userid):
    check_for_admin_user()
    my_login_db_handler = LoginDbHandler(None)
    user_info_dict = my_login_db_handler.get_information_for_admin_edit(User, userid)
    return render_template("routes/adminpanel_edit_user.html", user_info=user_info_dict)


@app.route("/adminpanel/update_user", methods=['GET', 'POST'])
@login_required
def panel_update_user():
    check_for_admin_user()
    returned_data_dict, returned_keys = dict(), ["name", "user_id", "remove_region[]", "insert_region[]"]
    for key in returned_keys:
        if "[]" in key:
            returned_data_dict[key] = request.form.getlist(key)
        else:
            returned_data_dict[key] = request.form.get(key)
    my_login_handler = LoginDbHandler(None)
    valid = my_login_handler.update_user(returned_data_dict)
    if valid:
        return redirect(url_for('panel'))
    else:
        return redirect(url_for('panel_edit_user', userid=returned_data_dict["user_id"]))


@app.route("/adminpanel/delete_user/<int:userid>", methods=['GET', 'POST'])
@login_required
def panel_delete_user(userid):
    check_for_admin_user()
    my_login_handler = LoginDbHandler(None)
    my_login_handler.delete_user(userid)
    return redirect(url_for('panel'))


# --------------------------------------
# ---------- UPLOADS/KOPIEREN ----------
# --------------------------------------
def check_upload():
    if request.method == 'POST':
        if "file" not in request.files:
            return None
        file = request.files["file"]
        region_name_upload = request.form.get("region")
        if file.filename == "":
            flash('Bitte Datei auswählen!', 'info')
            return None
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in extensions:
            filename = secure_filename(file.filename)
        else:
            flash('Ungültige Datei!', 'info')
            return None
        if region_name_upload == '':
            flash('Bitte Regionname angeben!', 'info')
            return None
        my_db_handler = LoginDbHandler(None)
        regions_in_db = my_db_handler.get_all_region_names()
        for region in regions_in_db:
            ratio = SequenceMatcher(a=region_name_upload, b=region).ratio()
            if ratio >= 0.75:
                pass  # TODO
        return [file, filename, region_name_upload]


@app.route("/uploadEinzugsgebiete", methods=['GET', 'POST'])
@login_required
def upload_einzugsgebiete():  # Modellgrenzen
    if request.method == 'POST':
        uploaded_data = check_upload()
        if uploaded_data is None:
            return redirect(request.url)
        uploaded_data[0].save(os.path.join(folder, uploaded_data[1]))
        my_database_handler = LoginDbHandler(uploaded_data[2])
        my_database_handler.write_uploaded_einzugsgebiete_to_database(folder, uploaded_data[1])
    return render_template("routes/uploadEinzugsgebiete.html")


@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():  # DGM
    if request.method == 'POST':
        uploaded_data = check_upload()
        if uploaded_data is None:
            return redirect(request.url)
        if request.form.get("reuseFile") is None:
            uploaded_data[0].save(os.path.join(folder, uploaded_data[1]))

        my_database_handler = LoginDbHandler(uploaded_data[2])
        if not uploaded_data[1].rsplit('.', 1)[1].lower() == "txt":
            flash(f'Bitte als Dateityp .txt wählen!', 'info')
            return redirect(request.url)
        my_database_handler.write_uploaded_data_to_dgm1(folder, uploaded_data[1])  # , request.form.get("reuseFile")
    return render_template("routes/upload.html")


@app.route("/uploadKatasterAsXml", methods=['GET', 'POST'])
@login_required
def upload_kataster_as_xml():  # ALKIS/XML
    if request.method == 'POST':
        uploaded_data = check_upload()
        if uploaded_data is None:
            return redirect(request.url)
        uploaded_data[0].save(os.path.join(folder, uploaded_data[1]))

        my_login_db_handler = LoginDbHandler(request.form.get("region"))
        if uploaded_data[1].rsplit('.', 1)[1].lower() in ["xml", "zip"]:
            my_login_db_handler.write_uploaded_kataster_as_xml_to_database(folder, uploaded_data[1])
        elif uploaded_data[1].rsplit('.', 1)[1].lower() == "shp":
            my_login_db_handler.write_uploaded_kataster_as_shp_to_database(folder, uploaded_data[1])
        else:
            flash(f'Bitte als Dateityp .xml, .zip oder .shp wählen!', 'info')
            return redirect(request.url)
    return render_template("routes/uploadKatasterAsXml.html")


@app.route("/copyRegion")
@login_required
def copy_region():
    return render_template("routes/copyRegion.html")


@app.route("/copyRegion_process", methods=['GET', 'POST'])
@login_required
def copy_region_process():
    if request.method == "POST":
        dataset = json.loads(request.form.get("dataset"))
        region = Region.query.filter_by(name=dataset["from"]).first()
        if region and not (dataset["from"] == dataset["to"]):
            my_database_handler = LoginDbHandler(dataset["from"])
            my_database_handler.copy_region_to(dataset["to"])
            return jsonify(
                {'success': 'Die Daten wurden erfolgreich in die Datenbank kopiert am ' + str(datetime.now())})
    return jsonify({'error': 'Something Went Wrong!'})


# -----------------------------------
# ---------- EINGANGSDATEN ----------
# -----------------------------------
@app.route("/modifyHeaderData")
@login_required
def modify_header_data():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    json_to_return_to_frontend = {}
    for header in headers:
        json_to_return_to_frontend[header] = {"amount": headers[header]["rainAmount"],
                                              "duration": headers[header]["rainDuration"]}
    return render_template("routes/modifyHeaderData.html", headers=headers,
                           headersAsJson=json_to_return_to_frontend)


@app.route("/modifyHeaderDataSaveToDatabase_process", methods=["POST"])
@login_required
def modify_header_data_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            my_database_handler = LoginDbHandler(None)
            my_database_handler.update_header_data_from_frontend(returned_data)
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyBuildings")
@login_required
def modify_buildings():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    regions = my_database_handler.get_user_regions()
    return render_template("routes/modifyBuildings.html", regions=regions)


@app.route("/modifyBuildingsDraw_process", methods=["GET", "POST"])
@login_required
def modify_buildings_draw_process():
    if request.method == "POST":
        region_id = request.form.get("dataset")
        if region_id is not None:
            regionname = Region.query.filter_by(id=region_id).first().name
            my_database_handler = LoginDbHandler(regionname)
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend = dict()
            json_to_return_to_frontend["region"] = regionname
            json_to_return_to_frontend["Buildings"] = my_database_handler.read_buildings_for_display()
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyBuildingsSaveToDatabase_process", methods=["POST"])
@login_required
def modify_buildings_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            region = returned_data["region"]
            my_database_handler = LoginDbHandler(region)
            my_database_handler.update_buildings_from_frontend(returned_data["Buildings"])
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


# ----------------------------------
# ---------- MODELLIERUNG ----------
# ----------------------------------
@app.route("/showKataster")
@login_required
def show_kataster():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/showKataster.html", headers=headers)


@app.route("/showKatasterDisplay_process", methods=["POST"])
@login_required
def show_kataster_display_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            json_to_return_to_frontend = my_database_handler.read_einzugsgebiete_for_display()
            my_kataster = my_database_handler.read_kataster_for_display()
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend["Kataster"] = my_kataster["Kataster"]
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyKatasterSaveToDatabase_process", methods=["POST"])
@login_required
def modify_kataster_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            region = returned_data["region"]
            my_database_handler = LoginDbHandler(region)
            my_database_handler.update_kataster_from_frontend(returned_data["Kataster"])
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyGraph")
@login_required
def modify_graph():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/modifyGraph.html", headers=headers)


@app.route("/modifyGraphDraw_process", methods=["POST"])
@login_required
def modify_graph_draw_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend = dict()
            json_to_return_to_frontend["region"] = region_name
            json_to_return_to_frontend["Auffangbecken"] = my_database_handler.read_auffangbecken()
            json_to_return_to_frontend["Leitgraeben"] = my_database_handler.read_leitgraeben()
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyGraphSaveToDatabase_process", methods=["POST"])
@login_required
def modify_graph_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            region = returned_data["region"]
            my_database_handler = LoginDbHandler(region)
            my_database_handler.update_auffangbecken_from_frontend(returned_data["Auffangbecken"])
            my_database_handler.update_leitgraeben_from_frontend(returned_data["Leitgraeben"])
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/modifyOptimizationParameters")
@login_required
def modify_optimization_parameters():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    parameters = my_database_handler.read_all_optimization_parameters()
    parameter_names = []
    some_region = list(parameters.keys())[0]
    parameters_for_some_region = parameters[some_region]
    for param in parameters_for_some_region[list(parameters_for_some_region.keys())[0]].keys():
        parameter_names.append(param)
    return render_template("routes/modifyOptimizationParameters.html", headers=headers, parameters=parameters,
                           parameterNames=parameter_names)


@app.route("/modifyOptimizationParametersSaveToDatabase_process", methods=["POST"])
@login_required
def modify_optimization_parameters_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            my_database_handler = LoginDbHandler(None)
            my_database_handler.update_optimization_parameters_from_frontend(returned_data)
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showGrid")
@login_required
def show_grid():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/showGrid.html", headers=headers)


@app.route("/showGridDisplay_process", methods=["POST"])
@login_required
def show_grid_display_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            json_to_return_to_frontend = my_database_handler.read_einzugsgebiete_for_display()
            my_grid = my_database_handler.read_grid_for_display()
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend["Grid"] = my_grid["Grid"]
            json_to_return_to_frontend["Relevant"] = my_grid["Relevant"]
            json_to_return_to_frontend["MitMassnahme"] = my_grid["MitMassnahme"]
            json_to_return_to_frontend["connectedToRelevantNode"] = my_grid["connectedToRelevantNode"]
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showGridSaveToDatabase_process", methods=["POST"])
@login_required
def show_grid_save_to_database_process():
    if request.method == "POST":
        returned_data = json.loads(request.form.get("dataset"))
        if returned_data is not None:
            region = returned_data["region"]
            my_database_handler = LoginDbHandler(region)
            my_database_handler.update_relevant_from_frontend(returned_data)
            json_to_return_to_frontend = jsonify({
                'success': 'Die Daten wurden erfolgreich in die Datenbank geschrieben. Ende des Prozesses: ' + str(
                    datetime.now())})
            return json_to_return_to_frontend
    return jsonify({'error': 'Something Went Wrong!'})


# ----------------------------------
# ---------- BERECHNUNGEN ----------
# ----------------------------------
@app.route("/computeMitMassnahme")
@login_required
def compute_mit_massnahme():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/computeMitMassnahme.html", headers=headers)


@app.route('/computeMitMassnahme_process', methods=['GET', 'POST'])
@login_required
def compute_mit_massnahme_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_database_handler.update_mit_massnahme()
            return jsonify({'dataset': region_name + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeGraphOfRelevantNodes")
@login_required
def compute_graph_of_relevant_nodes():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/computeGraphOfRelevantNodes.html", headers=headers)


@app.route('/computeGraphOfRelevantNodes_process', methods=['GET', 'POST'])
@login_required
def compute_graph_of_relevant_nodes_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_database_handler.update_relevant()
            return jsonify({'dataset': region_name + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeMassnahmenKataster")
@login_required
def compute_massnahmen_kataster():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/computeMassnahmenKataster.html", headers=headers)


@app.route('/computeMassnahmenKataster_process', methods=['GET', 'POST'])
@login_required
def compute_massnahmen_kataster_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_database_handler.compute_massnahmen_kataster()
            return jsonify({'dataset': region_name + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/computeOptimalSolution")
@login_required
def compute_optimal_solution():
    my_database_handler = LoginDbHandler(None)
    headers = my_database_handler.read_user_header_table()
    return render_template("routes/computeOptimalSolution.html", headers=headers)


@app.route('/computeOptimalSolution_process', methods=['GET', 'POST'])
@login_required
def compute_optimal_solution_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_database_handler.compute_optimal_solution()
            return jsonify({'dataset': region_name + " wurde erfolgreich berechnet."})
    return jsonify({'error': 'Something Went Wrong!'})


# -------------------------------
# ---------- LOESUNGEN ----------
# -------------------------------
@app.route("/showHandlungsbedarf")
@login_required
def show_handlungsbedarf():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    headers = my_database_handler.read_user_header_table_solved_only()
    return render_template("routes/showHandlungsbedarf.html", headers=headers)


@app.route('/showHandlungsbedarfDisplay_process', methods=['GET', 'POST'])
@login_required
def show_handlungsbedarf_display_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_solution = my_database_handler.read_optimal_solution()
            json_to_return_to_frontend = my_database_handler.read_einzugsgebiete_for_display()
            my_grid = my_database_handler.read_grid_for_display()
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend["Grid"] = my_grid["Grid"]
            json_to_return_to_frontend["Relevant"] = my_grid["Relevant"]
            json_to_return_to_frontend["MitMassnahme"] = my_grid["MitMassnahme"]
            json_to_return_to_frontend["connectedToRelevantNode"] = my_grid["connectedToRelevantNode"]
            json_to_return_to_frontend["GeodesicHeight"] = my_grid["GeodesicHeight"]
            json_to_return_to_frontend["Flooded"] = my_solution["Flooded"]
            json_to_return_to_frontend["waterHeight"] = my_solution["waterHeight"]
            json_to_return_to_frontend["handlungsbedarf"] = my_solution["handlungsbedarf"]
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            json_to_return_to_frontend["Buildings"] = my_database_handler.read_buildings_for_display()
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showFliesswege")
@login_required
def show_fliesswege():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    headers = my_database_handler.read_user_header_table_solved_only()
    return render_template("routes/showFliesswege.html", headers=headers)


@app.route('/showFliesswegeDisplay_process', methods=['GET', 'POST'])
@login_required
def show_fliesswege_display_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_solution = my_database_handler.read_optimal_solution()
            header = my_database_handler.read_region_header()
            json_to_return_to_frontend = my_database_handler.read_einzugsgebiete_for_display()
            my_grid = my_database_handler.read_grid_for_display()
            json_to_return_to_frontend["Grid"] = my_grid["Grid"]
            # json_to_return_to_frontend["Relevant"] = my_grid["Relevant"]
            # json_to_return_to_frontend["MitMassnahme"] = my_grid["MitMassnahme"]
            # json_to_return_to_frontend["connectedToRelevantNode"] = my_grid["connectedToRelevantNode"]
            # json_to_return_to_frontend["GeodesicHeight"] = my_grid["GeodesicHeight"]
            json_to_return_to_frontend["flow_through_nodes"] = my_solution["flow_through_nodes"]
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


@app.route("/showMassnahmenSolution")
@login_required
def show_massnahmen_solution():
    my_database_handler = LoginDbHandler(request.form.get("region"))
    headers = my_database_handler.read_user_header_table_solved_only()
    return render_template("routes/showMassnahmenSolution.html", headers=headers)


@app.route('/showMassnahmenDisplay_process', methods=['GET', 'POST'])
@login_required
def show_massnahmen_display_process():
    if request.method == "POST":
        region_name = request.form.get("dataset")
        if region_name is not None:
            my_database_handler = LoginDbHandler(region_name)
            my_solution = my_database_handler.read_optimal_solution()
            header = my_database_handler.read_region_header()
            all_auffangbecken = my_database_handler.read_auffangbecken()
            all_leitgraeben = my_database_handler.read_leitgraeben()
            json_to_return_to_frontend = my_database_handler.read_einzugsgebiete_for_display()
            json_to_return_to_frontend["auffangbeckenInOptimalSolution"] = my_solution["auffangbecken"]
            json_to_return_to_frontend["leitgraebenInOptimalSolution"] = my_solution["leitgraeben"]
            json_to_return_to_frontend["auffangbecken"] = all_auffangbecken
            json_to_return_to_frontend["leitgraeben"] = all_leitgraeben
            json_to_return_to_frontend["center_lat"] = header["center_lat"]
            json_to_return_to_frontend["center_lon"] = header["center_lon"]
            return jsonify(json_to_return_to_frontend)
    return jsonify({'error': 'Something Went Wrong!'})


# ------------------------------
# ---------- LOESCHEN ----------
# ------------------------------
@app.route("/delete", methods=['GET', 'POST'])
@login_required
def delete():
    my_login_db_handler = LoginDbHandler(None)
    region_list = my_login_db_handler.get_user_region_list()
    if request.method == "POST":
        my_database_handler = LoginDbHandler(request.form.get("Region"))
        my_database_handler.delete_region()
        flash(f"Daten für Region {request.form.get('Region')} gelöscht!", 'success')
    return render_template("routes/delete.html", regions=region_list)
