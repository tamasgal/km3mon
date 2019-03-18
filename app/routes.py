from os.path import join, exists
from functools import wraps
import toml
from flask import render_template, send_from_directory, request, Response
from app import app

CONFIG_PATH = "pipeline.toml"
PLOTS_PATH = "../plots"
USERNAME = None
PASSWORD = None
app.config['FREEZER_DESTINATION'] = '../km3web'

PLOTS = [['dom_activity', 'dom_rates'], ['pmt_rates', 'pmt_hrv'],
         ['trigger_rates'], ['ztplot', 'triggermap']]

AHRS_PLOTS = [['yaw_calib'], ['pitch_calib'], ['roll_calib']]
TRIGGER_PLOTS = [['trigger_rates'], ['trigger_rates_lin']]
K40_PLOTS = [['intradom'], ['angular_k40rate_distribution']]
RTTC_PLOTS = [['rttc']]
RECO_PLOTS = [['track_reco', 'ztplot_roy'], ['time_residuals']]
COMPACT_PLOTS = [['dom_activity', 'dom_rates', 'pmt_rates', 'pmt_hrv'],
                 ['trigger_rates', 'trigger_rates_lin'],
                 ['ztplot', 'ztplot_roy', 'triggermap']]
SN_PLOTS = [['sn_bg_distribution']]

if exists(CONFIG_PATH):
    config = toml.load(CONFIG_PATH)
    if "WebServer" in config:
        print("Reading authentication information from '%s'" % CONFIG_PATH)
        USERNAME = config["WebServer"]["username"]
        PASSWORD = config["WebServer"]["password"]


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    if USERNAME is not None and PASSWORD is not None:
        return username == USERNAME and password == PASSWORD
    else:
        return True


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


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
@requires_auth
def index():
    return render_template('plots.html', plots=PLOTS)


@app.route('/ahrs.html')
@requires_auth
def ahrs():
    return render_template('plots.html', plots=AHRS_PLOTS)


@app.route('/reco.html')
@requires_auth
def reco():
    return render_template('plots.html', plots=RECO_PLOTS)

@app.route('/sn.html')
@requires_auth
def supernova():
    return render_template('plots.html', plots=SN_PLOTS)

@app.route('/compact.html')
@requires_auth
def compact():
    return render_template('plots.html', plots=COMPACT_PLOTS)


@app.route('/rttc.html')
@requires_auth
def rttc():
    return render_template(
        'plots.html',
        plots=RTTC_PLOTS,
        info=
        "Cable Round Trip Time calculated from realtime data provided by the "
        "Detector Manager. The red lines shows the median and the STD "
        "from the past 24 hours. "
        "RTTC = Cable_RTT - (TX_Slave + RX_Slave + TX_Master + RX_Master)")


@app.route('/k40.html')
@requires_auth
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
@requires_auth
def trigger():
    return render_template('plots.html', plots=TRIGGER_PLOTS)


@app.route('/plots/<path:filename>')
@requires_auth
def custom_static(filename):
    print(filename)
    filepath = join(app.root_path, PLOTS_PATH)
    print(filepath)
    return send_from_directory(join(app.root_path, PLOTS_PATH), filename)
