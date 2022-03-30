from akut import app
from akut.models import LoggingMiddleware

if __name__ == "__main__":
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    # app.run(port=4000, debug=True, host='0.0.0.0', threaded=False, processes=10)
    app.run(port=4000, debug=True, host='0.0.0.0', threaded=False)

"""
TODOs:
0.) Refactoring
1.) Berechnungen:
    2: Key-Error instanceGraph
    4: Überprüfen
2.) Lösungen überprüfe
3.) Todo bei ähnlichen Regionennamen
4.) Todo bei Mailserver
5.) Doku
6.) Admin-Panel sortable / filterable
"""