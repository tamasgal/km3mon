from os.path import join
from flask import render_template, send_from_directory
from app import app

app.config['PLOTS_PATH'] = "plots"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/plots/<path:filename>')
def custom_static(filename):
    return send_from_directory(join(app.root_path, "../plots"), filename)
