import csv
from datetime import datetime
import json
import utm
import fiona
import xml.etree.ElementTree as Et

from flask import url_for, redirect, flash, abort, request
from flask_login import current_user, login_user
from shapely.geometry import Polygon, LineString
from sqlalchemy.orm import make_transient

from akut.instanceGraph import *
from akut.instanceGraphForDGM25 import *
import zipfile
from akut import login_db, User_Region, Region, User, Message, GlobalToAkteur, GlobalToSchadensklasse, \
    GlobalForGefahrensklasse, DGM1, DGM5, DGM25, Auffangbecken, Data, DataBuildings, Einzugsgebiete, Header, Kataster, \
    Leitgraeben, MassnahmenKatasterMapping, OptimizationParameters, Solutions, bcrypt


class LoginDbHandler:
    def __init__(self, regionname):
        self.regionname = regionname
        self.region = Region.query.filter_by(name=regionname).first()
        self.user = current_user
        self.database = login_db
        self.delimiter = ";"
        self.utm_zone = 32
        self.utm_zone_kataster = 32
        self.customer = "Other"

    # ------------------------------------
    # ---------- USERMANAGEMENT ----------
    # ------------------------------------
    @staticmethod
    def login_user(email, pw, remember):
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, pw):
            login_user(user, remember=remember)
        else:
            flash('Login fehlgeschlagen. Bitte überprüfen Sie E-Mail and Passwort.', 'danger')

    def register_user(self, username, email, pw):
        if username in ['username', 'Username', 'USERNAME']:
            return True
        else:
            self.database.session.add(User(username=username, email=email, password=pw))
            self.database.session.commit()
            flash(f'Account erstellt für {username}!', 'success')
            return False

    def show_messages(self):
        for message in self.user.messages_recieved:
            if print(message) is not 'Ignore Message':
                flash(message, 'info')
            self.database.session.delete(message)
        self.database.session.commit()

    def get_user_region_list(self):
        region_array = []
        regions_id = User_Region.query.filter_by(user_id=self.user.id).all()
        for r_id in regions_id:
            region_id = r_id.region_id
            r = Region.query.filter_by(id=region_id).first()
            region_array.append(r.name)
        return region_array

    def delete_region_association(self):
        self.check_rights()
        if self.region.admin_id == current_user.id:
            if len(self.region.users) == 1:  # Wenn kein anderer User Region hat: Admin die Region übertragen
                self.database.session.add(
                    User_Region(region_id=self.region.id, user_id=User.query.filter_by(username="admin").first().id))
                flash(f'Geben Sie vorher den Admin der Region "{self.region.name}" an User "admin" ab!', 'info')
            else:
                flash(f'Geben Sie vorher den Admin der Region "{self.region.name}" ab!', 'warning')
            return redirect(url_for('account'))
        delete_object = User_Region.query.filter_by(user_id=current_user.id).filter_by(
            region_id=self.region.id).first()
        self.database.session.delete(delete_object)
        flash(f'Region-Zuweisung für "{self.region.name}" gelöscht!', 'success')
        self.database.session.commit()

    def share_region(self, user_manage):
        self.check_rights()
        if User_Region.query.filter_by(user_id=user_manage.id).filter_by(region_id=self.region.id).first():
            flash(f'User "{user_manage.username}" hat Region bereits!', 'warning')
            return redirect(url_for('account'))
        self.region.users.append(User_Region(user=user_manage, provided_by_id=current_user.id))
        flash(f'"{self.region.name}" freigegeben für {user_manage.username}!', 'success')
        message = Message(user_to_id=user_manage.id, user_from_id=current_user.id, region_id=self.region.id,
                          type="Freigegeben")
        self.database.session.add(message)
        self.database.session.commit()

    def hand_over_region(self, user_manage):
        self.check_rights()
        if not self.region.admin_id == current_user.id:
            flash(f'Sie sind kein Admin der Region "{self.region.name}"!', 'warning')
            return redirect(url_for('account'))
        self.region.admin_id = user_manage.id
        flash(f'Admin von "{self.region.name}" abgegeben an "{user_manage.username}"!', 'success')
        message = Message(user_to_id=user_manage.id, user_from_id=current_user.id, region_id=self.region.id,
                          type="Admin abgegeben")
        self.database.session.add(message)
        self.database.session.commit()

    def change_pw(self, new_pw):
        hashed_password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        self.user.password = hashed_password
        self.database.session.commit()
        flash('Passwort aktualisiert!', 'success')

    def get_user_regions(self):
        region_array = []
        association_list = User_Region.query.filter_by(user=self.user).all()
        region_ids = []
        for association in association_list:
            region_ids.append(association.region_id)
        for region_id in region_ids:
            region_array.append(Region.query.filter_by(id=region_id).first())
        return region_array

    @staticmethod
    def get_all_region_names():
        region_array = []
        for region in Region.query.all():
            region_array.append(region.name)
        return region_array

    def get_all_region_information(self):
        regions = Region.query.all()
        region_dict = dict()
        for region in regions:
            dictionary = self.db_object_to_dict(region)
            region_dict[region.name] = dictionary
        return region_dict

    def get_all_user_information(self):
        users = User.query.all()
        region_dict = dict()
        for user in users:
            dictionary = self.db_object_to_dict(user)
            region_dict[user.username] = dictionary
        return region_dict

    def get_all_information(self, Database, key):
        data = Database.query.all()
        returned_dict = dict()
        for d in data:
            dictionary = self.compute_additional_information(self.db_object_to_dict(d), Database)
            real_key = dictionary[key]
            returned_dict[real_key] = dictionary
        return returned_dict

    def get_information_for_admin_edit(self, Database, identification):
        db_object = Database.query.filter_by(id=identification).first()
        returned_dict = self.compute_additional_information(self.db_object_to_dict(db_object), Database)
        return returned_dict

    @staticmethod
    def compute_additional_information(dictionary, Database):
        if Database == Region:
            dictionary["users"], dictionary["users_not"] = [], []
            for users_from_db in User.query.all():
                associated = False
                for association in users_from_db.regions:
                    if dictionary["id"] == association.region_id:
                        associated = True
                if associated:
                    dictionary["users"].append(users_from_db.username)
                else:
                    dictionary["users_not"].append(users_from_db.username)
                dictionary["admin_name"] = User.query.filter_by(id=dictionary["admin_id"]).first().username
            dictionary["users_string"] = ", ".join(dictionary["users"])

        if Database == User:
            dictionary["regions"], dictionary["regions_not"], dictionary["admin_regions"] = [], [], []
            for users_from_db in Region.query.all():
                associated = False
                for association in users_from_db.users:
                    if dictionary["id"] == association.user_id:
                        associated = True
                if associated:
                    dictionary["regions"].append(users_from_db.name)
                else:
                    dictionary["regions_not"].append(users_from_db.name)
            for admin_region in User.query.filter_by(id=dictionary["id"]).first().admin_regions:
                dictionary["admin_regions"].append(admin_region.name)

            dictionary["regions_string"] = ", ".join(dictionary["regions"])
        return dictionary

    def update_region(self, returned_data_dict):
        # Check für "falsche" Namensänderungen, Init
        if not returned_data_dict["name"]:
            flash('Bitte Regionennamen angeben!', 'info')
            return False
        region_obj = Region.query.filter_by(name=returned_data_dict["name"]).first()
        if region_obj:
            if not region_obj.id == int(returned_data_dict["region_id"]):
                flash(f'Region mit Namen "{returned_data_dict["name"]}" existiert bereits! Bitte anderen Namen wählen!',
                      'info')
                return False
        # Init Änderungen
        changed = False
        self.region = Region.query.filter_by(id=int(returned_data_dict["region_id"])).first()
        self.regionname = self.region.name
        # Name
        if not returned_data_dict["name"] == self.region.name:
            changed = True
            self.copy_region_to(returned_data_dict["name"])
            self.delete_region()
            self.region = Region.query.filter_by(name=returned_data_dict["name"]).first()
        # Admin
        new_admin_user = User.query.filter_by(username=returned_data_dict["change_admin"]).first()
        if not new_admin_user.id == self.region.admin_id:
            changed = True
            print(new_admin_user.admin_regions)
            self.region.admin_id = new_admin_user.id
            print(new_admin_user.admin_regions)
        # User entfernen
        for user in returned_data_dict["remove_user[]"]:
            if not user == returned_data_dict["change_admin"]:  # Um nicht auf einmal neuen admin & direkt entfernen
                user_id = User.query.filter_by(username=user).first().id
                if user_id:
                    changed = True
                    User_Region.query.filter_by(region_id=self.region.id).filter_by(user_id=user_id).delete()
            else:
                flash('Neuer Admin der Region kann nicht entfernt werden', 'warning')
        # User hinzufügen
        for user in returned_data_dict["insert_user[]"]:
            user_id = User.query.filter_by(username=user).first().id
            if user_id:
                changed = True
                self.database.session.add(User_Region(user_id=user_id, region_id=self.region.id))
        # Commit/Flash
        if changed:
            self.database.session.commit()
            flash("Region geändert.", 'success')
        else:
            flash("Region ungeändert.", 'info')
        return True

    def update_user(self, returned_data_dict):
        # Check für "falsche" Namensänderungen, Init
        if not returned_data_dict["name"]:
            flash('Bitte Usernamen angeben!', 'info')
            return False
        user_obj_check_duplicate = User.query.filter_by(username=returned_data_dict["name"]).first()
        if user_obj_check_duplicate:
            if not user_obj_check_duplicate.id == int(returned_data_dict["user_id"]):
                flash(f'User mit Namen "{returned_data_dict["name"]}" existiert bereits! Bitte anderen Namen wählen!',
                      'info')
                return False
        changed = False
        user_obj = User.query.filter_by(id=returned_data_dict["user_id"]).first()

        # Name
        if not returned_data_dict["name"] == user_obj.username:
            changed = True
            user_obj.username = returned_data_dict["name"]
        # Region entfernen
        for region in returned_data_dict["remove_region[]"]:
            region_id = Region.query.filter_by(name=region).first().id
            if region_id:
                changed = True
                User_Region.query.filter_by(region_id=region_id).filter_by(user_id=user_obj.id).delete()
        # Region hinzufügen
        for region in returned_data_dict["insert_region[]"]:
            region_id = Region.query.filter_by(name=region).first().id
            if region_id:
                changed = True
                self.database.session.add(User_Region(user_id=user_obj.id, region_id=region_id))
        # Commit/Flash
        if changed:
            self.database.session.commit()
            flash("User geändert.", 'success')
        else:
            flash("User ungeändert.", 'info')
        return True

    def delete_user(self, userid):
        user = User.query.filter_by(id=userid).first()
        if user.username == "admin":
            flash('Admin-User nicht löschbar!', 'warning')
            return redirect(url_for('panel'))
        # Entferne Associations
        User_Region.query.filter_by(user_id=user.id).delete()
        # Entferne provided_by in Accociations
        provided_list = User_Region.query.filter_by(provided_by_id=user.id).all()
        for prov in provided_list:
            prov.provided_by_id = None
        # Gebe Admin ab
        admin_region_list = Region.query.filter_by(admin_id=user.id).all()
        for admR in admin_region_list:
            if not list(admR.users) == []:
                admR.admin_id = admR.users[0].user_id
            else:
                admin_user = User.query.filter_by(username="admin").first()
                self.database.session.add(User_Region(region_id=admR.id, user_id=admin_user.id))
                admR.admin_id = admin_user.id
        # Passe Gesendete Messages an
        user_messages_sent = user.messages_sent
        for message in user_messages_sent:
            if message is None:
                continue
            message.user_from_id = User.query.filter_by(username="admin").first().id
            message.text.append(" Der entsprechende User existiert nicht mehr!")
        # Entferne empfangene Messages
        Message.query.filter_by(user_to_id=user.id).delete()
        # Entferne User
        self.database.session.query(User).filter(User.username == user.username).delete()
        self.database.session.commit()
        print(f"deleted {user.username}")

    def check_rights(self):
        association = User_Region.query.filter_by(user_id=self.user.id).filter_by(
            region_id=self.region.id).first()
        if not association:
            return abort(403)

    # ------------------------------
    # ---------- NUR INTERN --------
    # ------------------------------

    @staticmethod
    def myround(x, base=5):
        return base * round(x / base)

    @staticmethod
    def dict_to_array(input_dict):
        returned_array = []
        for key in input_dict:
            if key != "region_id":
                returned_array.append(input_dict[key])
        return returned_array

    @staticmethod
    def polygon_to_database_format(array_in_polygon_format):
        string_in_polygon_format = ';'.join([str(x[0]) + ',' + str(x[1]) for x in array_in_polygon_format])
        return string_in_polygon_format

    @staticmethod
    def database_to_polygon_format(string_in_database_format):
        array_in_polygon_format = [(float(x.split(',')[0]), float(x.split(',')[1])) for x in
                                   string_in_database_format.split(';')]
        return array_in_polygon_format

    def compute_grid_polygon(self, centre, gridSize):
        polygon_point_upper_left = utm.to_latlon(centre[0] - gridSize / 2, centre[1] + gridSize / 2, self.utm_zone, 'N')
        polygon_point_upper_right = utm.to_latlon(centre[0] + gridSize / 2, centre[1] + gridSize / 2, self.utm_zone,
                                                  'N')
        polygon_point_lower_right = utm.to_latlon(centre[0] + gridSize / 2, centre[1] - gridSize / 2, self.utm_zone,
                                                  'N')
        polygon_point_lower_left = utm.to_latlon(centre[0] - gridSize / 2, centre[1] - gridSize / 2, self.utm_zone, 'N')
        position = str(polygon_point_upper_left[0]) + "," + str(polygon_point_upper_left[1]) + self.delimiter + str(
            polygon_point_upper_right[0]) + "," + str(polygon_point_upper_right[1]) + self.delimiter + str(
            polygon_point_lower_right[0]) + "," + str(polygon_point_lower_right[1]) + self.delimiter + str(
            polygon_point_lower_left[0]) + "," + str(polygon_point_lower_left[1])
        new_polygon_array = [polygon_point_upper_left, polygon_point_upper_right, polygon_point_lower_right,
                             polygon_point_lower_left]
        return position, new_polygon_array

    @staticmethod
    def db_object_to_dict(db_object):
        dictionary = dict((col, getattr(db_object, col)) for col in db_object.__table__.columns.keys())
        return dictionary

    # ---------------------------------------------
    # ---------- MEHRFACH GENUTZTE READS ----------
    # ---------------------------------------------

    def read_user_header_table(self):
        header_dict = dict()
        for region in self.get_user_regions():
            for header in region.header:
                header_dict[header.region] = self.db_object_to_dict(header)
        return header_dict

    def read_user_header_table_solved_only(self):
        header_dict = dict()
        for region in self.get_user_regions():
            for header in region.header:
                if header.solved == 1:
                    header_dict[header.region] = self.db_object_to_dict(header)
        return header_dict

    def read_region_header(self):
        return self.db_object_to_dict(Header.query.filter_by(region=self.region.name).first())

    def read_einzugsgebiete_for_display(self):
        returned_data = dict()
        e_array = []
        einzugsgebiete = Einzugsgebiete.query.filter_by(region=self.region.name).all()
        for e in einzugsgebiete:
            e_array.append([e.yCoord, e.xCoord])
        returned_data["Einzugsgebiete"] = e_array
        returned_data["region"] = self.region.name
        return returned_data

    def read_kataster_for_display(self):
        my_kataster_in_dict = dict()
        returned_data = dict()
        kataster = Kataster.query.filter_by(region=self.region.name).filter_by(inEinzugsgebiete=1).all()
        for k in kataster:
            points = k.position.split(";")
            points_of_polygon = []
            for point in points:
                new_point = point.split(",")
                new_point_tuple = (float(new_point[0]), float(new_point[1]))
                points_of_polygon.append(new_point_tuple)
            my_kataster_in_dict[k.id] = {"position": points_of_polygon, "additionalCost": k.additionalCost}
        returned_data["Kataster"] = my_kataster_in_dict
        return returned_data

    def read_buildings_for_display(self):
        buildings = DataBuildings.query.filter_by(region=self.region.name).all()
        my_buildings_in_dictionary = dict()
        for b in buildings:
            b_dict = self.db_object_to_dict(b)
            new_building = dict()
            for key, value in b_dict.items():
                new_building[key] = value
                new_building["position"] = self.database_to_polygon_format(b_dict["position"])
            my_buildings_in_dictionary[b_dict["id"]] = new_building
        return my_buildings_in_dictionary

    def read_grid_for_display(self):
        grid_nodes_dgm_1 = DGM1.query.filter_by(region=self.region.name).filter_by(inEinzugsgebiete=1).filter_by(
            willBeInGraph=1).all()
        grid_nodes_dgm_5 = DGM5.query.filter_by(region=self.region.name).filter_by(inEinzugsgebiete=1).filter_by(
            willBeInGraph=1).all()
        grid_nodes_dgm_25 = DGM25.query.filter_by(region=self.region.name).filter_by(inEinzugsgebiete=1).filter_by(
            willBeInGraph=1).all()
        grid_nodes_every_dgm = []
        for node1 in grid_nodes_dgm_1:
            dgm_dict = self.db_object_to_dict(node1)
            dgm_dict["which_dgm_from"] = 1
            grid_nodes_every_dgm.append(dgm_dict)
        for node5 in grid_nodes_dgm_5:
            dgm_dict = self.db_object_to_dict(node5)
            dgm_dict["which_dgm_from"] = 5
            grid_nodes_every_dgm.append(dgm_dict)
        for node25 in grid_nodes_dgm_25:
            dgm_dict = self.db_object_to_dict(node25)
            dgm_dict["which_dgm_from"] = 25
            grid_nodes_every_dgm.append(dgm_dict)

        print(len(grid_nodes_dgm_25))
        print(len(grid_nodes_dgm_5))
        print(len(grid_nodes_dgm_1))
        print(len(grid_nodes_every_dgm))

        my_grid_in_dict = dict()
        my_relevant_in_dict = dict()
        my_position_in_dict = dict()
        my_geodesic_height = dict()
        my_mit_massnahme = dict()
        my_connected_to_relevant_node = dict()
        my_massnahmen_on_node = dict()
        which_dgm_from = dict()
        returned_data = dict()

        for grid in grid_nodes_every_dgm:
            points_of_polygon = []
            points_of_actual_grid = grid["gridPolyline"].split(self.delimiter)
            for point in points_of_actual_grid:
                new_point = point.split(",")
                new_point_tuple = (float(new_point[0]), float(new_point[1]))
                points_of_polygon.append(new_point_tuple)
            my_grid_in_dict[grid["id"]] = points_of_polygon
            my_relevant_in_dict[grid["id"]] = grid["relevantForGraph"]
            my_position_in_dict[grid["id"]] = (grid["xutm"], grid["yutm"])
            my_geodesic_height[grid["id"]] = grid["geodesicHeight"]
            my_mit_massnahme[grid["id"]] = grid["mitMassnahme"]
            my_connected_to_relevant_node[grid["id"]] = grid["connectedToRelevantNodes"]
            which_dgm_from[grid["id"]] = grid["which_dgm_from"]
            if grid["massnahmeOnNode"]:
                if len(grid["massnahmeOnNode"]) > 2:
                    my_massnahmen_on_node[grid["id"]] = json.loads(grid["massnahmeOnNode"])
                else:
                    my_massnahmen_on_node[grid["id"]] = ""
            else:
                my_massnahmen_on_node[grid["id"]] = ""

        returned_data["Relevant"] = my_relevant_in_dict
        returned_data["Grid"] = my_grid_in_dict
        returned_data["Position"] = my_position_in_dict
        returned_data["GeodesicHeight"] = my_geodesic_height
        returned_data["MitMassnahme"] = my_mit_massnahme
        returned_data["connectedToRelevantNode"] = my_connected_to_relevant_node
        returned_data["massnahmenOnNode"] = my_massnahmen_on_node
        returned_data["which_DGM_from"] = which_dgm_from

        return returned_data

    def read_auffangbecken(self):
        auffangbecken_frontend = dict()
        auffangbecken_db = Auffangbecken.query.filter_by(region_id=self.region.id).all()
        for auffangbecken in auffangbecken_db:
            points = auffangbecken.position.split(self.delimiter)
            points_of_polygon = []
            for point in points:
                new_point = point.split(",")
                new_point_tuple = (float(new_point[0]), float(new_point[1]))
                points_of_polygon.append(new_point_tuple)
            auffangbecken_frontend[auffangbecken.id] = {
                "position": points_of_polygon,
                "depth": auffangbecken.depth,
                "cost": auffangbecken.cost
            }
        return auffangbecken_frontend

    def read_leitgraeben(self):
        my_leitgraeben_from_database = Leitgraeben.query.filter_by(region_id=self.region.id).all()
        leitgraeben_for_frontend = dict()
        for leitgraben in my_leitgraeben_from_database:
            points_ofleitgraben = leitgraben.position.split(self.delimiter)
            points_of_polygon = []
            for point in points_ofleitgraben:
                new_point = point.split(",")
                new_point_tuple = (float(new_point[0]), float(new_point[1]))
                points_of_polygon.append(new_point_tuple)
            leitgraeben_for_frontend[leitgraben.id] = {
                "position": points_of_polygon,
                "depth": leitgraben.depth,
                "cost": leitgraben.cost,
                "leitgrabenOderBoeschung": leitgraben.leitgrabenOderBoeschung
            }
        return leitgraeben_for_frontend

    @staticmethod
    def read_gebaeudeklasse_to_schadensklasse():
        gebaeudeklasse_to_schadensklasse_as_dict = dict()
        gebaeudeklasse_to_schadensklasse_from_db = GlobalToSchadensklasse.query.all()
        for entry in gebaeudeklasse_to_schadensklasse_from_db:
            gebaeudeklasse_to_schadensklasse_as_dict[entry.gebaeudeklasse] = entry.schadensklasse
        return gebaeudeklasse_to_schadensklasse_as_dict

    @staticmethod
    def read_gebaeudeklasse_to_akteur():
        gebaeudeklasse_to_akteur_from_db = GlobalToAkteur.query.all()
        gebaeudeklasse_to_akteur_as_dict = dict()
        for entry in gebaeudeklasse_to_akteur_from_db:
            gebaeudeklasse_to_akteur_as_dict[entry.gebaeudeklasse] = entry.akteur
        return gebaeudeklasse_to_akteur_as_dict

    def read_optimization_parameters(self, **kwargs):
        diffrent_region = kwargs.get('diffrent_region', None)
        certain_param_id = kwargs.get('certain_param_id', None)
        if diffrent_region:
            if certain_param_id:
                optimization_parameters_from_db = OptimizationParameters.query.filter_by(
                    region=diffrent_region).filter_by(parameterId=certain_param_id).all()
            else:
                optimization_parameters_from_db = OptimizationParameters.query.filter_by(region=diffrent_region).all()
        else:
            if certain_param_id:
                optimization_parameters_from_db = OptimizationParameters.query.filter_by(
                    region=self.region.name).filter_by(parameterId=certain_param_id).all()
            else:
                optimization_parameters_from_db = OptimizationParameters.query.filter_by(region=self.region.name).all()
        optimization_parameters_as_dict = dict()
        for param_db in optimization_parameters_from_db:
            if param_db.parameterId not in optimization_parameters_as_dict.keys():
                optimization_parameters_as_dict[param_db.parameterId] = dict()
            optimization_parameters_as_dict[param_db.parameterId][param_db.parameterName] = param_db.parameterValue
        return optimization_parameters_as_dict

    # --------------------------------------
    # ---------- UPLOADS/KOPIEREN ----------
    # --------------------------------------

    def write_uploaded_einzugsgebiete_to_database(self, path, filename):
        if not self.region:
            # Neue Regionen hochladen
            self.region = Region(name=self.regionname, admin_id=self.user.id)
            self.database.session.add(self.region)
            # Gebe admin Region frei
            self.region.users.append(User_Region(user=User.query.filter_by(username='admin').first()))
            flash(f'Modellgrenzen der Region {self.region.name} hochgeladen!', 'success')
        else:
            flash(f'Modellgrenzen der Region {self.region.name} geupdated!', 'success')
        # User hinzufuegen
        association_exists = User_Region.query.filter_by(user_id=self.user.id).filter_by(
            region_id=self.region.id).first()
        if not association_exists:
            self.region.users.append(User_Region(user=current_user))
            flash(f'Region {self.region.name} wurde für Sie freigegeben!', 'success')
        else:
            flash(f'Region {self.region.name} wurde für Sie bereits freigegeben', 'info')

        identity = 1
        Einzugsgebiete.query.filter_by(region_id=self.region.id).delete()
        with open(os.path.join(path, filename), encoding="utf-8-sig") as file:
            dr = csv.DictReader(file, fieldnames=["col1", "col2"], delimiter=";")
            for i in dr:
                conversed_coordinates = utm.to_latlon(float(i["col1"]), float(i["col2"]), self.utm_zone, 'N')
                einzugsgebiet = Einzugsgebiete(region=self.region.name, region_id=self.region.id, id=identity,
                                               xCoord=conversed_coordinates[1],
                                               yCoord=conversed_coordinates[0])
                self.database.session.add(einzugsgebiet)
                identity += 1
        self.database.session.commit()

    def initialize_optimization_parameters(self, param_id):
        self.check_rights()
        OptimizationParameters.query.filter_by(region_id=self.region.id).delete()
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
        optimization_parameter_array = []
        for key, value in parameters.items():
            new_optim_param = OptimizationParameters(region=self.region.name, region_id=self.region.id,
                                                     parameterId=param_id, parameterName=key,
                                                     parameterValue=value)
            optimization_parameter_array.append(new_optim_param)
        self.database.session.add_all(optimization_parameter_array)
        self.database.session.commit()
        flash(f'DGM der Region {self.region.name} hochgeladen!', 'success')

    def write_uploaded_data_to_dgm1(self, path, filename):  # , reuse
        self.check_rights()
        if not self.region:
            flash(
                f'Region "{self.regionname}" existiert nicht! '
                f'Bitte überprüfen sie den Namen oder laden sie die Modellgrenzen hoch',
                'info')
            return redirect(request.url)
        Header.query.filter_by(region_id=self.region.id).delete()
        DGM1.query.filter_by(region_id=self.region.id).delete()
        DGM5.query.filter_by(region_id=self.region.id).delete()
        DGM25.query.filter_by(region_id=self.region.id).delete()
        db_object_array = []
        # in database, we want the geodesic height in mm. Adjust the scaling factor as desired (10 for cm, 1000 for m)
        if self.customer == "Wismar" or self.customer == "KMB" or self.customer == "Ersfeld":
            scaling = 1000
        else:
            scaling = 10
        einzugsgebiete_data = self.read_einzugsgebiete_for_display()
        einzugsgebiete_polygon = Polygon(einzugsgebiete_data["Einzugsgebiete"])
        print(f'Polygon.centroid.x: {einzugsgebiete_polygon.centroid.x}')
        # add Header
        header = Header(region=self.region.name, region_id=self.region.id, uploaded=1,
                        date_uploaded=datetime.datetime.now(), solved=0,
                        data_solved='not solved', timeHorizon=0, gridSize=1, rainAmount=126.5, rainDuration=60,
                        center_lat=einzugsgebiete_polygon.centroid.x, center_lon=einzugsgebiete_polygon.centroid.y)
        db_object_array.append(header)
        # add DGM
        with open(os.path.join(path, filename), encoding="utf-8-sig") as file:
            fieldnames = ["Rowid", "DPFILL10", "X", "Y", "DPFILL10_1"]
            delimiter = ";"
            if self.customer == "Wismar":
                delimiter = ";"
                # fieldnames = ["d1", "d2", "X", "d3", "Y", "d4", "d5", "d6", "d7", "d8", "d9", "DPFILL10_1"]
                fieldnames = ["X", "Y", "DPFILL10_1"]
            if self.customer == "KMB" or self.customer == "Ersfeld" or self.customer == "Puderbach":
                delimiter = ";"
                fieldnames = ["X", "Y", "DPFILL10_1"]
            dr = csv.DictReader(file, fieldnames=fieldnames, delimiter=delimiter)
            if self.customer != "Wismar":
                next(dr, None)  # Skip header line
            remember_keys_to_avoid_dupicates = set()
            for identification, grid in enumerate(dr):
                # print(grid["X"], " - ", grid["Y"])
                xutm = int(float(grid["X"].replace(",", ".")))
                yutm = int(float(grid["Y"].replace(",", ".")))
                if (xutm, yutm) not in remember_keys_to_avoid_dupicates:
                    remember_keys_to_avoid_dupicates.add((xutm, yutm))
                    xutm25 = self.myround(xutm, 25)
                    yutm25 = self.myround(yutm, 25)
                    conversed_coordinates = utm.to_latlon(xutm, yutm, self.utm_zone, 'N')
                    position, new_polygon_array = self.compute_grid_polygon((xutm, yutm), 1)
                    position25, new_polygon_array25 = self.compute_grid_polygon((xutm25, yutm25), 25)
                    # new_kataster_polygon = Polygon(new_polygon_array)
                    new_kataster_polygon25 = Polygon(new_polygon_array25)
                    if new_kataster_polygon25.intersects(einzugsgebiete_polygon):  # Kommt ned rein
                        dgm1 = DGM1(region=self.region.name, region_id=self.region.id, id=identification, xutm=xutm,
                                    yutm=yutm,
                                    geodesicHeight=int(float(grid["DPFILL10_1"]) * scaling), inEinzugsgebiete=1,
                                    xCoord=conversed_coordinates[0],
                                    yCoord=conversed_coordinates[1], gridPolyline=position, mitMassnahme="notComputed",
                                    relevantForGraph=0, connectedToRelevantNodes=0,
                                    resolveFurther=0, willBeInGraph=0)
                        db_object_array.append(dgm1)
                        if xutm % 5 == 0 and yutm % 5 == 0:
                            position5, new_polygon_array5 = self.compute_grid_polygon((xutm, yutm), 5)
                            dgm5 = DGM5(region=self.region.name, region_id=self.region.id, id=identification, xutm=xutm,
                                        yutm=yutm,
                                        geodesicHeight=int(float(grid["DPFILL10_1"]) * scaling), inEinzugsgebiete=1,
                                        xCoord=conversed_coordinates[0],
                                        yCoord=conversed_coordinates[1], gridPolyline=position5,
                                        mitMassnahme="notComputed", relevantForGraph=0, connectedToRelevantNodes=0,
                                        resolveFurther=0, willBeInGraph=0)
                            db_object_array.append(dgm5)
                        if xutm % 25 == 0 and yutm % 25 == 0:
                            dgm25 = DGM25(region=self.region.name, region_id=self.region.id, id=identification,
                                          xutm=xutm, yutm=yutm,
                                          geodesicHeight=int(float(grid["DPFILL10_1"]) * scaling), inEinzugsgebiete=1,
                                          xCoord=conversed_coordinates[0],
                                          yCoord=conversed_coordinates[1], gridPolyline=position25,
                                          mitMassnahme="notComputed", relevantForGraph=0, connectedToRelevantNodes=0,
                                          resolveFurther=0, willBeInGraph=1)
                            db_object_array.append(dgm25)
        self.database.session.add_all(db_object_array)
        self.database.session.commit()
        self.initialize_optimization_parameters("init")

    def write_uploaded_kataster_as_xml_to_database(self, path, filename):
        self.check_rights()

        def get_new_points(array):
            returned_aray = []
            while array:
                x_utm = float(array.pop(0))
                y_utm = float(array.pop(0))
                returned_aray.append((x_utm, y_utm))
            return returned_aray

        def get_buildings_in_einzugesgebiet(filename_inner, identification):
            root = Et.parse(os.path.join(path, filename_inner)).getroot()
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
                        conversed_coordinates = utm.to_latlon(point[0], point[1], self.utm_zone_kataster, 'N')
                        pos_array_latlon.append(conversed_coordinates)
                    building_polygon = Polygon(pos_array_latlon)
                    if building_polygon.intersects(einzugsgebiete_polygon):
                        identification += 1
                        buildings_in_dict[identification] = {"position": pos_array_latlon,
                                                             "gebaeudeklasse": gebaeudeklasse.text}
            return identification

        def get_kataster_in_einzugsgebiet(filename_inner, identification):
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
            root = Et.parse(os.path.join(path, filename_inner)).getroot()
            if self.customer == "Alzey" or self.customer == "KMB":
                geaenderte_objekte = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}geaenderteObjekte')
                iterator = geaenderte_objekte.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}Transaction')
            else:
                enthaelt = root.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}enthaelt')
                feature_collection = enthaelt.find('{http://www.adv-online.de/namespaces/adv/gid/wfs}FeatureCollection')
                iterator = feature_collection.findall('{http://www.opengis.net/gml/3.2}featureMember')

            for child in iterator:
                kat = None
                for ax_code, akteur_mapping in kataster_akteur_mapping.items():
                    if not kat:
                        kat = child.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}' + ax_code)
                        if kat:
                            # remember_ax_code = ax_code
                            remember_akteur = akteur_mapping
                if kat:
                    position_of_kataster = kat.find('{http://www.adv-online.de/namespaces/adv/gid/6.0}position')
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
                        conversed_coordinates = utm.to_latlon(point[0], point[1], self.utm_zone_kataster, 'N')
                        pos_array_latlon.append(conversed_coordinates)
                    kataster_polygon = Polygon(pos_array_latlon)
                    if kataster_polygon.intersects(einzugsgebiete_polygon):
                        identification += 1
                        kataster_in_dict[identification] = {"position": pos_array_latlon,
                                                            "akteur": remember_akteur}
            return identification

        if not self.region:
            flash(
                f'Region "{self.regionname}" existiert nicht! '
                f'Bitte überprüfen sie den Namen oder laden sie die Modellgrenzen hoch',
                'info')
            return redirect(request.url)
        self.check_rights()
        for data_building in self.region.databuildings:
            self.database.session.delete(data_building)
        db_objects = []
        einzugsgebiete_data = self.read_einzugsgebiete_for_display()
        einzugsgebiete_polygon = Polygon(einzugsgebiete_data["Einzugsgebiete"])
        # max_id_buildings, max_id_kataster = extract_indices()
        max_id_buildings, max_id_kataster = 0, 0
        buildings_id = 0
        kataster_id = 0
        buildings_in_dict = dict()
        kataster_in_dict = dict()
        if filename.rsplit('.', 1)[1].lower() == "xml":
            buildings_id = get_buildings_in_einzugesgebiet(filename, buildings_id)
            kataster_id = get_kataster_in_einzugsgebiet(filename, kataster_id)
        elif filename.rsplit('.', 1)[1].lower() == "zip":
            with zipfile.ZipFile(os.path.join(path, filename), "r") as f:
                f.extractall(path)
                for fn in f.namelist():
                    if fn.find(".") >= 0 and fn.rsplit('.', 1)[1].lower() == "xml" and fn[0:1] != "_":
                        buildings_id = get_buildings_in_einzugesgebiet(fn, buildings_id)
                        kataster_id = get_kataster_in_einzugsgebiet(fn, kataster_id)

        print(f"len of kataster in dict: {len(kataster_in_dict)}")
        print(kataster_in_dict)
        gebaeudeklasse_to_schadensklasse_as_dict = self.read_gebaeudeklasse_to_schadensklasse()
        gebaeudeklasse_to_akteur_as_dict = self.read_gebaeudeklasse_to_akteur()
        # DataBuildings
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
            data_building = DataBuildings(region=self.region.name, region_id=self.region.id, id=max_id_buildings,
                                          position=self.polygon_to_database_format(buildings_in_dict[key]["position"]),
                                          properties=json.dumps({}), active=1,
                                          gebaeudeklasse=buildings_in_dict[key]["gebaeudeklasse"],
                                          schadensklasse=schadensklasse, akteur=akteur)
            db_objects.append(data_building)
        # Kataster
        Kataster.query.filter_by(region=self.region.name).delete()
        for key, value in kataster_in_dict.items():
            max_id_kataster = max_id_kataster + 1
            Kataster.query.filter_by(region=self.region.name).delete()
            kataster = Kataster(region=self.region.name, region_id=self.region.id, id=max_id_kataster,
                                position=self.polygon_to_database_format(kataster_in_dict[key]["position"]),
                                inEinzugsgebiete=1, additionalCost=0, akteur=kataster_in_dict[key]["akteur"])
            db_objects.append(kataster)
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    def write_uploaded_kataster_as_shp_to_database(self, path, filename):
        if not self.region:
            flash(
                f'Region "{self.regionname}" existiert nicht! '
                f'Bitte überprüfen sie den Namen oder laden sie die Modellgrenzen hoch',
                'info')
            return redirect(request.url)
        self.check_rights()
        for data_building in self.region.databuildings:
            self.database.session.delete(data_building)
        db_objects = []
        einzugsgebiete_data = self.read_einzugsgebiete_for_display()
        einzugsgebiete_polygon = Polygon(einzugsgebiete_data["Einzugsgebiete"])
        identification = 1
        gebaeudeklasse_to_akteur_as_dict = self.read_gebaeudeklasse_to_akteur()
        gebaeudeklasse_to_schadensklasse_as_dict = self.read_gebaeudeklasse_to_schadensklasse()
        with fiona.open(os.path.join(path, filename)) as src:
            for f in src:
                if 'geometry' in f:
                    if f['geometry']['type'] == 'Polygon':
                        coordinates_in_shp = f['geometry']['coordinates'][0]
                        coordinates_in_shp_as_latlon = [utm.to_latlon(x[0], x[1], self.utm_zone_kataster, 'N') for x in
                                                        coordinates_in_shp]
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
                        if gebaeude_as_polygon.intersects(einzugsgebiete_polygon):
                            data_building = DataBuildings(region=self.region.name, region_id=self.region.id,
                                                          id=identification,
                                                          position=self.polygon_to_database_format(
                                                              coordinates_in_shp_as_latlon), properties=json.dumps({}),
                                                          active=1, gebaeudeklasse=gebaeudeklasse,
                                                          schadensklasse=schadensklasse, akteur=akteur)
                            identification += 1
                            db_objects.append(data_building)
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    def copy_database(self, database, new_region_in_db):
        data_from, data_new = database.query.filter_by(region=self.region.name).all(), []
        for data in data_from:
            # make it transient, remove the identiy
            make_transient(data)
            data._oid = None
            data_new.append(data)
        for data in data_new:
            data.region = new_region_in_db.name
            data.region_id = new_region_in_db.id
        self.database.session.add_all(data_new)

    def copy_region_to(self, new_region_name):
        if not self.region:  # Region_from
            flash(f'Region {self.regionname} existiert nicht!', 'warning')
            return redirect(request.url)
        self.check_rights()
        new_region_in_db = Region.query.filter_by(name=new_region_name).first()
        if new_region_in_db is None:
            new_region_in_db = Region(name=new_region_name, admin_id=current_user.id)
            self.database.session.add(new_region_in_db)
        associations = User_Region.query.filter_by(region_id=self.region.id).all()
        for ass in associations:
            self.database.session.add(User_Region(region_id=new_region_in_db.id, user_id=ass.user_id))

        for db in [Auffangbecken, DGM1, DGM5, DGM25, DataBuildings, Einzugsgebiete, Header, Kataster, Leitgraeben,
                   OptimizationParameters, Solutions, MassnahmenKatasterMapping]:
            print(f"Copying Database {db}")
            db.query.filter_by(region=new_region_in_db.name).delete()
            self.copy_database(db, new_region_in_db)
        self.database.session.commit()

    # -----------------------------------
    # ---------- EINGANGSDATEN ----------
    # -----------------------------------

    def update_header_data_from_frontend(self, data):
        for region in data:
            self.region = Region.query.filter_by(name=region).first()
            self.check_rights()
            header = Header.query.filter_by(region=region).first()
            header.rainAmount, header.rainDuration = data[region]["amount"], data[region]["duration"]
        self.database.session.commit()

    def update_buildings_from_frontend(self, data):
        self.check_rights()
        db_objects = []
        for building in data:
            data_building = DataBuildings(region=self.region.name, region_id=self.region.id, id=int(building),
                                          position=self.polygon_to_database_format(data[building]["position"]),
                                          properties=json.dumps(data[building]["properties"]),
                                          active=int(data[building]["active"]), akteur=data[building]["akteur"],
                                          gebaeudeklasse=int(data[building]["gebaeudeklasse"]),
                                          schadensklasse=int(data[building]["schadensklasse"]))
            db_objects.append(data_building)
        DataBuildings.query.filter_by(region_id=self.region.id).delete()
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    # ----------------------------------
    # ---------- MODELLIERUNG ----------
    # ----------------------------------

    def update_kataster_from_frontend(self, data):
        self.check_rights()
        for kataster in data:
            kataster_db = Kataster.query.filter_by(region=self.region.name).filter_by(id=kataster).first()
            kataster_db.additionalCost = data[kataster]["additionalCost"]
        self.database.session.commit()

    def update_auffangbecken_from_frontend(self, data):
        self.check_rights()
        for auffangbecken in self.region.auffangbecken:
            self.database.session.delete(auffangbecken)
        db_objects = []
        for auffangbecken in data:
            position_string = ""
            for point in data[auffangbecken]["position"]:
                position_string = position_string + str(point[0]) + "," + str(point[1]) + self.delimiter
            position_string = position_string[:-1]
            auffangbecken = Auffangbecken(region=self.region.name, region_id=self.region.id, id=int(auffangbecken),
                                          position=position_string,
                                          depth=data[auffangbecken]["depth"],
                                          cost=data[auffangbecken]["cost"])
            db_objects.append(auffangbecken)
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    def update_leitgraeben_from_frontend(self, data):
        self.check_rights()
        for leitgraeben in self.region.leitgraeben:
            self.database.session.delete(leitgraeben)
        db_objects = []
        for leitgraben in data:
            position_string = ""
            for point in data[leitgraben]["position"]:
                position_string = position_string + str(point[0]) + "," + str(point[1]) + self.delimiter
            position_string = position_string[:-1]
            leitgraben = Leitgraeben(region=self.region.name, region_id=self.region.id, id=int(leitgraben),
                                     position=position_string,
                                     depth=data[leitgraben]["depth"], cost=data[leitgraben]["cost"],
                                     leitgrabenOderBoeschung=data[leitgraben]["leitgrabenOderBoeschung"])
            db_objects.append(leitgraben)
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    def read_all_optimization_parameters(self):
        headers = self.read_user_header_table()
        all_params = dict()
        for header in headers:
            optimization_parameters_for_region = self.read_optimization_parameters(diffrent_region=header)
            all_params[header] = optimization_parameters_for_region
        return all_params

    def update_optimization_parameters_from_frontend(self, returned_data):
        db_objects = []
        for region in returned_data.keys():
            self.region = Region.query.filter_by(name=region).first()
            self.check_rights()
            OptimizationParameters.query.filter_by(region_id=self.region.id).delete()
            for param_id in returned_data[region].keys():
                for param_name in returned_data[region][param_id].keys():
                    opt_param = OptimizationParameters(region=self.region.name, region_id=self.region.id,
                                                       parameterId=param_id,
                                                       parameterName=param_name,
                                                       parameterValue=returned_data[region][param_id][param_name])
                    db_objects.append(opt_param)
        self.database.session.add_all(db_objects)
        self.database.session.commit()

    def update_relevant_from_frontend(self, dataFromFrontend):
        self.check_rights()
        for nodeId in dataFromFrontend["Relevant"]:
            dgm_db = DGM25.query.filter_by(region_id=self.region.id).filter_by(id=nodeId).first()
            dgm_db.relevantForGraph = dataFromFrontend["Relevant"][nodeId]
        self.database.session.commit()

    # ----------------------------------
    # ---------- BERECHNUNGEN ----------
    # ----------------------------------

    def update_mit_massnahme(self):
        def compute_mit_massnahme(gridSize):
            all_buildings = self.read_buildings_for_display()
            all_auffangbecken = self.read_auffangbecken()
            all_leitgraeben = self.read_leitgraeben()
            auffangbecken_as_polygons = {}
            buildings_as_polygons = {}
            leitgraeben_as_polylines = dict()
            affected_grids = dict()
            grid_massnahme_counter = dict()
            for auffangbecken in all_auffangbecken:
                auffangbecken_as_polygons[auffangbecken] = Polygon(all_auffangbecken[auffangbecken]["position"])
                first_point_in_polygon = all_auffangbecken[auffangbecken]["position"][0]
                auffangbecken_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone,
                                                    'N')
                auffangbecken_start_xutm = auffangbecken_utm[0]
                auffangbecken_start_yutm = auffangbecken_utm[1]
                auffangbecken_start_xutm_grid_size = self.myround(auffangbecken_start_xutm, gridSize)
                auffangbecken_start_yutm_grid_size = self.myround(auffangbecken_start_yutm, gridSize)
                grids_queue = [(auffangbecken_start_xutm_grid_size, auffangbecken_start_yutm_grid_size)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(auffangbecken_as_polygons[auffangbecken]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[
                                                                                   actual_grid_to_check] + 1
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
                leitgraben_utm = utm.from_latlon(first_point_in_polyline[0], first_point_in_polyline[1], self.utm_zone,
                                                 'N')
                leitgraben_start_xutm = leitgraben_utm[0]
                leitgraben_start_yutm = leitgraben_utm[1]
                leitgraben_start_xutm_grid_size = self.myround(leitgraben_start_xutm, gridSize)
                leitgraben_start_yutm_grid_size = self.myround(leitgraben_start_yutm, gridSize)
                grids_queue = [(leitgraben_start_xutm_grid_size, leitgraben_start_yutm_grid_size)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(leitgraeben_as_polylines[leitgraben]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[
                                                                                   actual_grid_to_check] + 1
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
            for building in all_buildings:
                buildings_as_polygons[building] = Polygon(all_buildings[building]["position"])
                first_point_in_polygon = all_buildings[building]["position"][0]
                building_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone, 'N')
                building_start_xutm = building_utm[0]
                building_start_yutm = building_utm[1]
                building_start_xutm_grid_size = self.myround(building_start_xutm, gridSize)
                building_start_yutm_grid_size = self.myround(building_start_yutm, gridSize)
                grids_queue = [(building_start_xutm_grid_size, building_start_yutm_grid_size)]
                checked_grids = dict()
                while grids_queue:
                    actual_grid_to_check = grids_queue.pop()
                    if actual_grid_to_check not in checked_grids.keys():
                        checked_grids[actual_grid_to_check] = 1
                        actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, gridSize)
                        if Polygon(actual_grid_poly).intersects(buildings_as_polygons[building]):
                            if actual_grid_to_check in affected_grids:
                                grid_massnahme_counter[actual_grid_to_check] = grid_massnahme_counter[
                                                                                   actual_grid_to_check] + 1
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
            affected_grids_grid_size = compute_mit_massnahme(gridSize)
            to_db_grid_size = dict()
            for utm_coordinates in affected_grids_grid_size:
                to_db_grid_size[utm_coordinates] = (
                    "yes", 1, json.dumps(affected_grids_grid_size[utm_coordinates]), self.region.name,
                    utm_coordinates[0],
                    utm_coordinates[1])
            return to_db_grid_size

        def compute_additional_to_db_for_5_and_1_dgm(to_db_DGM_25, to_db_dict_5, to_db_dict_1):
            # otherwise, only 5m and 1m grids with Massnahme will be displayed
            for dgm_25_key in to_db_DGM_25:
                xutm_25 = to_db_DGM_25[dgm_25_key][4]
                yutm_25 = to_db_DGM_25[dgm_25_key][5]
                for i in range(5):
                    xutm_5 = xutm_25 + i * 5 - 10
                    for j in range(5):
                        yutm_5 = yutm_25 + j * 5 - 10
                        if (xutm_5, yutm_5) not in to_db_dict_5.keys():  # no Massnahme on 5DGM grid
                            to_db_dict_5[(xutm_5, yutm_5)] = ("no", 1, "", self.region.name, xutm_5, yutm_5)
                        else:  # Massnahme on 5DGM grid -> need to be finer
                            for i1 in range(5):
                                xutm_1 = xutm_5 + i1 - 2
                                for j1 in range(5):
                                    yutm_1 = yutm_5 + j1 - 2
                                    if (xutm_1, yutm_1) not in to_db_dict_1.keys():
                                        to_db_dict_1[(xutm_1, yutm_1)] = ("no", 1, "", self.region.name, xutm_1, yutm_1)
            return to_db_dict_1, to_db_dict_5

        self.check_rights()
        to_db25_as_dict = compute_to_db(25)
        to_db5_as_dict = compute_to_db(5)
        to_db1_as_dict = compute_to_db(1)

        completed_dict_1, completed_dict_5 = compute_additional_to_db_for_5_and_1_dgm(to_db25_as_dict, to_db5_as_dict,
                                                                                      to_db1_as_dict)

        print("Start updating database at " + str(datetime.datetime.now()))
        for db in [DGM1, DGM5, DGM25]:
            dgm = db.query.filter_by(region=self.region.name).all()
            for d in dgm:
                d.mitMasnahme = 'no'
                d.relevantForGraph = 0
                d.connectedToRelevantNodes = 0
                d.massnahmeOnNode = ''
                d.resolveFurther = 0
                if db == DGM25:
                    d.willBeInGraph = 1
                else:
                    d.willBeInGraph = 0

        for db, dictionary in zip([DGM1, DGM5, DGM25], [completed_dict_1, completed_dict_5, to_db25_as_dict]):
            for key, value in dictionary.items():
                db_object = db.query.filter_by(region=value[3]).filter_by(xutm=key[0]).filter_by(yutm=key[1]).first()
                if db_object:
                    db_object.mitMassnahme = value[0]
                    db_object.relevantForGraph = value[1]
                    db_object.massnahmenOnNode = value[2]
        self.database.session.commit()
        print("End updating database at " + str(datetime.datetime.now()))

    def update_relevant_readjust_grid_size_at_buildings(self, nodes_with_buildings_25, nodes_with_massnahmen_25,
                                                        remember_buildings_25, water_height_in_25):
        self.check_rights()
        grid_data = self.read_grid_for_display()
        header_data = self.read_region_header()
        all_auffangbecken = self.read_auffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        all_buildings = self.read_buildings_for_display()
        grid_instance_graph = instanceGraph(self.region.name, grid_data["Position"], grid_data["Relevant"],
                                            grid_data["GeodesicHeight"], grid_data["massnahmenOnNode"],
                                            header_data["gridSize"],
                                            all_auffangbecken, all_leitgraeben, all_buildings,
                                            header_data["rainAmount"],
                                            header_data["rainDuration"],
                                            grid_data["which_DGM_from"])

        flooding_times, water_amounts, mod_graph, mod_area, flooded_nodes, water_height = \
            grid_instance_graph.computeInitialSolution(None)

        threshold_when_to_resolve_further = 0.01

        nodes_to_check = nodes_with_buildings_25 - nodes_with_massnahmen_25

        affected_grids_5 = dict()
        affected_grids_25 = dict()

        for n25 in nodes_to_check:
            node_flooded = False
            remember_5m_nodes = set()
            for i in range(5):
                n5x = n25[0] - 10 + i * 5
                for j in range(5):
                    n5y = n25[1] - 10 + j * 5
                    remember_5m_nodes.add((n5x, n5y))
                    if (n5x, n5y) in flooded_nodes:
                        actual_grid_pos, actual_grid_poly = self.compute_grid_polygon((n5x, n5y), 5)
                        for b in remember_buildings_25[n25]:
                            if Polygon(actual_grid_poly).intersects(Polygon(all_buildings[b]["position"])):
                                if (n5x, n5y) in water_height.keys():
                                    if water_height[(n5x, n5y)] >= threshold_when_to_resolve_further:
                                        node_flooded = True

            if n25 in water_height_in_25.keys():
                if water_height_in_25[n25] > 0:
                    node_flooded = True

            if not node_flooded:
                for n5 in remember_5m_nodes:
                    affected_grids_5[n5] = (0, 0, n5[0], n5[1])
                affected_grids_25[n25] = (1, 1, 0, 1, n25[0], n25[1])

        to_db = self.dict_to_array(affected_grids_25)
        to_db_5 = self.dict_to_array(affected_grids_5)
        for entry in to_db:
            dgm25 = DGM25.query.filter_by(region=self.region.name).filter_by(xutm=entry[4]).filter_by(
                yutm=entry[5]).first()
            if dgm25:
                dgm25.relevantForGraph, dgm25.connectedToRelevantNodes, dgm25.resolveFurther, dgm25.willBeInGraph = \
                    entry[0], entry[1], entry[2], entry[3]
        for entry in to_db_5:
            dgm5 = DGM25.query.filter_by(region=self.region.name).filter_by(xutm=entry[2]).filter_by(
                yutm=entry[3]).first()
            if dgm5:
                dgm5.resolveFurther, dgm5.willBeInGraph = entry[0], entry[1]
        self.database.session.commit()
        print("Successfully updated relevant and connected nodes reiterate over buildings")

    def update_relevant(self):
        def read_dgm25():
            array_of_25_dgm = DGM25.query.filter_by(region=self.region.name).all()
            my_grid_in_dict = dict()
            my_relevant_in_dict = dict()
            my_position_in_dict = dict()
            my_geodesic_height = dict()
            my_mit_massnahme = dict()
            my_connected_to_relevant_node = dict()
            my_massnahmen_on_node = dict()
            returned_data = dict()
            for grid in array_of_25_dgm:
                points_of_actual_grid = grid.gridPolyline.split(self.delimiter)
                points_of_polygon = []
                for point in points_of_actual_grid:
                    new_point = point.split(",")
                    new_point_tuple = (float(new_point[0]), float(new_point[1]))
                    points_of_polygon.append(new_point_tuple)
                my_grid_in_dict[grid.id] = points_of_polygon
                my_relevant_in_dict[grid.id] = grid.relevantForGraph
                my_position_in_dict[grid.id] = (grid.xutm, grid.yutm)
                my_geodesic_height[grid.id] = grid.geodesicHeight
                my_mit_massnahme[grid.id] = grid.mitMassnahme
                my_connected_to_relevant_node[grid.id] = grid.connectedToRelevantNodes
                if len(grid.massnahmeOnNode) > 2:
                    my_massnahmen_on_node[grid.id] = json.loads(grid.massnahmeOnNode)
                else:
                    my_massnahmen_on_node[grid.id] = ""

            returned_data["Relevant"] = my_relevant_in_dict
            returned_data["Grid"] = my_grid_in_dict
            returned_data["Position"] = my_position_in_dict
            returned_data["GeodesicHeight"] = my_geodesic_height
            returned_data["MitMassnahme"] = my_mit_massnahme
            returned_data["connectedToRelevantNode"] = my_connected_to_relevant_node
            returned_data["massnahmenOnNode"] = my_massnahmen_on_node

            return returned_data

        self.check_rights()
        grid_data = read_dgm25()
        header_data = self.read_region_header()
        all_auffangbecken = self.read_auffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        grid_instance_graph = instanceGraphForDGM25(self.region.name, grid_data["Position"], grid_data["Relevant"],
                                                    grid_data["GeodesicHeight"], grid_data["massnahmenOnNode"],
                                                    header_data["gridSize"], all_auffangbecken,
                                                    header_data["rainAmount"],
                                                    header_data["rainDuration"])
        print("Computing list of relevant and connected nodes")
        relevant_nodes, connected_nodes = grid_instance_graph.computeListOfRelevantAndConnectedNodes()
        print("Computing initial solution")
        flooding_times, water_amounts, mod_graph, mod_area, water_height_in_25 = \
            grid_instance_graph.computeInitialSolution(None)
        all_buildings = self.read_buildings_for_display()
        # to_db_5 = []
        # to_db_1 = []
        nodes_with_buildings_25 = set()
        nodes_with_massnahmen_25 = set()
        remember_buildings_25 = dict()
        auffangbecken_as_polygons = {}
        buildings_as_polygons = {}
        leitgraeben_as_polylines = dict()

        affected_grids_25 = dict()
        affected_grids_5 = dict()
        affected_grids_1 = dict()

        for building in all_buildings:
            # print(building)
            buildings_as_polygons[building] = Polygon(all_buildings[building]["position"])
            first_point_in_polygon = all_buildings[building]["position"][0]
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
                    actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(buildings_as_polygons[building]):
                        nodes_with_buildings_25.add(actual_grid_to_check)
                        if actual_grid_to_check in remember_buildings_25.keys():
                            remember_buildings_25[actual_grid_to_check].add(building)
                        else:
                            remember_buildings_25[actual_grid_to_check] = {building}
                        # if actual grid to ckeck is not in waterHeight['waterHeight'],
                        # this means that the water height is 0
                        affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (
                            1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                        for i in range(5):
                            actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                            for j in range(5):
                                actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (
                                    0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                        affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (
                            1, 1, 0, 1, actual_grid_to_check[0], actual_grid_to_check[1])

                        grids_queue.append((actual_grid_to_check[0] + 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0] - 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + 25))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - 25))

        for node in connected_nodes:
            if node in relevant_nodes:
                if node in nodes_with_buildings_25:
                    affected_grids_25[(node[0], node[1])] = (1, 1, 1, 0, node[0], node[1])
                else:
                    affected_grids_25[(node[0], node[1])] = (1, 1, 0, 1, node[0], node[1])
            else:
                affected_grids_25[(node[0], node[1])] = (0, 1, 0, 1, node[0], node[1])

        for auffangbecken in all_auffangbecken:
            auffangbecken_as_polygons[auffangbecken] = Polygon(all_auffangbecken[auffangbecken]["position"])
            first_point_in_polygon = all_auffangbecken[auffangbecken]["position"][0]
            auffangbecken_utm = utm.from_latlon(first_point_in_polygon[0], first_point_in_polygon[1], self.utm_zone,
                                                'N')
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
                    actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(auffangbecken_as_polygons[auffangbecken]):
                        nodes_with_massnahmen_25.add(actual_grid_to_check)
                        print(f"Affected-Grid: {affected_grids_25}")  # connected_nodes
                        print(f"Check: {actual_grid_to_check}")
                        if affected_grids_25[actual_grid_to_check][2] == 0:
                            affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (
                                1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                            for i in range(5):
                                actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                                for j in range(5):
                                    actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (
                                        0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
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
                    actual_grid_pos, actual_grid_poly = self.compute_grid_polygon(actual_grid_to_check, 25)
                    if Polygon(actual_grid_poly).intersects(leitgraeben_as_polylines[leitgraben]):
                        nodes_with_massnahmen_25.add(actual_grid_to_check)
                        affected_grids_25[(actual_grid_to_check[0], actual_grid_to_check[1])] = (
                            1, 1, 1, 0, actual_grid_to_check[0], actual_grid_to_check[1])
                        for i in range(5):
                            actual_grid_to_check_x_5 = actual_grid_to_check[0] - 10 + i * 5
                            for j in range(5):
                                actual_grid_to_check_y_5 = actual_grid_to_check[1] - 10 + j * 5
                                actual_grid_pos_5, actual_grid_poly_5 = self.compute_grid_polygon(
                                    (actual_grid_to_check_x_5, actual_grid_to_check_y_5), 5)
                                if Polygon(actual_grid_poly_5).intersects(leitgraeben_as_polylines[leitgraben]):
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (
                                        1, 0, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                                    for i1 in range(5):
                                        actual_grid_to_check_x_1 = actual_grid_to_check_x_5 - 2 + i1
                                        for j1 in range(5):
                                            actual_grid_to_check_y_1 = actual_grid_to_check_y_5 - 2 + j1
                                            affected_grids_1[(actual_grid_to_check_x_1, actual_grid_to_check_y_1)] = (
                                                0, 1, actual_grid_to_check_x_1, actual_grid_to_check_y_1)
                                else:
                                    affected_grids_5[(actual_grid_to_check_x_5, actual_grid_to_check_y_5)] = (
                                        0, 1, actual_grid_to_check_x_5, actual_grid_to_check_y_5)
                        grids_queue.append((actual_grid_to_check[0] + 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0] - 25, actual_grid_to_check[1]))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] + 25))
                        grids_queue.append((actual_grid_to_check[0], actual_grid_to_check[1] - 25))

        to_db = self.dict_to_array(affected_grids_25)
        to_db_5 = self.dict_to_array(affected_grids_5)
        to_db_1 = self.dict_to_array(affected_grids_1)

        for i, (db, array) in enumerate(zip([DGM1, DGM5, DGM25], [to_db_1, to_db_5, to_db])):
            if db == DGM25:
                entry_25 = DGM25.query.filter_by(region=self.region.name, xutm=array[i][4], yutm=array[i][5]).first()
                if entry:
                    entry_25.relevantForGraph, entry_25.connectedToRelevantNodes, entry_25.resolveFurther, \
                        entry_25.willBeInGraph = array[i][0], array[i][1], array[i][2], array[i][3]
            else:
                entry = db.query.filter_by(region=self.region.name, xutm=array[i][2], yutm=array[i][3]).first()
                if entry:
                    entry.resolveFurther, entry.willBeInGraph = array[i][0], array[i][1]

        print("Successfully updated relevant and connected nodes sizing all buildings at 5m grid size")

        self.update_relevant_readjust_grid_size_at_buildings(nodes_with_buildings_25, nodes_with_massnahmen_25,
                                                             remember_buildings_25, water_height_in_25)

    def compute_massnahmen_kataster(self):
        self.check_rights()
        all_kataster = self.read_kataster_for_display()
        all_kataster = all_kataster["Kataster"]
        all_auffangbecken = self.read_auffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        print("Start computing massnahmen kataster", datetime.datetime.now())
        MassnahmenKatasterMapping.query.filter_by(region=self.region.name).delete()
        for kataster in all_kataster:
            einzugsgebiete_polygon = Polygon(all_kataster[kataster]["position"])
            for auffangbecken in all_auffangbecken:
                auffangbecken_polygon = Polygon(all_auffangbecken[auffangbecken]["position"])
                if auffangbecken_polygon.intersects(einzugsgebiete_polygon):
                    massnahme_kataster_mapping = MassnahmenKatasterMapping(region=self.region.name,
                                                                           region_id=self.region.id,
                                                                           artMassnahme="Auffangbecken",
                                                                           massnahmeId=auffangbecken,
                                                                           katasterId=kataster)
                    self.database.session.add(massnahme_kataster_mapping)
            for leitgraben in all_leitgraeben:
                leitgraben_polygon = LineString(all_leitgraeben[leitgraben]["position"])
                if leitgraben_polygon.intersects(einzugsgebiete_polygon):
                    massnahme_kataster_mapping = MassnahmenKatasterMapping(region=self.region.name,
                                                                           region_id=self.region.id,
                                                                           artMassnahme="Leitgraben",
                                                                           massnahmeId=leitgraben,
                                                                           katasterId=kataster)
                    self.database.session.add(massnahme_kataster_mapping)
        print("End computing massnahmen kataster", datetime.datetime.now())
        self.database.session.commit()

    def read_massnahmen_kataster(self):
        data_from = MassnahmenKatasterMapping.query.filter_by(region=self.region.name).all()
        returned_array = []
        for data in data_from:
            returned_array.append(self.dict_to_array(self.db_object_to_dict(data)))
        return returned_array

    def compute_optimal_solution(self):
        def read_gefahrenklasse_threshold():
            thresh_for_gefahr = GlobalForGefahrensklasse.query.all()
            threshold_for_gefahrenklasse_as_dict = dict()
            for threshhold in thresh_for_gefahr:
                threshold_for_gefahrenklasse_as_dict[threshhold.gefahrenklasse] = threshhold.threshhold
            threshold_for_gefahrenklasse_as_dict[0] = 0.001
            return threshold_for_gefahrenklasse_as_dict

        self.check_rights()
        grid_data = self.read_grid_for_display()
        header_data = self.read_region_header()
        all_auffangbecken = self.read_auffangbecken()
        all_leitgraeben = self.read_leitgraeben()
        all_buildings = self.read_buildings_for_display()
        optimization_parameters = self.read_optimization_parameters(certain_param_id="init")
        optimization_parameters = optimization_parameters[list(optimization_parameters.keys())[0]]
        grid_instance_graph = instanceGraph(self.region.name, grid_data["Position"], grid_data["Relevant"],
                                            grid_data["GeodesicHeight"], grid_data["massnahmenOnNode"],
                                            header_data["gridSize"], all_auffangbecken, all_leitgraeben,
                                            all_buildings, header_data["rainAmount"],
                                            header_data["rainDuration"],
                                            grid_data["which_DGM_from"])

        threshold_for_gefahrenklasse = read_gefahrenklasse_threshold()
        initialinitial_solutionolution = None
        graph_for_ip = grid_instance_graph.computeInstanceGraph()
        massnahmen_kataster = self.read_massnahmen_kataster()
        all_kataster = self.read_kataster_for_display()
        all_kataster = all_kataster["Kataster"]
        flooded_nodes, water_height, auffangbecken_solution, leitgraeben_solution, flow_through_nodes_for_db, \
            handlungsbedarf = grid_instance_graph.callIPWithEquilibriumWaterLevels(
                graph_for_ip, initialinitial_solutionolution, optimization_parameters, threshold_for_gefahrenklasse,
                massnahmen_kataster, all_kataster)

        to_db = []
        for timeStep in flooded_nodes:
            for identity in flooded_nodes[timeStep]:
                to_db.append((self.region.name, "flooded", timeStep, identity, grid_data["Position"][identity][0],
                              grid_data["Position"][identity][1], flooded_nodes[timeStep][identity]))
        for timeStep in water_height:
            for identity in water_height[timeStep]:
                to_db.append((self.region.name, "waterHeight", timeStep, identity, grid_data["Position"][identity][0],
                              grid_data["Position"][identity][1], water_height[timeStep][identity]))
        for a in auffangbecken_solution:
            to_db.append((self.region.name, "auffangbecken", 1, a, None, None, round(auffangbecken_solution[a])))
        for leitgraeben in leitgraeben_solution:
            to_db.append(
                (self.region.name, "leitgraben", 1, leitgraeben, None, None, round(leitgraeben_solution[leitgraeben])))
        for identity in flow_through_nodes_for_db:
            to_db.append((self.region.name, "flow_through_nodes", 1, identity, grid_data["Position"][identity][0],
                          grid_data["Position"][identity][1], flow_through_nodes_for_db[identity]))
        for b in handlungsbedarf:
            to_db.append((self.region.name, "handlungsbedarf", 1, b, None, None, handlungsbedarf[b]))

        Solutions.query.filter_by(region=self.region.name).delete()
        header = Header.query.filter_by(region=self.region.name).first()
        header.solved, header.data_solved = 1, str((datetime.datetime.now()))
        for entry in to_db:
            solution = Solutions(region=entry[0], variableName=entry[1], timeStep=entry[2], id=entry[3],
                                 nodeXCoord=entry[3], nodeYCoord=entry[4], variableValue=entry[5])
            self.database.session.add(solution)
        self.database.session.commit()

    # -------------------------------
    # ---------- LOESUNGEN ----------
    # -------------------------------

    def read_optimal_solution(self):
        solution_as_dict = dict()
        flooded_nodes_with_time_steps = dict()
        auffangbecken_in_solution = dict()
        leitgraeben_in_solution = dict()
        water_height = dict()
        flow_through_nodes = dict()
        handlungsbedarf = dict()
        my_solution_from_database = self.region.solutions
        for solution in my_solution_from_database:
            if solution.variableName == "flooded":
                if solution.timeStep not in flooded_nodes_with_time_steps:
                    flooded_nodes_with_time_steps[solution.timeStep] = dict()
                flooded_nodes_with_time_steps[solution.timeStep][solution.id] = int(solution.variableVale)
            if solution.variableName == "auffangbecken":
                auffangbecken_in_solution[solution.id] = int(solution.variableVale)
            if solution.variableName == "leitgraben":
                leitgraeben_in_solution[solution.id] = int(solution.variableVale)
            if solution.variableName == "waterHeight":
                water_height[solution.id] = float(solution.variableVale)
            if solution.variableName == "flow_through_nodes":
                flow_through_nodes[solution.id] = float(solution.variableVale)
            if solution.variableName == "handlungsbedarf":
                handlungsbedarf[solution.id] = float(solution.variableVale)
        last_timestep = max(flooded_nodes_with_time_steps.keys())
        solution_as_dict["Flooded"] = flooded_nodes_with_time_steps[last_timestep]
        solution_as_dict["auffangbecken"] = auffangbecken_in_solution
        solution_as_dict["leitgraeben"] = leitgraeben_in_solution
        solution_as_dict["waterHeight"] = water_height
        solution_as_dict["flow_through_nodes"] = flow_through_nodes
        solution_as_dict["handlungsbedarf"] = handlungsbedarf
        return solution_as_dict

    # ------------------------------
    # ---------- LOESCHEN ----------
    # ------------------------------

    def delete_region(self):
        if not self.region:
            flash(f'Region {self.regionname} existiert nicht!', 'warning')
            return redirect(request.url)
        self.check_rights()
        for db in [Header, Data, Solutions, DataBuildings, Kataster, Einzugsgebiete, Auffangbecken, Leitgraeben, DGM1,
                   DGM5, DGM25, OptimizationParameters, MassnahmenKatasterMapping, ]:
            db.query.filter_by(region=self.region.name).delete()
        User_Region.query.filter_by(region_id=self.region.id).delete()
        Region.query.filter_by(name=self.regionname).delete()
        self.database.session.commit()
