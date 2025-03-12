import logging

from flask import (Blueprint, g, render_template as flask_render_template,
                   redirect, request, session)
from flask_babel import gettext
from werkzeug.security import check_password_hash

import config

from . import utils
from db import db

import json

log = logging.getLogger("\033[1;35m[VIEW]\033[0m")
view_api = Blueprint('VIEW', __name__)


def render_template(*args, **argv):
    fields = []
    query = (g.session
              .query(db.models.field.id,
                     db.models.field.name,
                     db.models.field.alias,
                     db.models.field.iframe,
                     db.models.user_access.is_active)
              .select_from(db.models.field)
              .join(db.models.user_access)
              .join(db.models.user)
              .filter(db.models.user.username == session.get('username'))
              .order_by(db.models.user_access.id)
              .all())
              
    for id, name, alias, iframe, is_active in query:
        field_data = {
            'id': id,
            'name': name,
            'alias': alias,
            'iframe': iframe.replace('{username}', session.get('username')),
            'is_active': 1 & is_active,
            'sensors': []
        }
        for sensor in (g.session
                        .query(db.models.field_sensor)
                        .filter(db.models.field_sensor.field == id)
                        .order_by(db.models.field_sensor.id)
                        .all()):
            field_data['sensors'].append(utils.row2dict(sensor))
        fields.append(field_data)

    user = (g.session
             .query(db.models.user)
             .filter(db.models.user.username == session.get('username'))
             .first())
             
    # 新增datatalk_methods，並在後端解析JSON(因為jinja2不能使用fromjson)
    datatalk_methods = []
    for m in (g.session
              .query(db.models.DatatalkMethod.id,
                     db.models.DatatalkMethod.user,
                     db.models.DatatalkMethod.name,
                     db.models.DatatalkMethod.datatalk_data)
              .order_by(db.models.DatatalkMethod.id)
              .all()):
        try:
            datatalk_data = json.loads(m.datatalk_data)  # 解析 JSON
            datatalk_methods.append([m.id, m.user, m.name, datatalk_data])
        except json.JSONDecodeError:
            log.error(f"JSON 解析失敗: {m.datatalk_data}")
            continue
    return flask_render_template(*args,
                                 fields=fields,
                                 username=session.get('username'),
                                 is_superuser=session.get('is_superuser'),
                                 memo=user.memo,
                                 timeout_strikethrough=config.TIMEOUT_STRIKETHROUGH,
                                 i18n=config.i18n,
                                 datatalk_methods=datatalk_methods,
                                 **argv)


@view_api.route('/', methods=['GET'], strict_slashes=False)
def root():
    return redirect(utils.lang_url('/dashboard'))


@view_api.route('/login/', methods=['GET', 'POST'], strict_slashes=False)
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = (g.session
                 .query(db.models.user)
                 .filter(db.models.user.username == username)
                 .first())

        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['id'] = user.id
            session['is_superuser'] = user.is_superuser

            return utils.security_redirect()
        else:
            return flask_render_template('login.html',
                                         msg=gettext('username or password is wrong.'))

    if session.get('username'):
        return utils.security_redirect()

    return flask_render_template('login.html')


@view_api.route('/logout/', strict_slashes=False)
def logout():
    if session.get('username'):
        del session['username']

    if session.get('id'):
        del session['id']

    if session.get('is_superuser'):
        del session['is_superuser']

    return redirect(utils.lang_url('/login'))


@view_api.route('/dashboard/', methods=['GET'], strict_slashes=False)
@utils.required_login
def index():
    return render_template('dashboard.html')


@view_api.route('/history/', methods=['GET'], strict_slashes=False)
@utils.required_login
def history():
    return render_template('history.html')


@view_api.route('/compare/', methods=['GET'], strict_slashes=False)
@utils.required_login
def compare_():
    return render_template('compare.html')


@view_api.route('/profile/', methods=['GET'], strict_slashes=False)
@utils.required_login
def profile():
    return render_template('profile.html')


@view_api.route('/management/', methods=['GET'], strict_slashes=False)
@utils.required_superuser
def management():
    return render_template('management.html')
    
@view_api.route('/plot/', methods=['GET'], strict_slashes=False)
@utils.required_login
def plot():
    #return render_template('plot.html')
    return render_template('0927_analysis.html')
    
@view_api.route('/plot_number/', methods=['GET'], strict_slashes=False)
@utils.required_login
def plot_number_():
    return render_template('plot_number_of_datas.html')

