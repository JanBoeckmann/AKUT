from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=True, host='0.0.0.0', threaded=False)

# <- TODO ->
#   regionen nur für nutzer, die hochgeladen haben & filter, wenn user regionen aufrufr // admin-user;
#   exra tabelle user_region (rastergr. 1 hardcoden) in login.db

# <- TODO 2 ->
# - import * spezifizieren?
# - PW vergessen?
# - database.db path /// -> hardcoded in database.sqbpro?
# - "Verfügbare xyz öffnen/schließen" einheitlich (z.B. bei blauen)?
# - Delete (auf landingPage verlint) = DeleteBuildings (ungenutzt) identisch?!
# - Vereinheitlichung Englisch->Deutsch in manchen templates
# - Bootstrap-Version?