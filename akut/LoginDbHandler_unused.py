'''
    def read_full_header_table(self):
        headers = Header.query.all()
        header_dict = dict()
        for header in headers:
            header_dict[header.region] = self.db_object_to_dict(header)
        return header_dict
'''
'''
def writeUploadedDataToDatabase(self, path, filename):
    # delete existing, add header
    Header.query.filter_by(region=self.region.name).delete()
    Data.query.filter_by(region=self.region.name).delete()
    header = Header(region=self.region, uploaded=1, date_uploaded=datetime.datetime.now(), solved=0,
                    date_solved="not solved", timeHorizon=0, gridSize=1, rainAmount=126.5, rainDuration=60)
    self.database.session.add(header)
    # init
    to_db = []
    id = 1
    einzugsgebieteData = self.readEinzugsgebieteForDisplay()
    einzugsgebietePolygon = Polygon(einzugsgebieteData["Einzugsgebiete"])
    with open(os.path.join(path, filename), encoding="utf-8-sig") as file:
        dr = csv.DictReader(file, fieldnames=["col1", "col2", "col3"], delimiter=";")
        minimalRight = 9999999999
        minimalUp = 9999999999
        for grid in dr:
            conversedCoordinates = utm.to_latlon(int(float(grid["col1"])), int(float(grid["col2"])), self.utm_zone, 'N')
            position, newPolygonArray = self.computeGridPolygon((int(float(grid["col1"])), int(float(grid["col2"]))), gridSize)
            newKatasterPolygon = Polygon(newPolygonArray)
            if int(float(grid["col1"])) < minimalRight:
                minimalRight = int(float(grid["col1"]))
            if int(float(grid["col2"])) < minimalUp:
                minimalUp = int(float(grid["col2"]))
            posRight = int(float(grid["col1"])) - minimalRight
            posUp = int(float(grid["col2"])) - minimalUp
            if (newKatasterPolygon.intersects(einzugsgebietePolygon)):
                data = Data(region=self.region, id=id, xCoord=conversedCoordinates[0],
                            yCoord=conversedCoordinates[1], geodesicHeight=int(grid["col3"]), inEinzugsgebiet=1,
                            gridPolyline=position, mitMassnahme="notComputed", relevantForGraph=0,
                            utmRight=int(float(grid["col1"])),
                            utmUp=int(float(grid["col2"], posRight, posUp, connectedToRelevantNodes=0)))
                self.database.session.add(data)
            else:
                data = Data(region=self.region, id=id, xCoord=conversedCoordinates[0],
                            yCoord=conversedCoordinates[1], geodesicHeight=int(grid["col3"]), inEinzugsgebiet=0,
                            gridPolyline=position, mitMassnahme="notComputed", relevantForGraph=0,
                            utmRight=int(float(grid["col1"])),
                            utmUp=int(float(grid["col2"], posRight, posUp, connectedToRelevantNodes=0)))
                self.database.session.add(data)
            id = id + 1
    self.database.session.commit()

def writeUploadedBuildingsToDatabase(self, path, filename):
    geodata = pygeoj.load(os.path.join(path, filename))
    idRunningIndex = 1
    for feature in geodata:
        data_buildings = DataBuildings(region=self.region, id=idRunningIndex,
                                       xCoord=feature.geometry.coordinates[0],
                                       yCoord=feature.geometry.coordinates[1],
                                       properties=json.dumps(feature.properties), active=1)
        self.database.session.add(data_buildings)
        idRunningIndex = idRunningIndex + 1
    self.database.session.commit()
    print("Successfully wrote buildings data into database")


def writeUploadedKatasterToDatabase(self, path, filename):
    dwg = dxfgrabber.readfile(os.path.join(path, filename))
    all_lines = [entity for entity in dwg.entities if entity.dxftype == 'LWPOLYLINE']
    id = 1
    einzugsgebieteData = self.readEinzugsgebieteForDisplay()
    einzugsgebietePolygon = Polygon(einzugsgebieteData["Einzugsgebiete"])
    for line in all_lines:
        position = ""
        newPolygonArray = []
        if len(line.points) > 2:
            for point in line.points:
                conversedCoordinates = utm.to_latlon(point[0], point[1], self.utm_zone_kataster, 'N')
                newPolygonArray.append(conversedCoordinates)
                position = position + self.delimiter + str(conversedCoordinates[0]) + "," + str(
                    conversedCoordinates[1])
            position = position[1:]
            newKatasterPolygon = Polygon(newPolygonArray)
            if newKatasterPolygon.intersects(einzugsgebietePolygon):
                region_kataster = Kataster(region=self.region, id=id, position=position, inEinzugsgebiet=1,
                                           additionalCost=0)
                self.region.session.add(region_kataster)
            else:
                region_kataster = Kataster(region=self.region, id=id, position=position, inEinzugsgebiet=0,
                                           additionalCost=0)
                self.region.session.add(region_kataster)
            id = id + 1
    Kataster.query.filter_by(region=self.region.name).delete()
    self.database.session.commit()
'''
'''
def readDataFromDatabase(self):
    header = Data.query.filter_by(region=self.region.name).all()
    rows = []
    for header in header:
        rows.append(header.region)
    myGisDataFloat = []
    for row in rows:
        if len(row) >= 1:
            myGisDataFloat.append([float(row[1]), float(row[2]), float(row[3])])
    return myGisDataFloat

def writeOptimalSolutionToDatabase(self, flooded, activeNodes, timeSteps):
    Headers = Header.query.filter_By(region=self.region).all()
    for header in Headers:
        header.solved = 1
        header.date_solved = datetime.datetime.now()
        header.timeHorizon = timeSteps

    Solutions.filter_by(region=self.region.name).delete()
    for timeStep in flooded.keys():
        for node in flooded[timeStep].keys():
            solution1 = Solutions(region=self.region, variableName="flooded", timeStep=timeStep, nodeXCoord=node[0],
                                  nodeYCoord=node[1], variableValue=flooded[timeStep][node])
            solution2 = Solutions(region=self.region, variableName="activeNodes", timeStep=timeStep,
                                  nodeXCoord=node[0],
                                  nodeYCoord=node[1], variableValue=flooded[timeStep][node])
            self.database.session.add_all([solution1, solution2])
    self.database.session.commit()


def writeGraphToDatabase(self, graph):
    GraphNodes.query.filter_by(region=self.region.name).delete()
    GraphEdges.query.filter_by(region=self.region.name).delete()
    for node in graph.nodes:
        graph_node = GraphNodes(region=self.region, nodeNumberXCoord=node[0], nodeNumberyCoord=node[1])
        login_db.session.add(graph_node)
    for edge in graph.edges():
        graph_edge = GraphEdges(region=self.region, sourceNodeNumberXCoord=edge[0][0],
                                sourceNodeNumberyCoord=edge[0][1], sinkNodeNumberXCoord=edge[1][0],
                                sinkNodeNumberyCoord=edge[1][1])
        login_db.session.add(graph_edge)
    self.database.session.commit()


def readGraphAndOptimalSolutionFromDatabase(self):
    myHeader = Header.query.filter_by(region=self.region).first()
    if myHeader:
        timeSteps = myHeader.timeHorizon

    nodes = []
    graph_nodes = GraphNodes.query.filter_by(region=self.region).all()
    for g_n in graph_nodes:
        nodes.append({"id": "node_" + str(g_n.nodeNumberXCoord) + "_" + str(g_n.nodeNumberYCoord),
                      "label": "node_" + str(g_n.nodeNumberXCoord) + "_" + str(g_n.nodeNumberYCoord),
                      "x": g_n.nodeNumberXCoord,
                      "y": g_n.nodeNumberYCoord,
                      "size": 0.5,
                      "color": "#0A0"})

    edges = []
    graph_edges = GraphEdges.query.filter_by(region=self.region).all()
    for g_e in graph_edges:
        edges.append({"id": "edge_" + str(g_e.sourceNodeNumberXCoord) + "_" + str(
            g_e.sourceNodeNumberyCoord) + "_" + str(g_e.sinkNodeNumberXCoord) + "_" + str(g_e.sinkNodeNumberyCoord),
                      "source": "node_" + str(g_e.sourceNodeNumberXCoord) + "_" + str(g_e.sourceNodeNumberyCoord),
                      "target": "node_" + str(g_e.sinkNodeNumberXCoord) + "_" + str(g_e.sinkNodeNumberyCoord),
                      "weight": 300,
                      "size": 2,
                      "type": "arrow"})

    flooded = dict()
    for t in range(1, timeSteps + 1):
        flooded[t] = dict()
    solutions = Solutions.query.filter_by(region=self.region).filter_by(variableName="flooded").all()
    for s in solutions:
        flooded[s.timeStep]["node_" + str(s.id) + "_" + str(s.nodeXCoord)] = s.nodeYCoord

    activeNodes = dict()
    for t in range(1, timeSteps + 1):
        activeNodes[t] = dict()
    solutions = Solutions.query.filter_by(region=self.region).filter_by(variableName="activeNodes").all()
    for s in solutions:
        activeNodes[s.timeStep]["node_" + str(s.id) + "_" + str(s.nodeXCoord)] = s.nodeYCoord

    return timeSteps, nodes, edges, flooded, activeNodes

def transformStringToPolygonList(self, polygonString):
    points = polygonString.split(self.delimiter)
    pointsOfPolygon = []
    for point in points:
        newPoint = point.split(",")
        newPointTuple = (float(newPoint[0]), float(newPoint[1]))
        pointsOfPolygon.append(newPointTuple)
    return pointsOfPolygon
'''
'''
def deleteBuildings(self):
    DataBuildings.query.filter_by(region=self.region.name).delete()
    self.database.session.commit()
    print("Buildings deleted Successfully")


def deleteWholeData(self):
    Auffangbecken.query.delete()
    Data.query.delete()
    Solutions.query.delete()
    DataBuildings.query.delete()
    Kataster.query.delete()
    Einzugsgebiete.query.delete()
    Leitgraeben.query.delete()
    DGM1.query.delete()
    DGM5.query.delete()
    DGM25.query.delete()
    Header.query.delete()
    OptimizationParameters.query.delete()
    MassnahmenKatasterMapping.query.delete()
    self.database.session.commit()
    print("Tabula Rasa")
'''
'''
def write_uploaded_kataster_as_xml_to_database(self):
        def extract_indices():
            buildings_in_db = self.read_buildings_for_display()
            kataster_in_db = self.read_kataster_for_display()
            if not buildings_in_db:
                max_key_buildings = 0
            else:
                max_key_buildings = max(buildings_in_db, key=buildings_in_db.get)
            if not kataster_in_db:
                max_key_kataster = 0
            else:
                max_key_kataster = max(kataster_in_db, key=kataster_in_db.get)
            return max_key_buildings, max_key_kataster

'''
