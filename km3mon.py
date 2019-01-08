import sys
from flask_frozen import Freezer
from app import app

freezer = Freezer(app)


@freezer.register_generator
def index():
    yield "/index.html"
    yield "/static/css/bootstrap.min.css"
    yield "/static/css/main.css"
    yield "/static/js/jquery-3.3.1.slim.min.js"
    yield "/static/js/bootstrap.min.js"


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
    else:
        app.run(port=8000)
