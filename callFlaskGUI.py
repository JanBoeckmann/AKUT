from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=False, host='0.0.0.0', threaded=False)

"""
FRAGEN:
1.) PW vergessen? > "Wenn email existiert, wurde mail an 'xyz' geschickt statt validierungs-feedback"; Mailserver?
2.) cascade -> SR-Code -> Wenn User oder Region gelöscht: Nur association löschen, nix an Regionen; 2 Arten von deletes?
3.) Association-Model: primary_key bzw. nullable=False

TODO
1.) uploads in login.db speichern/verwalten -> siehe databaseHandler
2.) Filter, wenn user regionen aufruft -> database.db > zusammenfügen -> route-Code in entspr. databasehandler-funktion

SPÄTER
1.) import * spezifizieren, imports verschiedener seiten aufräumen, Formatierung, blueprints
2.) "Verfügbare xyz öffnen/schließen" einheitlich > button, standardmäßig aufgeklappt (berechnungen lassen)
3.) Bootstrap-Version? > 4.0.0 oder 5
4.) flask_migrate
5.) app.run([...], processes)
"""