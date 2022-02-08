from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=True, host='0.0.0.0', threaded=False)

"""
DONE/FRAGEN:

TODO
1.) uploads in login.db speichern/verwalten -> siehe databaseHandler > sql-statements zusätzlich sqlalchemy
    (Grenzen, dgm, alkis)
    -> database.db > zusammenfügen -> route-Code in entspr. databasehandler-funktion > Routs entsprechend handler-fkt
    -> connections[direkt db?] vs sessions[init, dann sqldb?] -> conn
2.) Wenn User seit Login Regionen freigegeben bekommen oder Admin bekommen hat hat: Nachricht
> Tabelle Messages in User (Message-ID, User-ID, Inhalt, Art) > deleteUser(self) anpassen!
3.) PW vergessen > Mailserver
4.) Rechte für editieren von Gebäuden -> Check, ob User Rechte an Region hat > Corey > Wenn current user in region.users, sonst F403
z.B. Gebäude
5.) Welche Regionen sieht ein User? Anhängen an bestehende Test-Regionen

SPÄTER
1.) import * spezifizieren, imports verschiedener seiten aufräumen, Formatierung, blueprints, flask-migrate
2.) "Verfügbare xyz öffnen/schließen" einheitlich > button, standardmäßig aufgeklappt (berechnungen lassen)
3.) Bootstrap-Version? > 4.0.0 oder 5
4.) app.run([...], processes) Fehler
5.) Admin-User der Seite kann (admins der) regionen verwalten
"""