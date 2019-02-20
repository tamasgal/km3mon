from os.path import join
from flask import render_template, send_from_directory
from app import app

PLOTS_PATH = "../plots"
app.config['FREEZER_DESTINATION'] = '../km3web'

PLOTS = [['dom_activity', 'dom_rates'], ['pmt_rates', 'pmt_hrv'],
         ['trigger_rates'], ['ztplot', 'triggermap']]

AHRS_PLOTS = [['yaw_calib'], ['pitch_calib'], ['roll_calib']]
TRIGGER_PLOTS = [['trigger_rates'], ['trigger_rates_lin']]
K40_PLOTS = [['intradom'], ['angular_k40rate_distribution']]
RTTC_PLOTS = [['rttc']]


@app.after_request
def add_header(r):
    """
    Disable caches.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


@app.route('/')
@app.route('/index.html')
def index():
    return render_template('plots.html', plots=PLOTS)


@app.route('/ahrs.html')
def ahrs():
    return render_template('plots.html', plots=AHRS_PLOTS)


@app.route('/rttc.html')
def rttc():
    return render_template(
        'plots.html',
        plots=RTTC_PLOTS,
        info=
        "Cable Round Trip Time calculated from realtime data provided by the "
        "Detector Manager. The red lines shows the median and the STD "
        "calculated. from the last 24 hours. "
        "RTTC = Cable_RTT - (TX_Slave + RX_Slave + TX_Master + RX_Master)")


@app.route('/k40.html')
def k40():
    return render_template(
        'plots.html',
        plots=K40_PLOTS,
        info="The first plot shows the intra-DOM calibration. "
        "y-axis: delta_t [ns], x-axis: cosine of angles. "
        "The second plot the angular distribution of K40 rates. "
        "y-axis: rate [Hz], x-axis: cosine of angles. "
        "blue=before, red=after")


@app.route('/trigger.html')
def trigger():
    return render_template('plots.html', plots=TRIGGER_PLOTS)


@app.route('/plots/<path:filename>')
def custom_static(filename):
    print(filename)
    filepath = join(app.root_path, PLOTS_PATH)
    print(filepath)
    return send_from_directory(join(app.root_path, PLOTS_PATH), filename)
