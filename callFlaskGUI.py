from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=False, host='0.0.0.0', threaded=False)

"""
DONE/FRAGEN:

TODO
1.) uploads in login.db speichern/verwalten -> siehe databaseHandler
2.) Filter, wenn user regionen aufruft -> database.db > zusammenfügen -> route-Code in entspr. databasehandler-funktion

3.) Account (Dropdown Account/Region) -> Über forms?

(Anpassungen in user.regions etc. richtig erfolgt?)
(Einträge, die man nicht mehr rausbekommt?)

Datenschutz
-> Region freigeben -> Muss eh Liste aller user haben, nicht nur die mit der region

Frontend: User-Feld anpassen

provided_by fixen

Neu laden nach löschen nötig
> JS 

Bei admin abgeben/freigeben -> textfeld für email ODER username



SPÄTER
1.) import * spezifizieren, imports verschiedener seiten aufräumen, Formatierung, blueprints
2.) "Verfügbare xyz öffnen/schließen" einheitlich > button, standardmäßig aufgeklappt (berechnungen lassen)
3.) Bootstrap-Version? > 4.0.0 oder 5
4.) flask_migrate
5.) app.run([...], processes)
6.) PW vergessen > Mailserver
7.) Admin-User der Seite kann admins der regionen verwalten
8.) Unterschiedliche User laden unterschiedliche Datenformate hoch
"""