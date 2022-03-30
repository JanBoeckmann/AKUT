'''
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
    return render_template("routes/uploadKataster.html")


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
    return render_template("routes/uploadBuildings.html")
'''
'''
@app.route("/showOptimalSolution")
@login_required
def show_optimal_solution():
    myDatabaseHandler = databaseHandler(request.form.get("region"), "database.db")
    headers = myDatabaseHandler.readFullHeaderTable()
    handledHeadersSolved = []
    for header in headers:
        if header[3] == 1:
            newHeader = header + ("buttonDisplay_" + header[0],)
            handledHeadersSolved.append(newHeader)
    return render_template("routes/showOptimalSolution.html", headers=handledHeadersSolved)


@app.route('/showOptimalSolutionDisplay_process', methods=['GET', 'POST'])
@login_required
def show_optimal_solution_display_process():
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
'''
'''
@app.route("/deleteWholeData", methods=['GET', 'POST'])
@login_required
def delete_whole_data():
    if request.method == "POST":
        myDatabaseHandler = databaseHandler("dummyRegion", "database.db")
        myDatabaseHandler.deleteWholeData()
    return render_template("routes/deleteWholeData.html")
'''
