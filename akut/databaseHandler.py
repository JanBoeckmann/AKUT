import os
import csv
import sqlite3
import pygeoj
import json
import datetime
import dxfgrabber
import utm
import fiona
import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, Point, LineString
from akut.instanceGraph import *
from akut.instanceGraphForDGM25 import *
import networkx as nx

class databaseHandler:
    def __init__(self, region, database):
        self.region = region
        self.database = database
        self.delimiter = ";"
        self.utm_zone = 32
        self.utm_zone_kataster = 32
        self.customer = "Ersfeld"


    def establishConnection(self):
        try:
            conn = sqlite3.connect(self.database, timeout=3600.0)
            return conn
        except NameError as e:
            print(e)
        return None

    def myround(self, x, base=5):
        return base * round(x / base)

    def dict_to_array(self, input_dict):
        returned_array = []
        for key in input_dict:
            returned_array.append(input_dict[key])
        return returned_array

    def polygon_to_database_format(self, array_in_polygon_format):
        string_in_polygon_format = ';'.join([str(x[0]) + ',' + str(x[1]) for x in array_in_polygon_format])
        return string_in_polygon_format

    def database_to_polygon_format(self, string_in_database_format):
        array_in_polygon_format = [(float(x.split(',')[0]), float(x.split(',')[1])) for x in string_in_database_format.split(';')]
        return array_in_polygon_format

    def computeGridPolygon(self, centre, gridSize):
        polygonPointUpperLeft = utm.to_latlon(centre[0] - gridSize / 2, centre[1] + gridSize / 2, self.utm_zone, 'N')
        polygonPointUpperRight = utm.to_latlon(centre[0] + gridSize / 2, centre[1] + gridSize / 2, self.utm_zone, 'N')
        polygonPointLowerRight = utm.to_latlon(centre[0] + gridSize / 2, centre[1] - gridSize / 2, self.utm_zone, 'N')
        polygonPointLowerLeft = utm.to_latlon(centre[0] - gridSize / 2, centre[1] - gridSize / 2, self.utm_zone, 'N')
        position = str(polygonPointUpperLeft[0]) + "," + str(polygonPointUpperLeft[1]) + self.delimiter + str(polygonPointUpperRight[0]) + "," + str(polygonPointUpperRight[1]) + self.delimiter + str(polygonPointLowerRight[0]) + "," + str(polygonPointLowerRight[1]) + self.delimiter + str(polygonPointLowerLeft[0]) + "," + str(polygonPointLowerLeft[1])
        newPolygonArray = [polygonPointUpperLeft, polygonPointUpperRight, polygonPointLowerRight, polygonPointLowerLeft]
        return position, newPolygonArray

    def initializeTablesInDatabase(self):
        def createSingleTable(SQLStatement):
            conn = self.establishConnection()
            if conn is not None:
                myCursor = conn.cursor()
                myCursor.execute(SQLStatement)
                conn.close()
        sqlCreateTableRegionsHeader = """ CREATE TABLE IF NOT EXISTS regionsHeader (
                                        region text PRIMARY KEY,
                                        uploaded int,
                                        date_uploaded text,
                                        solved int, 
                                        date_solved text, 
                                        timeHorizon int
                                    ); """

        sqlCreateTableRegionsData = """ CREATE TABLE IF NOT EXISTS regionsData (
                                                region text,
                                                xCoord int, 
                                                yCoord int,
                                                geodesicHeight int,
                                                PRIMARY KEY (region, xCoord, yCoord)
                                            ); """

        sqlCreateTableRegionsSolution = """ CREATE TABLE IF NOT EXISTS regionsSolution (
                                                        region text,
                                                        variableName text,
                                                        timeStep int,
                                                        nodeXCoord int,
                                                        nodeYCoord int,
                                                        variableValue float, 
                                                        PRIMARY KEY (region, variableName, timeStep, nodeXCoord, nodeYCoord)
                                                    ); """

        sqlCreateTableRegionsGraphNodes = """ CREATE TABLE IF NOT EXISTS regionsGraphNodes (
                                                                region text,
                                                                nodeNumberXCoord int,
                                                                nodeNumberyCoord int,
                                                                PRIMARY KEY (region, nodeNumberXCoord, nodeNumberYCoord)
                                                            ); """

        sqlCreateTableRegionsGraphEdges = """ CREATE TABLE IF NOT EXISTS regionsGraphEdges (
                                                                        region text,
                                                                        sourceNodeNumberXCoord int,
                                                                        sourceNodeNumberyCoord int,
                                                                        sinkNodeNumberXCoord int,
                                                                        sinkNodeNumberyCoord int,
                                                                        PRIMARY KEY (region, sourceNodeNumberXCoord, sourceNodeNumberyCoord, sinkNodeNumberXCoord, sinkNodeNumberyCoord)
                                                                    ); """

        sqlCreateTableRegionsDataBuildings = """ CREATE TABLE IF NOT EXISTS regionsDataBuildings (
                                                        region text,
                                                        id     int,
                                                        xCoord float, 
                                                        yCoord float,
                                                        properties text,
                                                        active int,
                                                        PRIMARY KEY (region, id)
                                                    ); """

        createSingleTable(sqlCreateTableRegionsHeader)
        createSingleTable(sqlCreateTableRegionsData)
        createSingleTable(sqlCreateTableRegionsSolution)
        createSingleTable(sqlCreateTableRegionsGraphNodes)
        createSingleTable(sqlCreateTableRegionsGraphEdges)
        createSingleTable(sqlCreateTableRegionsDataBuildings)

    def writeUploadedDataToDGM1(self, path, filename, gridSize, reuse):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsHeader WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM1 WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM5 WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM25 WHERE region = \"" + self.region + "\"")
        conn.commit()
        conn.close()
        to_db1 = []
        to_db5 = []
        to_db25 = []
        id = 1
        #in database, we want the geodesic height in mm. Adjust the scaling factor as desired (10 for cm, 1000 for m)
        scaling = 10
        if self.customer == "Wismar" or self.customer == "KMB" or self.customer == "Ersfeld":
            scaling = 1000
        einzugsgebieteData = self.readEinzugsgebieteForDisplay()
        einzugsgebietePolygon = Polygon(einzugsgebieteData["Einzugsgebiete"])
        print(einzugsgebietePolygon.centroid.x)
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("INSERT INTO regionsHeader (region, uploaded, date_uploaded, solved, date_solved, timeHorizon, gridSize, rainAmount, rainDuration, center_lat, center_lon) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", (self.region, 1, datetime.datetime.now(), 0, "not solved", 0, gridSize, 126.5, 60, einzugsgebietePolygon.centroid.x, einzugsgebietePolygon.centroid.y))
        conn.commit()
        conn.close()
        with open(os.path.join(path, filename), encoding="utf-8-sig") as file:
            fieldnames = ["Rowid", "DPFILL10", "X", "Y", "DPFILL10_1"]
            delimiter = ";"
            if self.customer == "Wismar":
                delimiter = ";"
                fieldnames = ["d1", "d2", "X", "d3", "Y", "d4", "d5", "d6", "d7", "d8", "d9", "DPFILL10_1"]
                fieldnames = ["X", "Y", "DPFILL10_1"]
            if self.customer == "KMB" or self.customer == "Ersfeld":
                delimiter = ";"
                fieldnames = ["X", "Y", "DPFILL10_1"]
            dr = csv.DictReader(file, fieldnames=fieldnames, delimiter=delimiter)
            if self.customer != "Wismar":
                next(dr, None) #Skip header line
            remember_keys_to_avoid_dupicates = set()
            for grid in dr:
                # print(grid["X"], " - ", grid["Y"])
                xutm = int(float(grid["X"].replace(",", ".")))
                yutm = int(float(grid["Y"].replace(",", ".")))
                if (xutm, yutm) not in remember_keys_to_avoid_dupicates:
                    remember_keys_to_avoid_dupicates.add((xutm, yutm))
                    xutm25 = self.myround(xutm, 25)
                    yutm25 = self.myround(yutm, 25)
                    conversedCoordinates = utm.to_latlon(xutm, yutm, self.utm_zone, 'N')
                    position, newPolygonArray = self.computeGridPolygon((xutm, yutm), gridSize)
                    position25, newPolygonArray25 = self.computeGridPolygon((xutm25, yutm25), 25)
                    newKatasterPolygon = Polygon(newPolygonArray)
                    newKatasterPolygon25 = Polygon(newPolygonArray25)
                    if (newKatasterPolygon25.intersects(einzugsgebietePolygon)):
                        to_db1.append((self.region, id, xutm, yutm, int(float(grid["DPFILL10_1"]) * scaling), 1, conversedCoordinates[0], conversedCoordinates[1], position, "notComputed", 0, 0, 0, 0))
                        if(xutm % 5 == 0 and yutm % 5 == 0):
                            position5, newPolygonArray5 = self.computeGridPolygon((xutm, yutm), 5)
                            to_db5.append((self.region, id, xutm, yutm, int(float(grid["DPFILL10_1"]) * scaling), 1, conversedCoordinates[0], conversedCoordinates[1], position5, "notComputed", 0, 0, 0, 0))
                        if (xutm % 25 == 0 and yutm % 25 == 0):
                            to_db25.append((self.region, id, xutm, yutm, int(float(grid["DPFILL10_1"]) * scaling), 1, conversedCoordinates[0], conversedCoordinates[1], position25, "notComputed", 0, 0, 0, 1))
                    id = id + 1
                    if id % 100000 == 0:
                        print(id)
                        print(len(to_db1))
                        print("____________")
            conn = self.establishConnection()
            myCursor = conn.cursor()
            myCursor.executemany("INSERT INTO regionsDGM1 (region, id, xutm, yutm, geodesicHeight, inEinzugsgebiet, xCoord, yCoord, gridPolyline, mitMassnahme, relevantForGraph, connectedToRelevantNodes, resolveFurther, willBeInGraph) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", to_db1)
            myCursor.executemany("INSERT INTO regionsDGM5 (region, id, xutm, yutm, geodesicHeight, inEinzugsgebiet, xCoord, yCoord, gridPolyline, mitMassnahme, relevantForGraph, connectedToRelevantNodes, resolveFurther, willBeInGraph) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", to_db5)
            myCursor.executemany("INSERT INTO regionsDGM25 (region, id, xutm, yutm, geodesicHeight, inEinzugsgebiet, xCoord, yCoord, gridPolyline, mitMassnahme, relevantForGraph, connectedToRelevantNodes, resolveFurther, willBeInGraph) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", to_db25)
            conn.commit()
            conn.close()

    def writeUploadedDataToDatabase(self, path, filename, gridSize):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsHeader WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsData WHERE region = \"" + self.region + "\"")
        myCursor.execute("INSERT INTO regionsHeader (region, uploaded, date_uploaded, solved, date_solved, timeHorizon, gridSize, rainAmount, rainDuration) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", (self.region, 1, datetime.datetime.now(), 0, "not solved", 0, gridSize, 126.5, 60))
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
                if (newKatasterPolygon.intersects(einzugsgebietePolygon)):
                    to_db.append((self.region, id, conversedCoordinates[0], conversedCoordinates[1], int(grid["col3"]), 1, position, "notComputed", 0, int(float(grid["col1"])), int(float(grid["col2"]))))
                else:
                    to_db.append((self.region, id, conversedCoordinates[0], conversedCoordinates[1], int(grid["col3"]), 0, position, "notComputed", 0, int(float(grid["col1"])), int(float(grid["col2"]))))
                id = id + 1
            to_db_new = []
            for line in to_db:
                newLine = line + ((line[9] - minimalRight) / gridSize, (line[10] - minimalUp) / gridSize, 0)
                to_db_new.append(newLine)

        myCursor.executemany("INSERT INTO regionsData (region, id, xCoord, yCoord, geodesicHeight, inEinzugsgebiet, gridPolyline, mitMassnahme, relevantForGraph, utmRight, utmUp, posRight, posUp, connectedToRelevantNodes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", to_db_new)
        conn.commit()
        conn.close()

    def writeUploadedBuildingsToDatabase(self, path, filename):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        geodata = pygeoj.load(os.path.join(path, filename))
        to_db = []
        idRunningIndex = 1
        for feature in geodata:
            to_db.append((self.region, idRunningIndex, feature.geometry.coordinates[0], feature.geometry.coordinates[1], json.dumps(feature.properties), 1))
            idRunningIndex = idRunningIndex + 1
        myCursor.executemany("INSERT INTO regionsDataBuildings (region, id, xCoord, yCoord, properties, active) VALUES (?, ?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()
        print("Successfully wrote buildings data into database")

    def writeUploadedKatasterToDatabase(self, path, filename):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        dwg = dxfgrabber.readfile(os.path.join(path, filename))
        all_lines = [entity for entity in dwg.entities if entity.dxftype == 'LWPOLYLINE']
        to_db = []
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
                    position = position + self.delimiter + str(conversedCoordinates[0]) + "," + str(conversedCoordinates[1])
                position = position[1:]
                newKatasterPolygon = Polygon(newPolygonArray)
                if (newKatasterPolygon.intersects(einzugsgebietePolygon)):
                    to_db.append((self.region, id, position, 1, 0))
                else:
                    to_db.append((self.region, id, position, 0, 0))
                id = id + 1
        myCursor.execute("DELETE from regionsKataster WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsKataster (region, id, position, inEinzugsgebiet, additionalCost) VALUES (?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def writeUploadedKatasterAsXmlToDatabase(self, path, filename):
        def get_new_points(array):
            returned_aray = []
            while array:
                x_utm = float(array.pop(0))
                y_utm = float(array.pop(0))
                returned_aray.append((x_utm, y_utm))
            return returned_aray

        def get_buildings_in_einzugesgebiet():
            root = ET.parse(os.path.join(path, filename)).getroot()
            buildings_id = 0
            # for child in root:
            #     print(child)
            if self.customer == "Alzey" or self.customer == "KMB":
                geaenderte_objekte = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}geaenderteObjekte')
                iterator = geaenderte_objekte.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}Transaction')
            else:
                enthaelt = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}enthaelt')
                feature_collection = enthaelt.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}FeatureCollection')
                iterator = feature_collection.findall('{http://www.opengis.net/gml/3.2}featureMember')

            for child in iterator:
                gebaeude = child.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}AX_Gebaeude')
                if gebaeude:
                    gebaeudeklasse = gebaeude.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}gebaeudefunktion')
                    position_of_building = gebaeude.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}position')
                    pos_array = []
                    for pos_list in position_of_building.findall('.//{http://www.opengis.net/gml/3.2}posList'):
                        new_points = get_new_points(pos_list.text.split(' '))
                        if pos_array:
                            pos_array.pop()
                        pos_array = pos_array + new_points
                    if pos_array[0] == pos_array[-1]:
                        pos_array.pop()
                    pos_array_latlon = []
                    for point in pos_array:
                        conversedCoordinates = utm.to_latlon(point[0], point[1], self.utm_zone_kataster, 'N')
                        pos_array_latlon.append(conversedCoordinates)
                    building_polygon = Polygon(pos_array_latlon)
                    if building_polygon.intersects(einzugsgebietePolygon):
                        buildings_id = buildings_id + 1
                        buildings_in_dict[buildings_id] = {"position": pos_array_latlon, "gebaeudeklasse": gebaeudeklasse.text}



        def get_kataster_in_einzugsgebiet():
            kataster_akteur_mapping = {"AX_IndustrieUndGewerbeflaeche": "None",
                                       "AX_FlächeGemischterNutzung": "None",
                                       "AX_FlaecheBesondererFunktionalerPraegung": "None",
                                       "AX_SportFreizeitUndErholungsflaeche": "None",
                                       "AX_Wohnbauflaeche": "None",
                                       "AX_Strassenverkehr": "None",
                                       "AX_Weg": "None",
                                       "AX_Bahnverkehr": "None",
                                       "AX_Flugverkehr": "None",
                                       "AX_Schiffsverkehr": "None",
                                       "AX_Platz": "None",
                                       "AX_Landwirtschaft": "None",
                                       "AX_Wald": "Forstwirtschaft",
                                       "AX_Gehoelz": "None",
                                       "AX_Heide": "None",
                                       "AX_Moor": "None",
                                       "AX_Sumpf": "None",
                                       "AX_UnlandVegetationsloseFlaeche": "None",
                                       }
            kataster_id = 0
            root = ET.parse(os.path.join(path, filename)).getroot()
            if self.customer == "Alzey" or self.customer == "KMB":
                geaenderte_objekte = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}geaenderteObjekte')
                iterator = geaenderte_objekte.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}Transaction')
            else:
                enthaelt = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}enthaelt')
                feature_collection = enthaelt.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}FeatureCollection')
                iterator = feature_collection.findall('{http://www.opengis.net/gml/3.2}featureMember')

            for child in iterator:
                kataster = None
                for ax_code, akteur in kataster_akteur_mapping.items():
                    if not kataster:
                        kataster = child.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}' + ax_code)
                        if kataster:
                            remember_ax_code = ax_code
                            remember_akteur = akteur
                if kataster:
                    position_of_kataster = kataster.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}position')
                    pos_array = []
                    for pos_list in position_of_kataster.findall('.//{http://www.opengis.net/gml/3.2}posList'):
                        new_points = get_new_points(pos_list.text.split(' '))
                        if pos_array:
                            pos_array.pop()
                        pos_array = pos_array + new_points
                    if pos_array[0] == pos_array[-1]:
                        pos_array.pop()
                    pos_array_latlon = []
                    for point in pos_array:
                        conversedCoordinates = utm.to_latlon(point[0], point[1], self.utm_zone_kataster, 'N')
                        pos_array_latlon.append(conversedCoordinates)
                    kataster_polygon = Polygon(pos_array_latlon)
                    if kataster_polygon.intersects(einzugsgebietePolygon):
                        kataster_id = kataster_id + 1
                        kataster_in_dict[kataster_id] = {"position": pos_array_latlon,
                                                         "akteur": remember_akteur}

        def extract_indices():
            buildings_in_db = self.readBuildingsForDisplay()
            kataster_in_db = self.readKatasterForDisplay()
            if not buildings_in_db:
                max_key_buildings = 0
            else:
                max_key_buildings = max(buildings_in_db, key=buildings_in_db.get)
            if not kataster_in_db:
                max_key_kataster = 0
            else:
                max_key_kataster = max(kataster_in_db, key=kataster_in_db.get)
            return max_key_buildings, max_key_kataster

        einzugsgebieteData = self.readEinzugsgebieteForDisplay()
        einzugsgebietePolygon = Polygon(einzugsgebieteData["Einzugsgebiete"])
        # max_id_buildings, max_id_kataster = extract_indices()
        max_id_buildings, max_id_kataster = 0, 0
        buildings_in_dict = dict()
        kataster_in_dict = dict()
        get_buildings_in_einzugesgebiet()
        get_kataster_in_einzugsgebiet()
        print("len of kataster in dict: ", len(kataster_in_dict))
        print(kataster_in_dict)
        gebaeudeklasse_to_schadensklasse_as_dict = self.read_gebaeudeklasse_to_schadensklasse()
        gebaeudeklasse_to_akteur_as_dict = self.read_gebaeudeklasse_to_akteur()

        conn = self.establishConnection()
        myCursor = conn.cursor()
        #DB Buildings
        to_db = []
        for key, value in buildings_in_dict.items():
            if int(buildings_in_dict[key]["gebaeudeklasse"]) in gebaeudeklasse_to_schadensklasse_as_dict:
                schadensklasse = gebaeudeklasse_to_schadensklasse_as_dict[int(buildings_in_dict[key]["gebaeudeklasse"])]
            else:
                schadensklasse = 2
            if int(buildings_in_dict[key]["gebaeudeklasse"]) in gebaeudeklasse_to_akteur_as_dict:
                akteur = gebaeudeklasse_to_akteur_as_dict[int(buildings_in_dict[key]["gebaeudeklasse"])]
            else:
                akteur = "None"
            max_id_buildings = max_id_buildings + 1
            to_db.append((self.region, max_id_buildings, self.polygon_to_database_format(buildings_in_dict[key]["position"]), json.dumps({}), 1, buildings_in_dict[key]["gebaeudeklasse"], schadensklasse, akteur))

        myCursor.execute("DELETE from regionsDataBuildings WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsDataBuildings (region, id, position, properties, active, gebaeudeklasse, schadensklasse, akteur) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", to_db)

        #DB Kataster
        to_db = []
        for key, value in kataster_in_dict.items():
            max_id_kataster = max_id_kataster + 1
            to_db.append((self.region, max_id_kataster, self.polygon_to_database_format(kataster_in_dict[key]["position"]), 1, 0, kataster_in_dict[key]["akteur"]))
        myCursor.execute("DELETE from regionsKataster WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsKataster (region, id, position, inEinzugsgebiet, additionalCost, akteur) VALUES (?, ?, ?, ?, ?, ?);", to_db)

        conn.commit()
        conn.close()

    def writeUploadedKatasterAsShpToDatabase(self, path, filename):
        einzugsgebieteData = self.readEinzugsgebieteForDisplay()
        einzugsgebietePolygon = Polygon(einzugsgebieteData["Einzugsgebiete"])
        buildings_in_dict = dict()
        kataster_in_dict = dict()
        to_db = []
        id = 1
        gebaeudeklasse_to_akteur_as_dict = self.read_gebaeudeklasse_to_akteur()
        gebaeudeklasse_to_schadensklasse_as_dict = self.read_gebaeudeklasse_to_schadensklasse()
        with fiona.open(os.path.join(path, filename)) as src:
            for f in src:
                if 'geometry' in f:
                    if f['geometry']['type'] == 'Polygon':
                        coordinates_in_shp = f['geometry']['coordinates'][0]
                        coordinates_in_shp_as_latlon = [utm.to_latlon(x[0], x[1], self.utm_zone_kataster, 'N') for x in coordinates_in_shp]
                        gebaeude_as_polygon = Polygon(coordinates_in_shp_as_latlon)
                        gebaeudeklasse = f['properties']['GFK']
                        if gebaeudeklasse in gebaeudeklasse_to_schadensklasse_as_dict:
                            schadensklasse = gebaeudeklasse_to_schadensklasse_as_dict[gebaeudeklasse]
                        else:
                            schadensklasse = 2
                        if gebaeudeklasse in gebaeudeklasse_to_akteur_as_dict:
                            akteur = gebaeudeklasse_to_akteur_as_dict[gebaeudeklasse]
                        else:
                            akteur = "None"
                        if gebaeude_as_polygon.intersects(einzugsgebietePolygon):
                            to_db.append((self.region, id, self.polygon_to_database_format(coordinates_in_shp_as_latlon), json.dumps({}), 1, gebaeudeklasse, schadensklasse, akteur))
                            id = id + 1
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsDataBuildings WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsDataBuildings (region, id, position, properties, active, gebaeudeklasse, schadensklasse, akteur) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()


    def writeUploadedEinzugsgebieteToDatabase(self, path, filename):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        id = 1
        with open(os.path.join(path, filename), encoding="utf-8-sig") as file:
            dr = csv.DictReader(file, fieldnames=["col1", "col2"], delimiter=";")
            for i in dr:
                conversedCoordinates = utm.to_latlon(float(i["col1"]), float(i["col2"]), self.utm_zone, 'N')
                to_db.append((self.region, id, conversedCoordinates[1], conversedCoordinates[0]))
                id = id + 1
        myCursor.execute("DELETE from regionsEinzugsgebiete WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsEinzugsgebiete (region, id, xCoord, yCoord) VALUES (?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def deleteRegion(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsHeader WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsData WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsSolution WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDataBuildings WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsKataster WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsEinzugsgebiete WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsAuffangbecken WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsLeitgraeben WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM1 WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM5 WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsDGM25 WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsOptimizationParameters WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsMassnahmenKatasterMapping WHERE region = \"" + self.region + "\"")
        conn.commit()
        conn.close()
        print("Data deleted Successfully")

    def deleteBuildings(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsDataBuildings WHERE region = \"" + self.region + "\"")
        conn.commit()
        conn.close()
        print("Buildings deleted Successfully")

    def deleteWholeData(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsAuffangbecken")
        myCursor.execute("DELETE from regionsData")
        myCursor.execute("DELETE from regionsSolution")
        myCursor.execute("DELETE from regionsDataBuildings")
        myCursor.execute("DELETE from regionsKataster")
        myCursor.execute("DELETE from regionsEinzugsgebiete")
        myCursor.execute("DELETE from regionsLeitgraeben")
        myCursor.execute("DELETE from regionsDGM1")
        myCursor.execute("DELETE from regionsDGM5")
        myCursor.execute("DELETE from regionsDGM25")
        myCursor.execute("DELETE from regionsHeader")
        myCursor.execute("DELETE from regionsOptimizationParameters")
        myCursor.execute("DELETE from regionsMassnahmenKatasterMapping")
        conn.commit()
        conn.close()
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("vacuum")
        conn.commit()
        conn.close()
        print("Tabula Rasa")

    def readFullHeaderTable(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsHeader")
        rows = myCursor.fetchall()
        conn.close()
        return rows

    def readRegionHeader(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsHeader WHERE region = \"" + self.region + "\"")
        rows = myCursor.fetchall()
        conn.close()
        return rows[0]


    def readDataFromDatabase(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsData WHERE region = ?", (self.region,))
        rows = myCursor.fetchall()
        myGisDataFloat = []
        for row in rows:
            if len(row) >= 1:
                myGisDataFloat.append([float(row[1]), float(row[2]), float(row[3])])
        conn.close()
        return myGisDataFloat

    def writeOptimalSolutionToDatabase(self, flooded, activeNodes, timeSteps):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("UPDATE regionsHeader SET solved = ?, date_solved = ?, timeHorizon = ? WHERE region = ?", (1, datetime.datetime.now(), timeSteps, self.region))
        myCursor.execute("DELETE from regionsSolution WHERE region = \"" + self.region + "\"")
        to_db = []
        for timeStep in flooded.keys():
            for node in flooded[timeStep].keys():
                to_db.append((self.region, "flooded", timeStep, node[0], node[1], flooded[timeStep][node]))
                to_db.append((self.region, "activeNodes", timeStep, node[0], node[1], activeNodes[timeStep][node]))
        myCursor.executemany("INSERT INTO regionsSolution (region, variableName, timeStep, nodeXCoord, nodeYCoord, variableValue) VALUES (?, ?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def writeGraphToDatabase(self, graph):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        nodesToDB = []
        edgesToDB = []
        myCursor.execute("DELETE from regionsGraphNodes WHERE region = \"" + self.region + "\"")
        myCursor.execute("DELETE from regionsGraphEdges WHERE region = \"" + self.region + "\"")
        for node in graph.nodes:
            nodesToDB.append((self.region, node[0], node[1]))
        for edge in graph.edges():
            edgesToDB.append((self.region, edge[0][0], edge[0][1], edge[1][0], edge[1][1]))
        myCursor.executemany("INSERT INTO regionsGraphNodes (region, nodeNumberXCoord, nodeNumberyCoord) VALUES (?, ?, ?);", nodesToDB)
        myCursor.executemany("INSERT INTO regionsGraphEdges (region, sourceNodeNumberXCoord, sourceNodeNumberyCoord, sinkNodeNumberXCoord, sinkNodeNumberyCoord) VALUES (?, ?, ?, ?, ?);", edgesToDB)
        conn.commit()
        conn.close()

    def readGraphAndOptimalSolutionFromDatabase(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsHeader WHERE region = ?", (self.region,))
        myHeader = myCursor.fetchall()
        if len(myHeader) > 0:
            timeSteps = myHeader[0][5]

        nodes = []
        myCursor.execute("SELECT * FROM regionsGraphNodes WHERE region = ?", (self.region,))
        nodesInDBFormat = myCursor.fetchall()
        for row in nodesInDBFormat:
            nodes.append({"id": "node_" + str(row[1]) + "_"  + str(row[2]),
                          "label": "node_" + str(row[1]) + "_"  + str(row[2]),
                          "x": row[1],
                          "y": row[2],
                          "size": 0.5,
                          "color": "#0A0"})

        edges = []
        myCursor.execute("SELECT * FROM regionsGraphEdges WHERE region = ?", (self.region,))
        edgesInDBFormat = myCursor.fetchall()
        for row in edgesInDBFormat:
            edges.append({"id": "edge_" + str(row[1]) + "_"  + str(row[2]) + "_" + str(row[3]) + "_" + str(row[4]),
                          "source": "node_" + str(row[1]) + "_"  + str(row[2]),
                          "target": "node_" + str(row[3]) + "_"  + str(row[4]),
                          "weight": 300,
                          "size": 2,
                          "type": "arrow"})

        flooded = dict()
        for t in range(1, timeSteps + 1):
            flooded[t] = dict()
        myCursor.execute("SELECT * FROM regionsSolution WHERE region = ? AND variableName = \"flooded\"", (self.region,))
        floodedInDBFormat = myCursor.fetchall()
        for row in floodedInDBFormat:
            flooded[row[2]]["node_" + str(row[3]) + "_" + str(row[4])] = row[5]

        activeNodes = dict()
        for t in range(1, timeSteps + 1):
            activeNodes[t] = dict()
        myCursor.execute("SELECT * FROM regionsSolution WHERE region = ? AND variableName = \"activeNodes\"", (self.region,))
        activeNodesInDBFormat = myCursor.fetchall()
        for row in activeNodesInDBFormat:
            activeNodes[row[2]]["node_" + str(row[3]) + "_" + str(row[4])] = row[5]

        return timeSteps, nodes, edges, flooded, activeNodes

    def readBuildingsForDisplay(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsDataBuildings WHERE region = ?", (self.region,))
        myBuildingsFromDatabase = myCursor.fetchall()
        myBuildingsInDoctionary = dict()
        for building in myBuildingsFromDatabase:
            newBuilding = dict()
            newBuilding["region"] = building[0]
            newBuilding["position"] = self.database_to_polygon_format(building[2])
            newBuilding["properties"] = json.loads(building[3])
            newBuilding["active"] = building[4]
            newBuilding["schadensklasse"] = building[7]
            newBuilding["gebaeudeklasse"] = building[6]
            newBuilding["akteur"] = building[5]
            myBuildingsInDoctionary[building[1]] = newBuilding
        return myBuildingsInDoctionary

    def updateBuildingsFromFrontend(self, data):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        for building in data:
            to_db.append((self.region, int(building), self.polygon_to_database_format(data[building]["position"]), json.dumps(data[building]["properties"]), int(data[building]["active"]), data[building]["akteur"], int(data[building]["gebaeudeklasse"]), int(data[building]["schadensklasse"])))
        myCursor.execute("DELETE from regionsDataBuildings WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsDataBuildings (region, id, position, properties, active, akteur, gebaeudeklasse, schadensklasse) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def updateKatasterFromFrontend(self, data):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        for kataster in data:
            to_db.append((data[kataster]["additionalCost"], self.region, kataster))
        myCursor.executemany("UPDATE regionsKataster SET additionalCost = ? WHERE region = ? AND id = ?", to_db)
        conn.commit()
        conn.close()

    def readEinzugsgebieteForDisplay(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsEinzugsgebiete WHERE region = ?", (self.region,))
        myEinzugsgebieteFromDatabase = myCursor.fetchall()
        myEinzugsgebieteInArray = []
        returnedData = dict()
        for einzugsgebiet in myEinzugsgebieteFromDatabase:
            # myEinzugsgebieteInArray.append((einzugsgebiet[3], einzugsgebiet[2]))
            myEinzugsgebieteInArray.append([einzugsgebiet[3], einzugsgebiet[2]])
        returnedData["Einzugsgebiete"] = myEinzugsgebieteInArray
        returnedData["region"] = self.region
        return returnedData

    def readKatasterForDisplay(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsKataster WHERE region = ? AND inEinzugsgebiet = 1", (self.region,))
        myKatasterFromDatabase = myCursor.fetchall()
        myKatasterInDict = dict()
        returnedData = dict()
        for kataster in myKatasterFromDatabase:
            pointsOfActualKataster = kataster[2].split(";")
            pointsOfPolygon = []
            for point in pointsOfActualKataster:
                newPoint = point.split(",")
                newPointTuple = (float(newPoint[0]), float(newPoint[1]))
                pointsOfPolygon.append(newPointTuple)
            myKatasterInDict[kataster[1]] = {"position": pointsOfPolygon,
                                             "additionalCost": kataster[4]}

        returnedData["Kataster"] = myKatasterInDict
        return returnedData

    def readGridForDisplay(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsDGM25 WHERE region = ? AND inEinzugsgebiet = 1 AND willBeInGraph = 1", (self.region,))
        grid_nodes_DGM_25 = myCursor.fetchall()
        myCursor.execute("SELECT * FROM regionsDGM5 WHERE region = ? AND inEinzugsgebiet = 1 AND willBeInGraph = 1", (self.region,))
        grid_nodes_DGM_5 = myCursor.fetchall()
        myCursor.execute("SELECT * FROM regionsDGM1 WHERE region = ? AND inEinzugsgebiet = 1 AND willBeInGraph = 1", (self.region,))
        grid_nodes_DGM_1 = myCursor.fetchall()

        grid_nodes_every_DGM = []

        for node_25 in grid_nodes_DGM_25:
            grid_nodes_every_DGM.append(node_25 + (25, ))
        for node_5 in grid_nodes_DGM_5:
            grid_nodes_every_DGM.append(node_5 + (5, ))
        for node_1 in grid_nodes_DGM_1:
            grid_nodes_every_DGM.append(node_1 + (1, ))

        print(len(grid_nodes_DGM_25))
        print(len(grid_nodes_DGM_5))
        print(len(grid_nodes_DGM_1))
        print(len(grid_nodes_every_DGM))

        myGridInDict = dict()
        myRelevantInDict = dict()
        myPositionInDict = dict()
        myGeodesicHeight = dict()
        myMitMassnahme = dict()
        myConnectedToRelevantNode = dict()
        myMassnahmenOnNode = dict()
        which_DGM_from = dict()
        returnedData = dict()
        for grid in grid_nodes_every_DGM:
            pointsOfActualGrid = grid[8].split(self.delimiter)
            pointsOfPolygon = []
            for point in pointsOfActualGrid:
                newPoint = point.split(",")
                newPointTuple = (float(newPoint[0]), float(newPoint[1]))
                pointsOfPolygon.append(newPointTuple)
            myGridInDict[grid[1]] = pointsOfPolygon
            myRelevantInDict[grid[1]] = grid[10]
            myPositionInDict[grid[1]] = (grid[2], grid[3])
            myGeodesicHeight[grid[1]] = grid[4]
            myMitMassnahme[grid[1]] = grid[9]
            myConnectedToRelevantNode[grid[1]] = grid[11]
            which_DGM_from[grid[1]] = grid[15]
            if grid[12]:
                if len(grid[12]) > 2:
                    myMassnahmenOnNode[grid[1]] = json.loads(grid[12])
                else:
                    myMassnahmenOnNode[grid[1]] = ""
            else:
                myMassnahmenOnNode[grid[1]] = ""

        returnedData["Relevant"] = myRelevantInDict
        returnedData["Grid"] = myGridInDict
        returnedData["Position"] = myPositionInDict
        returnedData["GeodesicHeight"] = myGeodesicHeight
        returnedData["MitMassnahme"] = myMitMassnahme
        returnedData["connectedToRelevantNode"] = myConnectedToRelevantNode
        returnedData["massnahmenOnNode"] = myMassnahmenOnNode
        returnedData["which_DGM_from"] = which_DGM_from

        return returnedData

    def readDGM25(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsDGM25 WHERE region = ? AND inEinzugsgebiet = 1", (self.region,))
        array_of_25_DGM = myCursor.fetchall()
        myGridInDict = dict()
        myRelevantInDict = dict()
        myPositionInDict = dict()
        myGeodesicHeight = dict()
        myMitMassnahme = dict()
        myConnectedToRelevantNode = dict()
        myMassnahmenOnNode = dict()
        returnedData = dict()
        for grid in array_of_25_DGM:
            pointsOfActualGrid = grid[8].split(self.delimiter)
            pointsOfPolygon = []
            for point in pointsOfActualGrid:
                newPoint = point.split(",")
                newPointTuple = (float(newPoint[0]), float(newPoint[1]))
                pointsOfPolygon.append(newPointTuple)
            myGridInDict[grid[1]] = pointsOfPolygon
            myRelevantInDict[grid[1]] = grid[10]
            myPositionInDict[grid[1]] = (grid[2], grid[3])
            myGeodesicHeight[grid[1]] = grid[4]
            myMitMassnahme[grid[1]] = grid[9]
            myConnectedToRelevantNode[grid[1]] = grid[11]
            if len(grid[12]) > 2:
                myMassnahmenOnNode[grid[1]] = json.loads(grid[12])
            else:
                myMassnahmenOnNode[grid[1]] = ""

        returnedData["Relevant"] = myRelevantInDict
        returnedData["Grid"] = myGridInDict
        returnedData["Position"] = myPositionInDict
        returnedData["GeodesicHeight"] = myGeodesicHeight
        returnedData["MitMassnahme"] = myMitMassnahme
        returnedData["connectedToRelevantNode"] = myConnectedToRelevantNode
        returnedData["massnahmenOnNode"] = myMassnahmenOnNode

        return returnedData

    def updateMitMassnahme(self):
        def computeMitMassnahme(gridSize):
            allBuildings = self.readBuildingsForDisplay()
            allAuffangbecken = self.readAuffangbecken()
            all_leitgraeben = self.read_leitgraeben()
            auffangbeckenAsPolygons = {}
            buildingsAsPolygons = {}
            leitgraeben_as_polylines = dict()
            affected_grids = dict()
            grid_massnahme_counter = dict()
            for auffangbecken in allAuffangbecken:
                auffangbeckenAsPolygons[auffangbecken] = Polygon(allAuffangbecken[auffangbecken]["position"])
                first_point_in_polygon = allAuffangbecken[auffangbecken]["position"][0]
                auffangbecken_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone, 'N')
                auffangbecken_start_xutm = auffangbecken_utm[0]
                auffangbecken_start_yutm = auffangbecken_utm[1]
                auffangbecken_start_xutm_gridSize = self.myround(auffangbecken_start_xutm, gridSize)
                auffangbecken_start_yutm_gridSize = self.myround(auffangbecken_start_yutm, gridSize)
                grids_queue = [(auffangbecken_start_xutm_gridSize, auffangbecken_start_yutm_gridSize)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(auffangbeckenAsPolygons[auffangbecken]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[actual_grid_to_check] + 1
                                affected_grids[actual_grid_to_check][grid_massnahme_counter[actual_grid_to_check]] = {
                                    "type": "auffangbecken",
                                    "id": auffangbecken
                                }
                            else:
                                grid_massnahme_counter[actual_grid_to_check] = 1
                                affected_grids[actual_grid_to_check] = dict()
                                affected_grids[actual_grid_to_check][1] = {
                                    "type": "auffangbecken",
                                    "id": auffangbecken
                                }
                            grids_queue.append((actual_grid_to_check[0] + gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0] - gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + gridSize))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - gridSize))
            for leitgraben in all_leitgraeben:
                leitgraeben_as_polylines[leitgraben] = LineString(all_leitgraeben[leitgraben]["position"])
                first_point_in_polyline = all_leitgraeben[leitgraben]["position"][0]
                leitgraben_utm = utm.from_latlon(first_point_in_polyline[0], first_point_in_polyline[1], self.utm_zone, 'N')
                leitgraben_start_xutm = leitgraben_utm[0]
                leitgraben_start_yutm = leitgraben_utm[1]
                leitgraben_start_xutm_gridSize = self.myround(leitgraben_start_xutm, gridSize)
                leitgraben_start_yutm_gridSize = self.myround(leitgraben_start_yutm, gridSize)
                grids_queue = [(leitgraben_start_xutm_gridSize, leitgraben_start_yutm_gridSize)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(leitgraeben_as_polylines[leitgraben]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[actual_grid_to_check] + 1
                                affected_grids[actual_grid_to_check][grid_massnahme_counter[actual_grid_to_check]] = {
                                    "type": "leitgraben",
                                    "id": leitgraben
                                }
                            else:
                                grid_massnahme_counter[actual_grid_to_check] = 1
                                affected_grids[actual_grid_to_check] = dict()
                                affected_grids[actual_grid_to_check][1] = {
                                    "type": "leitgraben",
                                    "id": leitgraben
                                }
                            grids_queue.append((actual_grid_to_check[0] + gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0] - gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + gridSize))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - gridSize))
            for building in allBuildings:
                buildingsAsPolygons[building] = Polygon(allBuildings[building]["position"])
                first_point_in_polygon = allBuildings[building]["position"][0]
                building_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone, 'N')
                building_start_xutm = building_utm[0]
                building_start_yutm = building_utm[1]
                building_start_xutm_gridSize = self.myround(building_start_xutm, gridSize)
                building_start_yutm_gridSize = self.myround(building_start_yutm, gridSize)
                grids_queue = [(building_start_xutm_gridSize, building_start_yutm_gridSize)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(buildingsAsPolygons[building]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[actual_grid_to_check] + 1
                                affected_grids[actual_grid_to_check][grid_massnahme_counter[actual_grid_to_check]] = {
                                    "type": "building",
                                    "id": building
                                }
                            else:
                                grid_massnahme_counter[actual_grid_to_check] = 1
                                affected_grids[actual_grid_to_check] = dict()
                                affected_grids[actual_grid_to_check][1] = {
                                    "type": "building",
                                    "id": building
                                }
                            grids_queue.append((actual_grid_to_check[0] + gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0] - gridSize, actual_grid_to_check[1]))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + gridSize))
                            grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - gridSize))
            return affected_grids

        def compute_to_db(gridSize):
            affected_grids_gridSize = computeMitMassnahme(gridSize)
            to_db_gridSize = dict()
            for utm_coordinates in affected_grids_gridSize:
                to_db_gridSize[utm_coordinates] = ("yes", 1, json.dumps(affected_grids_gridSize[utm_coordinates]), self.region, utm_coordinates[0], utm_coordinates[1])
            return to_db_gridSize

        def dict_to_array(input_dict):
            returned_array = []
            for key in input_dict:
                returned_array.append(input_dict[key])
            return returned_array

        def compute_additional_to_db_for_5_and_1_DGM(to_db_DGM_25, to_db_dict_5, to_db_dict_1):
            #otherwise, only 5m and 1m grids with Massnahme will be displayed
            for key in to_db_DGM_25:
                xutm_25 = to_db_DGM_25[key][4]
                yutm_25 = to_db_DGM_25[key][5]
                for i in range(5):
                    xutm_5 = xutm_25 + i * 5 - 10
                    for j in range(5):
                        yutm_5 = yutm_25 + j * 5 - 10
                        if (xutm_5, yutm_5) not in to_db_dict_5.keys(): # no Massnahme on 5DGM grid
                            to_db_dict_5[(xutm_5, yutm_5)] = ("no", 1, "", self.region, xutm_5, yutm_5)
                        else: # Massnahme on 5DGM grid -> need to be finer
                            for i1 in range(5):
                                xutm_1 = xutm_5 + i1 - 2
                                for j1 in range(5):
                                    yutm_1 = yutm_5 + j1 - 2
                                    if (xutm_1, yutm_1) not in to_db_dict_1.keys():
                                        to_db_dict_1[(xutm_1, yutm_1)] = ("no", 1, "", self.region, xutm_1, yutm_1)
            return to_db_dict_1, to_db_dict_5

        to_db25_as_dict = compute_to_db(25)
        to_db5_as_dict = compute_to_db(5)
        to_db1_as_dict = compute_to_db(1)


        completed_dict_1, completed_dict_5 = compute_additional_to_db_for_5_and_1_DGM(to_db25_as_dict, to_db5_as_dict, to_db1_as_dict)

        to_db1 = dict_to_array(completed_dict_1)
        to_db5 = dict_to_array(completed_dict_5)
        to_db25 = dict_to_array(to_db25_as_dict)

        conn = self.establishConnection()
        myCursor = conn.cursor()
        print("Start updating database at " + str(datetime.datetime.now()))
        myCursor.execute("UPDATE regionsDGM25 SET mitMassnahme = \'no\', relevantForGraph = 0, connectedToRelevantNodes = 0, massnahmenOnNode = \' "" \', resolveFurther = 0, willBeInGraph = 1 WHERE region = \"" + self.region + "\"")
        myCursor.execute("UPDATE regionsDGM5 SET mitMassnahme = \'no\', relevantForGraph = 0, massnahmenOnNode = \' "" \', resolveFurther = 0, willBeInGraph = 0 WHERE region = \"" + self.region + "\"")
        myCursor.execute("UPDATE regionsDGM1 SET mitMassnahme = \'no\', relevantForGraph = 0, massnahmenOnNode = \' "" \', resolveFurther = 0, willBeInGraph = 0 WHERE region = \"" + self.region + "\"")
        myCursor.executemany("UPDATE regionsDGM25 SET mitMassnahme = ?, relevantForGraph = ?, massnahmenOnNode = ? WHERE region = ? AND xutm = ? AND yutm = ?", to_db25)
        myCursor.executemany("UPDATE regionsDGM5 SET mitMassnahme = ?, relevantForGraph = ?, massnahmenOnNode = ? WHERE region = ? AND xutm = ? AND yutm = ?", to_db5)
        myCursor.executemany("UPDATE regionsDGM1 SET mitMassnahme = ?, relevantForGraph = ?, massnahmenOnNode = ? WHERE region = ? AND xutm = ? AND yutm = ?", to_db1)
        conn.commit()
        conn.close()
        print("End updating database at " + str(datetime.datetime.now()))

    def updateRelevant(self):
        gridData = self.readDGM25()
        headerData = self.readRegionHeader()
        allAuffangbecken = self.readAuffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        gridInstanceGraph = instanceGraphForDGM25(self.region, gridData["Position"], gridData["Relevant"], gridData["GeodesicHeight"], gridData["massnahmenOnNode"], headerData[6], allAuffangbecken, headerData[7] * 1.1, headerData[8])
        print("Computing list of relevant and connected nodes")
        relevantNodes, connectedNodes = gridInstanceGraph.computeListOfRelevantAndConnectedNodes()
        print("Computing initial solution")
        floodingTimes, waterAmounts, modGraph, modArea, waterHeight = gridInstanceGraph.computeInitialSolution(None)
        allBuildings = self.readBuildingsForDisplay()
        print(allBuildings)
        to_db_5 = []
        to_db_1 = []
        nodes_with_buildings_25 = dict()
        auffangbeckenAsPolygons = {}
        buildingsAsPolygons = {}
        leitgraeben_as_polylines = dict()

        affected_grids_25 = dict()
        affected_grids_5 = dict()
        affected_grids_1 = dict()

        for building in allBuildings:
            print(building)
            buildingsAsPolygons[building] = Polygon(allBuildings[building]["position"])
            first_point_in_polygon = allBuildings[building]["position"][0]
            building_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone, 'N')
            building_start_xutm = building_utm[0]
            building_start_yutm = building_utm[1]
            building_start_xutm_25 = self.myround(building_start_xutm, 25)
            building_start_yutm_25 = self.myround(building_start_yutm, 25)
            grids_queue = [(building_start_xutm_25, building_start_yutm_25)]
            checked_grids = dict()
            while grids_queue:
                actual_grid_to_check = grids_queue.pop()
                if actual_grid_to_check not in checked_grids.keys():
                    checked_grids[actual_grid_to_check] = 1
                    actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(buildingsAsPolygons[building]):
                        nodes_with_buildings_25[actual_grid_to_check] = 1
                        # if actual grid to ckeck is not in waterHeight['waterHeight'], this means that the water height is 0
                        if actual_grid_to_check not in waterHeight['waterHeight']:
                            waterHeight['waterHeight'][actual_grid_to_check] = 0
                        if waterHeight['waterHeight'][actual_grid_to_check] > 0:
                            affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                            for i in range(5):
                                actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                                for j in range(5):
                                    actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                        else:
                            affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (1, 1, 0, 1, actual_grid_to_check[0], actual_grid_to_check[1])
                        grids_queue.append((actual_grid_to_check[0] + 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0] - 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + 25))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - 25))

        '''
            building_utm = utm.from_latlon(allBuildings[building]["yCoord"], allBuildings[building]["xCoord"], self.utm_zone, 'N')
            building_xutm = building_utm[0]
            building_yutm = building_utm[1]
            building_xutm_25 = int(self.myround(building_xutm, 25))
            building_yutm_25 = int(self.myround(building_yutm, 25))
            nodes_with_buildings_25[(building_xutm_25, building_yutm_25)] = 1
            if (building_xutm_25, building_yutm_25) in relevantNodes:
                if waterHeight['waterHeight'][(building_xutm_25, building_yutm_25)] > 0:
                    building_xutm_5 = int(self.myround(building_xutm, 5))
                    building_yutm_5 = int(self.myround(building_yutm, 5))
                    for i5 in range(5):
                        iteration_utm_x = building_xutm_25 + (i5 - 2) * 5
                        for j5 in range(5):
                            iteration_utm_y = building_yutm_25 + (j5 - 2) * 5
                            if iteration_utm_x != building_xutm_5 or iteration_utm_y != building_yutm_5:
                                affected_grids_5[(iteration_utm_x, iteration_utm_y)] = (0, 1, iteration_utm_x, iteration_utm_y)
                            else:
                                affected_grids_5[(iteration_utm_x, iteration_utm_y)] = (0, 1, iteration_utm_x, iteration_utm_y)
                    for i1 in range(5):
                        iteration_utm_x = building_xutm_5 + (i1 - 2)
                        for j1 in range(5):
                            iteration_utm_y = building_yutm_5 + (j1 - 2)
                            affected_grids_1[(iteration_utm_x, iteration_utm_y)] = (0, 0, iteration_utm_x, iteration_utm_y)
        '''

        for node in connectedNodes:
            if node in relevantNodes:
                if waterHeight['waterHeight'][node] > 0 and node in nodes_with_buildings_25.keys():
                    affected_grids_25[(node[0], node[1])] = (1, 1, 1, 0, node[0], node[1])
                else:
                    affected_grids_25[(node[0], node[1])] = (1, 1, 0, 1, node[0], node[1])
            else:
                affected_grids_25[(node[0], node[1])] = (0, 1, 0, 1, node[0], node[1])

        for auffangbecken in allAuffangbecken:
            auffangbeckenAsPolygons[auffangbecken] = Polygon(allAuffangbecken[auffangbecken]["position"])
            first_point_in_polygon = allAuffangbecken[auffangbecken]["position"][0]
            auffangbecken_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone, 'N')
            auffangbecken_start_xutm = auffangbecken_utm[0]
            auffangbecken_start_yutm = auffangbecken_utm[1]
            auffangbecken_start_xutm_25 = self.myround(auffangbecken_start_xutm, 25)
            auffangbecken_start_yutm_25 = self.myround(auffangbecken_start_yutm, 25)
            grids_queue = [(auffangbecken_start_xutm_25, auffangbecken_start_yutm_25)]
            checked_grids = dict()
            while grids_queue:
                actual_grid_to_check = grids_queue.pop()
                if actual_grid_to_check not in checked_grids.keys():
                    checked_grids[actual_grid_to_check] = 1
                    actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(auffangbeckenAsPolygons[auffangbecken]):
                        if affected_grids_25[actual_grid_to_check][2] == 0:
                            affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                            for i in range(5):
                                actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                                for j in range(5):
                                    actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                        grids_queue.append((actual_grid_to_check[0] + 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0] - 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + 25))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - 25))

        for leitgraben in all_leitgraeben:
            leitgraeben_as_polylines[leitgraben] = LineString(all_leitgraeben[leitgraben]["position"])
            first_point_in_polyline = all_leitgraeben[leitgraben]["position"][0]
            leitgraben_utm = utm.from_latlon(first_point_in_polyline[0], first_point_in_polyline[1], self.utm_zone, 'N')
            leitgraben_start_xutm = leitgraben_utm[0]
            leitgraben_start_yutm = leitgraben_utm[1]
            leitgraben_start_xutm_25 = self.myround(leitgraben_start_xutm, 25)
            leitgraben_start_yutm_25 = self.myround(leitgraben_start_yutm, 25)
            grids_queue = [(leitgraben_start_xutm_25, leitgraben_start_yutm_25)]
            checked_grids = dict()
            while grids_queue:
                actual_grid_to_check = grids_queue.pop()
                if actual_grid_to_check not in checked_grids.keys():
                    checked_grids[actual_grid_to_check] = 1
                    actual_grid_pos, actual_grid_poly = self.computeGridPolygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(leitgraeben_as_polylines[leitgraben]):
                        #if affected_grids_25[actual_grid_to_check][2] == 0:
                        affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                        for i in range(5):
                            actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                            for j in range(5):
                                actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                actual_grid_pos_5, actual_grid_poly_5 = self.computeGridPolygon((actual_grid_to_check_x_5, actual_grid_to_check_y_5), 5)
                                if Polygon(actual_grid_poly_5).intersects(leitgraeben_as_polylines[leitgraben]):
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (1, 0, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                                    for i1 in range(5):
                                        actual_grid_to_check_x_1 = actual_grid_to_check_x_5 - 2 + i1
                                        for j1 in range(5):
                                            actual_grid_to_check_y_1 = actual_grid_to_check_y_5 - 2 + j1
                                            affected_grids_1[(actual_grid_to_check_x_1, actual_grid_to_check_y_1)] = (0, 1, actual_grid_to_check_x_1, actual_grid_to_check_y_1)
                                else:
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                        grids_queue.append((actual_grid_to_check[0] + 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0] - 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + 25))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - 25))

        to_db = self.dict_to_array(affected_grids_25)
        to_db_5 = self.dict_to_array(affected_grids_5)
        to_db_1 = self.dict_to_array(affected_grids_1)

        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.executemany("UPDATE regionsDGM25 SET relevantForGraph = ?, connectedToRelevantNodes = ?, resolveFurther = ?, willBeInGraph = ? WHERE region = \"" + self.region + "\" AND xutm = ? AND yutm = ?", to_db)
        myCursor.executemany("UPDATE regionsDGM5 SET resolveFurther = ?, willBeInGraph = ? WHERE region = \"" + self.region + "\" AND xutm = ? AND yutm = ?", to_db_5)
        myCursor.executemany("UPDATE regionsDGM1 SET resolveFurther = ?, willBeInGraph = ? WHERE region = \"" + self.region + "\" AND xutm = ? AND yutm = ?", to_db_1)
        conn.commit()
        conn.close()
        print("Successfully updated relevant and connected nodes")

    def updateRelevantFromFrontend(self, dataFromFrontend):
        to_db = []
        for nodeId in dataFromFrontend["Relevant"]:
            to_db.append((dataFromFrontend["Relevant"][nodeId], nodeId))
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.executemany("UPDATE regionsDGM25 SET relevantForGraph = ? WHERE region = \"" + self.region + "\" AND id = ?", to_db)
        conn.commit()
        conn.close()

    def computeOptimalSolution(self):
        gridData = self.readGridForDisplay()
        headerData = self.readRegionHeader()
        allAuffangbecken = self.readAuffangbecken()
        allLeitgraeben = self.read_leitgraeben()
        all_buildings = self.readBuildingsForDisplay()
        optimization_parameters = self.read_optimization_parameters(certain_param_id="init")
        optimization_parameters = optimization_parameters[list(optimization_parameters.keys())[0]]
        gridInstanceGraph = instanceGraph(self.region, gridData["Position"], gridData["Relevant"], gridData["GeodesicHeight"], gridData["massnahmenOnNode"], headerData[6], allAuffangbecken, allLeitgraeben, all_buildings, headerData[7], headerData[8], gridData["which_DGM_from"])
        threshold_for_gefahrenklasse = self.read_gefahrenklasse_threshold()
        initialSolution = None
        graphForIP = gridInstanceGraph.computeInstanceGraph()
        massnahmen_kataster = self.read_massnahmen_kataster()
        all_kataster = self.readKatasterForDisplay()
        all_kataster = all_kataster["Kataster"]
        floodedNodes, waterHeight, auffangbecken_solution, leitgraeben_solution, flow_through_nodes_for_db, handlungsbedarf = gridInstanceGraph.callIPWithEquilibriumWaterLevels(graphForIP, initialSolution, optimization_parameters, threshold_for_gefahrenklasse, massnahmen_kataster, all_kataster)


        to_db = []
        for timeStep in floodedNodes:
            for id in floodedNodes[timeStep]:
                to_db.append((self.region, "flooded", timeStep, id, gridData["Position"][id][0], gridData["Position"][id][1], floodedNodes[timeStep][id]))
        for timeStep in waterHeight:
            for id in waterHeight[timeStep]:
                to_db.append((self.region, "waterHeight", timeStep, id, gridData["Position"][id][0], gridData["Position"][id][1], waterHeight[timeStep][id]))
        for a in auffangbecken_solution:
            to_db.append((self.region, "auffangbecken", 1, a, None, None, round(auffangbecken_solution[a])))
        for l in leitgraeben_solution:
            to_db.append((self.region, "leitgraben", 1, l, None, None, round(leitgraeben_solution[l])))
        for id in flow_through_nodes_for_db:
            to_db.append((self.region, "flow_through_nodes", 1, id, gridData["Position"][id][0], gridData["Position"][id][1], flow_through_nodes_for_db[id]))
        for b in handlungsbedarf:
            to_db.append((self.region, "handlungsbedarf", 1, b, None, None, handlungsbedarf[b]))

        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsSolution WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsSolution (region, variableName, timeStep, id, nodeXCoord, nodeYCoord, variableValue) VALUES (?, ?, ?, ?, ?, ?, ?);", to_db)
        myCursor.execute("UPDATE regionsHeader SET solved = ?, date_solved = ? WHERE region = \"" + self.region + "\"", (1, str((datetime.datetime.now()))))
        conn.commit()
        conn.close()

    def readOptimalSolution(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsSolution WHERE region = ?", (self.region,))
        mySolutionFromDatabase = myCursor.fetchall()
        solution_as_dict = dict()
        floodedNodesWithTimeSteps = dict()
        auffangbecken_in_solution = dict()
        leitgraeben_in_solution = dict()
        waterHeight = dict()
        flow_through_nodes = dict()
        handlungsbedarf = dict()
        for solution in mySolutionFromDatabase:
            if solution[1] == "flooded":
                if solution[2] not in floodedNodesWithTimeSteps:
                    floodedNodesWithTimeSteps[solution[2]] = dict()
                floodedNodesWithTimeSteps[solution[2]][solution[3]] = int(solution[6])
            if solution[1] == "auffangbecken":
                auffangbecken_in_solution[solution[3]] = int(solution[6])
            if solution[1] == "leitgraben":
                leitgraeben_in_solution[solution[3]] = int(solution[6])
            if solution[1] == "waterHeight":
                waterHeight[solution[3]] = float(solution[6])
            if solution[1] == "flow_through_nodes":
                flow_through_nodes[solution[3]] = float(solution[6])
            if solution[1] == "handlungsbedarf":
                handlungsbedarf[solution[3]] = float(solution[6])
        conn.close()
        lastTimestep = max(floodedNodesWithTimeSteps.keys())
        solution_as_dict["Flooded"] = floodedNodesWithTimeSteps[lastTimestep]
        solution_as_dict["auffangbecken"] = auffangbecken_in_solution
        solution_as_dict["leitgraeben"] = leitgraeben_in_solution
        solution_as_dict["waterHeight"] = waterHeight
        solution_as_dict["flow_through_nodes"] = flow_through_nodes
        solution_as_dict["handlungsbedarf"] = handlungsbedarf
        return solution_as_dict

    def readAuffangbecken(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsAuffangbecken WHERE region = ?", (self.region,))
        myAuffangbeckenFromDatabase = myCursor.fetchall()
        auffangbeckenForFrontend = dict()
        for auffangbecken in myAuffangbeckenFromDatabase:
            pointsOfAuffangbecken = auffangbecken[2].split(self.delimiter)
            pointsOfPolygon = []
            for point in pointsOfAuffangbecken:
                newPoint = point.split(",")
                newPointTuple = (float(newPoint[0]), float(newPoint[1]))
                pointsOfPolygon.append(newPointTuple)
            auffangbeckenForFrontend[auffangbecken[1]] = {
                "position": pointsOfPolygon,
                "depth": auffangbecken[3],
                "cost": auffangbecken[4]
            }
        return auffangbeckenForFrontend

    def read_leitgraeben(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsLeitgraeben WHERE region = ?", (self.region,))
        myLeitgraebenFromDatabase = myCursor.fetchall()
        leitgraebenForFrontend = dict()
        for leitgraben in myLeitgraebenFromDatabase:
            pointsOfleitgraben = leitgraben[2].split(self.delimiter)
            pointsOfPolygon = []
            for point in pointsOfleitgraben:
                newPoint = point.split(",")
                newPointTuple = (float(newPoint[0]), float(newPoint[1]))
                pointsOfPolygon.append(newPointTuple)
            leitgraebenForFrontend[leitgraben[1]] = {
                "position": pointsOfPolygon,
                "depth": leitgraben[3],
                "cost": leitgraben[4],
                "leitgrabenOderBoeschung": leitgraben[6]
            }
        return leitgraebenForFrontend

    def updateAuffangbeckenFromFrontend(self, data):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        for auffangbecken in data:
            positionString = ""
            for point in data[auffangbecken]["position"]:
                positionString = positionString + str(point[0]) + "," + str(point[1]) + self.delimiter
            positionString = positionString[:-1]
            to_db.append((self.region, int(auffangbecken), positionString, data[auffangbecken]["depth"], data[auffangbecken]["cost"]))
        myCursor.execute("DELETE from regionsAuffangbecken WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsAuffangbecken (region, id, position, depth, cost) VALUES (?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def updateLeitgraebenFromFrontend(self, data):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        for leitgraben in data:
            positionString = ""
            for point in data[leitgraben]["position"]:
                positionString = positionString + str(point[0]) + "," + str(point[1]) + self.delimiter
            positionString = positionString[:-1]
            to_db.append((self.region, int(leitgraben), positionString, data[leitgraben]["depth"], data[leitgraben]["cost"], data[leitgraben]["leitgrabenOderBoeschung"]))
        myCursor.execute("DELETE from regionsLeitgraeben WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsLeitgraeben (region, id, position, depth, cost, leitgrabenOderBoeschung) VALUES (?, ?, ?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def transformStringToPolygonList(self, polygonString):
        points = polygonString.split(self.delimiter)
        pointsOfPolygon = []
        for point in points:
            newPoint = point.split(",")
            newPointTuple = (float(newPoint[0]), float(newPoint[1]))
            pointsOfPolygon.append(newPointTuple)
        return pointsOfPolygon

    def updateHeaderDataFromFrontend(self, data):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        to_db = []
        for region in data:
            to_db.append((data[region]["amount"], data[region]["duration"], region))
        myCursor.executemany("UPDATE regionsHeader SET rainAmount = ?, rainDuration = ? WHERE region = ?", to_db)
        conn.commit()
        conn.close()

    def read_gebaeudeklasse_to_schadensklasse(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM globalGebaeudeklasseToSchadensklasse")
        gebaeudeklasse_to_schadensklasse_from_db = myCursor.fetchall()
        gebaeudeklasse_to_schadensklasse_as_dict = dict()
        for entry in gebaeudeklasse_to_schadensklasse_from_db:
            gebaeudeklasse_to_schadensklasse_as_dict[entry[0]] = entry[1]
        return gebaeudeklasse_to_schadensklasse_as_dict

    def read_gebaeudeklasse_to_akteur(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM globalGebaeudeklasseToAkteur")
        gebaeudeklasse_to_akteur_from_db = myCursor.fetchall()
        gebaeudeklasse_to_akteur_as_dict = dict()
        for entry in gebaeudeklasse_to_akteur_from_db:
            gebaeudeklasse_to_akteur_as_dict[entry[0]] = entry[1]
        return gebaeudeklasse_to_akteur_as_dict

    def initialize_optimization_parameters(self, param_id):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        parameters = {
            "gefahrenklasse1schadensklasse1": 1,
            "gefahrenklasse2schadensklasse1": 2,
            "gefahrenklasse3schadensklasse1": 3,
            "gefahrenklasse4schadensklasse1": 4,
            "gefahrenklasse1schadensklasse2": 2,
            "gefahrenklasse2schadensklasse2": 3,
            "gefahrenklasse3schadensklasse2": 4,
            "gefahrenklasse4schadensklasse2": 5,
            "gefahrenklasse1schadensklasse3": 3,
            "gefahrenklasse2schadensklasse3": 4,
            "gefahrenklasse3schadensklasse3": 5,
            "gefahrenklasse4schadensklasse3": 6,
            "gefahrenklasse1schadensklasse4": 4,
            "gefahrenklasse2schadensklasse4": 5,
            "gefahrenklasse3schadensklasse4": 6,
            "gefahrenklasse4schadensklasse4": 7,
            "budget": 3000000,
            "gewichtungNone": 1,
            "gewichtungBuerger": 1,
            "gewichtungKommune": 1,
            "gewichtungReligion": 1,
            "gewichtungLokaleWirtschaft": 1,
            "gewichtungLandwirtschaft": 1,
            "gewichtungForstwirtschaft": 1,
            "maxAnzahlGelb": 5,
            "maxAnzahlRot": 2,
            "genauigkeitDerGeodaetischenHoeheIncm": 5,
            "mipgap": 5,
            "timeout": 999999
        }
        to_db = []
        for key, value in parameters.items():
            to_db.append((self.region, param_id, key, value))
        myCursor.executemany("INSERT INTO regionsOptimizationParameters (region, parameterId, parameterName, parameterValue) VALUES (?, ?, ?, ?);", to_db)
        conn.commit()
        conn.close()

    def read_optimization_parameters(self, *args, **kwargs):
        diffrent_region = kwargs.get('diffrent_region', None)
        certain_param_id = kwargs.get('certain_param_id', None)
        conn = self.establishConnection()
        myCursor = conn.cursor()
        if diffrent_region:
            if certain_param_id:
                myCursor.execute("SELECT * FROM regionsOptimizationParameters WHERE region = ? AND parameterId = ?", (diffrent_region, certain_param_id))
            else:
                myCursor.execute("SELECT * FROM regionsOptimizationParameters WHERE region = ?", (diffrent_region,))
        else:
            if certain_param_id:
                myCursor.execute("SELECT * FROM regionsOptimizationParameters WHERE region = ? AND parameterId = ?", (self.region, certain_param_id))
            else:
                myCursor.execute("SELECT * FROM regionsOptimizationParameters WHERE region = ?", (self.region,))
        optimization_parameters_from_db = myCursor.fetchall()
        optimization_parameters_as_dict = dict()
        for param_db in optimization_parameters_from_db:
            if param_db[1] not in optimization_parameters_as_dict.keys():
                optimization_parameters_as_dict[param_db[1]] = dict()
            optimization_parameters_as_dict[param_db[1]][param_db[2]] = param_db[3]
        conn.close()
        return optimization_parameters_as_dict

    def read_all_optimization_parameters(self):
        headers = self.readFullHeaderTable()
        all_params = dict()
        for header in headers:
            optimization_parameters_for_region = self.read_optimization_parameters(diffrent_region=header[0])
            all_params[header[0]] = optimization_parameters_for_region
        return all_params

    def update_optimization_parameters_from_frontend(self, returned_data):
        to_db = []
        for region in returned_data.keys():
            for param_id in returned_data[region].keys():
                for param_name in returned_data[region][param_id].keys():
                    to_db.append((region, param_id, param_name, returned_data[region][param_id][param_name]))
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE FROM regionsOptimizationParameters")
        myCursor.executemany("INSERT INTO regionsOptimizationParameters VALUES (?, ?, ?, ?)", to_db)
        conn.commit()
        conn.close()

    def read_gefahrenklasse_threshold(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM globalThresholdForGefahrenklasse")
        threshold_for_gefahrenklasse = myCursor.fetchall()
        threshold_for_gefahrenklasse_as_dict = dict()
        for entry in threshold_for_gefahrenklasse:
            threshold_for_gefahrenklasse_as_dict[entry[0]] = entry[1]
        threshold_for_gefahrenklasse_as_dict[0] = 0.001
        return threshold_for_gefahrenklasse_as_dict

    def copy_region_to(self, new_region):
        def copy_database(database_name):
            print("Copying Database ", database_name)
            conn = self.establishConnection()
            myCursor = conn.cursor()
            myCursor.execute("SELECT * FROM \"" + database_name + "\" WHERE region = ?", (self.region,))
            data_from = myCursor.fetchall()
            data_to = [(new_region,) + x[1:] for x in data_from]
            number_of_entries = len(data_to)
            myCursor.execute("DELETE from \"" + database_name + "\" WHERE region = \"" + new_region + "\"")
            if number_of_entries > 0:
                exec_text = "INSERT INTO " + database_name + " VALUES (" + ','.join(['?'] * len(data_to[0])) + ')'
                myCursor.executemany(exec_text, data_to)
            conn.commit()
            conn.close()
        copy_database("regionsAuffangbecken")
        copy_database("regionsDGM1")
        copy_database("regionsDGM5")
        copy_database("regionsDGM25")
        copy_database("regionsDataBuildings")
        copy_database("regionsEinzugsgebiete")
        copy_database("regionsHeader")
        copy_database("regionsKataster")
        copy_database("regionsLeitgraeben")
        copy_database("regionsOptimizationParameters")
        copy_database("regionsSolution")
        copy_database("regionsMassnahmenKatasterMapping")

    def compute_massnahmen_kataster(self):
        all_kataster = self.readKatasterForDisplay()
        all_kataster = all_kataster["Kataster"]
        all_auffangbecken = self.readAuffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        to_db = []
        print("Start computing massnahmen kataster" , datetime.datetime.now())
        for kataster in all_kataster:
            einzugsgebiete_polygon = Polygon(all_kataster[kataster]["position"])
            for auffangbecken in all_auffangbecken:
                auffangbecken_polygon = Polygon(all_auffangbecken[auffangbecken]["position"])
                if auffangbecken_polygon.intersects(einzugsgebiete_polygon):
                    to_db.append((self.region, "Auffangbecken", auffangbecken, kataster))
            for leitgraben in all_leitgraeben:
                leitgraben_polygon = Polygon(all_leitgraeben[leitgraben]["position"])
                if leitgraben_polygon.intersects(einzugsgebiete_polygon):
                    to_db.append((self.region, "Leitgraben", leitgraben, kataster))
        print("End computing massnahmen kataster" , datetime.datetime.now())
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("DELETE from regionsMassnahmenKatasterMapping WHERE region = \"" + self.region + "\"")
        myCursor.executemany("INSERT INTO regionsMassnahmenKatasterMapping VALUES (?, ?, ?, ?)", to_db)
        conn.commit()
        conn.close()

    def read_massnahmen_kataster(self):
        conn = self.establishConnection()
        myCursor = conn.cursor()
        myCursor.execute("SELECT * FROM regionsMassnahmenKatasterMapping WHERE region = ?", (self.region,))
        data_from = myCursor.fetchall()
        conn.close()
        return data_from