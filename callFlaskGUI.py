from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=False, host='0.0.0.0', threaded=False)

"""
DONE/FRAGEN:
1.) Fehler bei Neuladen nach löschung einer region [Um diese Seite anzuzeigen, müssen die von Firefox gesendeten Daten erneut gesendet werden, wodurch alle zuvor durchgeführten Aktionen wiederholt werden (wie eine Suche oder eine Bestellungsaufgabe).]
2.) Mögliche Probleme bei Löschung eines Users: Wenn Admin einer region, provided by, Nachricht bei Region-Erhalt... -> deleteUser(self)

TODO


SPÄTER
1.) import * spezifizieren, imports verschiedener seiten aufräumen, Formatierung, blueprints, flask-migrate
2.) "Verfügbare xyz öffnen/schließen" einheitlich > button, standardmäßig aufgeklappt (berechnungen lassen)
3.) Bootstrap-Version? > 4.0.0 oder 5
4.) app.run([...], processes) Fehler
5.) PW vergessen > Mailserver
6.) Admin-User der Seite kann (admins der) regionen verwalten
7.) Unterschiedliche User laden unterschiedliche Datenformate hoch
8.) uploads in login.db speichern/verwalten -> siehe databaseHandler 
    -> database.db > zusammenfügen -> route-Code in entspr. databasehandler-funktion
9.) Wenn User seit Login Regionen freigegeben bekommen oder Admin bekommen hat hat: Nachricht
> Tabelle Messages in User (Message-ID, User-ID, Inhalt, Art)

10.) Alte Version:
1. Schadensklasse visualisieren (sättigung/opacity) Bei lokal speichern (sättigung anpassen)
-> ModifyBuildings.html (lila)
-> ModifyBuildingsDraw.js

2. Handlungsbedarf: (1) Wasser & Handlungsbedarf (2) nur handlungsbedarf (wasser weg = opacity auf 0? damits schneller geht) 
    (3) nur Wasserstand (gebäude weiß)
    -> Radio-Button unter Karte (Default = 1)
    -> Legende anpassen 
-> showHandlungsbedarf

3. Alle Module außer gelb:  Beschreibungstext für jedes Modul (Ein-Ausklappbar, default = eingeklappt, erstmal lorem ipsum)
"""