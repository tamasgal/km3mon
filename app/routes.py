from glob import glob
from os.path import basename, join, exists, splitext, getsize
from functools import wraps
from collections import OrderedDict
import toml
from flask import render_template, send_from_directory, request, Response
from app import app

from km3modules.common import LocalDBService

CONFIG_PATH = "pipeline.toml"
PLOTS_PATH = "../plots"
LOGS_PATH = "../logs"
USERNAME = None
PASSWORD = None
app.config['FREEZER_DESTINATION'] = '../km3web'

PLOTS = [['dom_activity', 'dom_rates'], 'pmt_rates_du*', ['trigger_rates'],
         ['ztplot', 'triggermap']]

AHRS_PLOTS = ['yaw_calib_du*', 'pitch_calib_du*', 'roll_calib_du*']
TRIGGER_PLOTS = [['trigger_rates'], ['trigger_rates_lin']]
K40_PLOTS = [['intradom'], ['angular_k40rate_distribution']]
RTTC_PLOTS = [['rttc']]
RECO_PLOTS = [['track_reco', 'ztplot_roy'], ['time_residuals']]
COMPACT_PLOTS = [['dom_activity', 'dom_rates', 'pmt_rates'],
                 ['trigger_rates', 'trigger_rates_lin'],
                 ['ztplot', 'ztplot_roy', 'triggermap']]
SN_PLOTS = [['sn_bg_histogram', 'sn_pk_history']]
RASP_PLOTS = [['dom_rates', 'ztplot', 'triggermap'],
              [
                  'pmt_rates_du2', 'pmt_rates_du3', 'pmt_rates_du4',
                  'pmt_rates_du5'
              ], ['trigger_rates', 'trigger_rates_lin']]

if exists(CONFIG_PATH):
    config = toml.load(CONFIG_PATH)
    if "WebServer" in config:
        print("Reading authentication information from '%s'" % CONFIG_PATH)
        USERNAME = config["WebServer"]["username"]
        PASSWORD = config["WebServer"]["password"]


def expand_wildcards(plot_layout):
    """Replace wildcard entries with list of files"""
    plots = []
    for row in plot_layout:
        if not isinstance(row, list) and '*' in row:
            plots.append(
                sorted([
                    splitext(basename(p))[0]
                    for p in glob(join(app.root_path, PLOTS_PATH, row))
                ]))
        else:
            plots.append(row)
    return plots


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
    return render_template('plots.html', plots=expand_wildcards(PLOTS))


@app.route('/plot_<plot>.html')
@requires_auth
def single_plot(plot):
    return render_template('plot.html', plot=plot)


@app.route('/ahrs.html')
@requires_auth
def ahrs():
    return render_template('plots.html', plots=expand_wildcards(AHRS_PLOTS))


@app.route('/reco.html')
@requires_auth
def reco():
    return render_template('plots.html', plots=expand_wildcards(RECO_PLOTS))


@app.route('/sn.html')
@requires_auth
def supernova():
    return render_template('plots.html', plots=expand_wildcards(SN_PLOTS))


@app.route('/compact.html')
@requires_auth
def compact():
    return render_template('plots.html', plots=expand_wildcards(COMPACT_PLOTS))


@app.route('/rttc.html')
@requires_auth
def rttc():
    return render_template(
        'plots.html',
        plots=expand_wildcards(RTTC_PLOTS),
        info=
        "Cable Round Trip Time calculated from realtime data provided by the "
        "Detector Manager. The red lines shows the median and the STD "
        "from the past 24 hours. "
        "RTTC = Cable_RTT - (TX_Slave + RX_Slave + TX_Master + RX_Master)")


# @app.route('/k40.html')
# @requires_auth
# def k40():
#     return render_template(
#         'plots.html',
#         plots=expand_wildcards(K40_PLOTS),
#         info="The first plot shows the intra-DOM calibration. "
#         "y-axis: delta_t [ns], x-axis: cosine of angles. "
#         "The second plot the angular distribution of K40 rates. "
#         "y-axis: rate [Hz], x-axis: cosine of angles. "
#         "blue=before, red=after")


@app.route('/trigger.html')
@requires_auth
def trigger():
    return render_template('plots.html', plots=expand_wildcards(TRIGGER_PLOTS))


@app.route('/top10.html')
@requires_auth
def top10():
    category_names = {
        'n_hits': 'Number of hits',
        'overlays': 'Number of overlays'
    }
    plots = {}
    dbs = LocalDBService(filename="data/monitoring.sqlite3")
    for category in ["overlays", "n_hits"]:
        filenames = [
            q[0]
            for q in dbs.query("SELECT plot_filename FROM event_selection "
                               "ORDER BY {} DESC LIMIT 10".format(category))
        ]
        if len(filenames) > 0:
            plots[category_names[category]] = filenames
    return render_template('top10.html', plots=plots)


@app.route('/logs.html')
@requires_auth
def logs():
    files = OrderedDict()
    filenames = sorted(glob(join(app.root_path, LOGS_PATH, "MSG*.log")),
                       reverse=True)
    main_log = filenames.pop(-1)
    for filename in [main_log] + filenames:
        files[basename(filename)] = getsize(filename)
    return render_template('logs.html', files=files)


@app.route('/logs/<path:filename>')
@requires_auth
def custom_static_logfile(filename):
    filepath = join(app.root_path, LOGS_PATH)
    print("Serving: {}/{}".format(filepath, filename))
    return send_from_directory(join(app.root_path, LOGS_PATH), filename)


@app.route('/plots/<path:filename>')
@requires_auth
def custom_static(filename):
    # filepath = join(app.root_path, PLOTS_PATH)
    # print("Serving: {}/{}".format(filepath, filename))
    return send_from_directory(join(app.root_path, PLOTS_PATH), filename)


@app.route('/rasp.html')
@requires_auth
def rasp():
    return render_template('plots.html', plots=expand_wildcards(RASP_PLOTS))
