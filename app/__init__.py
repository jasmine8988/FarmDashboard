import logging
import os
import re

import requests

from flask import Flask, redirect, request, g, send_from_directory
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect

import config

from . import utils
from .demo import demo_api
from .view import view_api
from .api import api
from db import db

log = logging.getLogger("\033[1;35m[WEB]: \033[0m")

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE

app.register_blueprint(view_api, name='VIEW', url_prefix='/')
app.register_blueprint(view_api, name='LANG_VIEW', url_prefix='/<lang_code>')
app.register_blueprint(api, name='API', url_prefix='/api')
app.register_blueprint(demo_api, name='DEMO', url_prefix='/demo')

db.connect()

csrf = CSRFProtect(app)
babel = Babel(app)


### lang code #################################################################
@app.template_filter('extract_path')
def extract_path(s):
    langs = '|'.join(config.i18n.values())

    return re.sub("^(/+{})?/".format(langs), "/", s)


# 1. before blueprint - get lang_code from url
@app.url_value_preprocessor
def get_lang_code(endpoint, values):
    if values is not None:
        g.lang_code = values.pop(
            'lang_code',
            request.accept_languages.best_match(config.i18n.values())
        )


# 2. check lang_code type is available
@app.before_request
def ensure_lang_support():
    lang_code = g.get('lang_code')
    if lang_code and lang_code not in config.i18n.values():
        g.lang_code = request.accept_languages.best_match(config.i18n.values())


# 3. set Flask-babel
@babel.localeselector
def get_locale():
    return g.get('lang_code')


# 4. Set lang_code for redirection or other usage
@app.url_defaults
def set_language_code(endpoint, values):
    if 'lang_code' in values or not g.lang_code:
        return
    if app.url_map.is_endpoint_expecting(endpoint, 'lang_code'):
        values['lang_code'] = g.lang_code
### lang_code end #############################################################


@app.errorhandler(404)
def not_found(error):
    return 'Not Found.', 404


@app.errorhandler(500)
def server_error(error):
    return 'Server error', 500


@app.route('/')
def root():
    return redirect(utils.lang_url('/dashboard_dropdown'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/admin/restart_server/', methods=['GET'], strict_slashes=False)
@utils.required_superuser
def restart_server():
    requests.get('http://localhost:{}/restart_server/'.format(config.RESTART_SERVER_PORT))
    return 'ok'


@app.route('/admin/restart_da/', methods=['GET'], strict_slashes=False)
@utils.required_superuser
def restart_da():
    requests.get('http://localhost:{}/restart_da/'.format(config.RESTART_SERVER_PORT))
    return 'ok'
###############################################################################


@app.before_request
def before_request():
    g.session = db.get_session()


@app.teardown_request
def teardown_request(exception):
    session = getattr(g, 'session', None)
    if session is not None:
        session.close()


@app.after_request
def add_header(r):
    """
    Add no cache header.

    Add headers to both force latest IE rendering engine or Chrome Frame,
    and not cache anything.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r


def main():
    app.run(config.host, port=config.port, debug=config.DEBUG, threaded=True)


if __name__ == '__main__':
    main()
