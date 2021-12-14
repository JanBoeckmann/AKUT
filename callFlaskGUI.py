from akut import app, login_db
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=False, host='0.0.0.0', threaded=False)

"""
TODO
- filter, wenn user regionen aufruft -> database.db > zusammenfügen -> rout-Code in entsprechende databasehandler-funktion
- uploads in login.db -> siehe databaseHandler
- models (dgmi, headers...) <- datenbanken; über id

- Association als model
- requirements fehler > egal
- import * spezifizieren > sinnvoll
- PW vergessen? > sinnvoll
- database.db path /// -> hardcoded in database.sqbpro? Aktuell in AKUT statt AKUT/akut > egal
- "Verfügbare xyz öffnen/schließen" einheitlich (z.B. bei blauen)? > button standardmäßig aufgeklappt (berechnungen lassen)
- Bootstrap-Version? > 4.0.0 oder 5
- flask_migrate? > später, sinnvoll
- cascadeOnDelete; association_table als model -> ST-Code
"""