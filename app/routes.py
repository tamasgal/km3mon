from os.path import join
from flask import render_template, send_from_directory
from app import app


PLOTS_PATH = "plots"


PLOTS = [
        ['dom_activity', 'dom_rates'],
        ['pmt_rates', 'pmt_hrv'],
        ['trigger_rates'],
        ]


@app.route('/')
def index():
    return render_template('plots.html', plots=PLOTS)


@app.route('/plots/<path:filename>')
def custom_static(filename):
    return send_from_directory(join(app.root_path, PLOTS_PATH), filename)
