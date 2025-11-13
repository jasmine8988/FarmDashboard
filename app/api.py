import inspect
import json
import logging
import re
import time

from datetime import datetime
from dateutil import parser

from flask import Blueprint, abort, jsonify, g, redirect, request, session
from flask_cors import CORS
from sqlalchemy import text, or_
from werkzeug.security import check_password_hash, generate_password_hash

import config

from . import utils
from db import db

from urllib.parse import unquote
from ccmapi.exceptions import CCMAPIError
from ccmapi.v0.devicemodel import get as get_dm
from ccmapi.v0.networkapplication import create as create_na
from ccmapi.v0 import config as ccm_config
from ccmapi.v0.deviceobject import create as create_do
from ccmapi.v0.alias import set as set_alias
from . import ccm_utils

ccm_config.config.api_url = "https://classgui.iottalk.tw/api/v0"

log = logging.getLogger("\033[1;33m[API]: \033[0m")
api = Blueprint('API', __name__)
CORS(api, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"]}})


@api.route('/datas/<string:field>', methods=['GET'])
@utils.required_login
def api_query_all_data(field):
    stime = datetime.now()

    res = {}

    start = request.args.get('start')
    end = request.args.get('end')
    limit = int(request.args.get('limit', config.QUERY_LIMIT))

    if start and end:
        start = parser.parse(start)
        end = parser.parse(end)

    query_df = (g.session
                 .query(db.models.field_sensor.df_name,
                        db.models.field_sensor.field)
                 .select_from(db.models.field_sensor)
                 .join(db.models.sensor)
                 .join(db.models.field)
                 .filter(db.models.field.name == field)
                 .all())

    for df_name, field_id in query_df:
        tablename = df_name.replace('-O', '')
        table = getattr(db.models, tablename)
        query = g.session.query(table).filter(table.field == field_id)
        if start and end:
            query = query.filter(table.timestamp >= start, table.timestamp <= end)
        query = query.order_by(table.timestamp.desc()).limit(limit).all()

        res.update({df_name: [(str(record.timestamp), record.value) for record in query]})

    etime = datetime.now()
    log.debug((etime - stime).total_seconds())
    return jsonify(res)


@api.route('/datas/<string:field>/<string:df_name>', methods=['GET'])
@utils.required_login
def api_query_field_data(field, df_name):
    stime = datetime.now()

    tablename = df_name.replace('-O', '')
    if not hasattr(db.models, tablename):
        abort(404)
    table = getattr(db.models, tablename)

    start = request.args.get('start')
    end = request.args.get('end')
    limit = int(request.args.get('limit', config.QUERY_LIMIT))

    if start and end:
        start = parser.parse(start)
        end = parser.parse(end)

    query = (g.session
              .query(table)
              .select_from(table)
              .join(db.models.field)
              .filter(db.models.field.name == field))
    if start and end:
        query = query.filter(table.timestamp >= start, table.timestamp <= end)
    query = query.order_by(table.timestamp.desc()).limit(limit).all()

    res = {df_name: [(str(record.timestamp), record.value) for record in query]}

    etime = datetime.now()
    log.debug((etime - stime).total_seconds())
    return jsonify(res)


@api.route('/datas', methods=['GET'])
@utils.required_login
def api_datas():
    '''
    :args f1: field, like `flower`, `orange`, etc
    :args f2: field, like `flower`, `orange`, etc
    :args s1: sensor, like `AtPressure`, `UV1`, etc
    :args s2: sensor, like `AtPressure`, `UV1`, etc
    :args st: start_time, any time format
    :args et: end_time, any time format
    :args i: interval, only allow `second`, `minute`, `hour`, `day`, default `hour`
    :args l: limit, query limit, default config.QUERY_LIMIT

    example:
        http://your.domain/api/datas?f1=flower&f2=orange&s1=Temperature&s2=AtPressure&st=2018-06-26&et=2018-06-27&i=second
    '''
    stime = datetime.now()

    field1 = request.args.get('f1')
    sensor1 = request.args.get('s1')
    start_time = request.args.get('st')
    end_time = request.args.get('et')
    interval = request.args.get('i', 'hour')
    limit = int(request.args.get('l')) if request.args.get('l') else None

    if not field1 or not sensor1 or not start_time or not end_time:
        abort(404)

    tablename1 = sensor1.replace('-O', '')
    if not hasattr(db.models, tablename1):
        abort(404)

    table1 = getattr(db.models, tablename1)
    start = parser.parse(start_time).strftime('%Y-%m-%d %H:%M:%S')
    end = parser.parse(end_time).strftime('%Y-%m-%d %H:%M:%S')

    result = {sensor1: {}}

    data1 = _query_data(interval, table1.__tablename__, field1, start, end, limit)
    result[sensor1].update({field1: data1})

    field2 = request.args.get('f2')
    if field2:
        sensor2 = request.args.get('s2')
        tablename2 = sensor2.replace('-O', '')
        table2 = getattr(db.models, tablename2)
        if not result.get(sensor2):
            result[sensor2] = {}
        data2 = _query_data(interval, table2.__tablename__, field2, start, end, limit)
        result[sensor2].update({field2: data2})

    etime = datetime.now()
    log.debug((etime - stime).total_seconds())
    return jsonify(result)


@api.route('/export_datas', methods=['GET'])
@utils.required_login
def api_export_datas():
    '''
    :args f: field, like `flower`, `orange`, etc
    :args s: sensor, like `AtPressure`, `UV1`, etc
    :args st: start_time, any time format
    :args et: end_time, any time format
    :args i: interval, only allow `second`, `minute`, `hour`, `day`, default `hour`
    :args l: limit, query limit, default config.QUERY_LIMIT

    example:
        http://your.domain/api/export_datas?f=flower&s=Temperature&st=2018-06-26&et=2018-06-27&i=second
    '''
    stime = datetime.now()

    field = request.args.get('f')
    sensor = request.args.get('s')
    start_time = request.args.get('st')
    end_time = request.args.get('et')
    interval = request.args.get('i', 'hour')
    limit = int(request.args.get('l')) if request.args.get('l') else None

    if not field or not sensor or not start_time or not end_time:
        abort(404)

    tablename = sensor.replace('-O', '')
    if not hasattr(db.models, tablename):
        abort(404)

    table = getattr(db.models, tablename)
    start = parser.parse(start_time).strftime('%Y-%m-%d %H:%M:%S')
    end = parser.parse(end_time).strftime('%Y-%m-%d %H:%M:%S')

    raw_data = _query_data(interval, table.__tablename__, field, start, end, limit)

    content = 'datetime,value\n'

    for data in raw_data[::-1]:
        if interval == 'second':
            content += '{},{}\n'.format(data['timestamp'],
                                        data['value'])
        elif interval == 'minute':
            content += '{} {}:{}:00,{}\n'.format(data['date'],
                                                 data['hour'],
                                                 data['minute'],
                                                 data['value'])
        elif interval == 'hour':
            content += '{} {}:00:00,{}\n'.format(data['date'],
                                                 data['hour'],
                                                 data['value'])
        elif interval == 'day':
            content += '{} 00:00:00,{}\n'.format(data['date'],
                                                 data['value'])
    etime = datetime.now()
    log.debug((etime - stime).total_seconds())
    return content


def _query_data(interval, table_name, field, start, end, limit):
    raw_sql = _get_mysql_raw_sql(interval, table_name, field, start, end, limit)
    query = g.session.execute(raw_sql).fetchall()

    datas = []
    for row in query:
        data = {}
        for key in row.keys():
            data[key] = str(row[key])
        datas.append(data)

    return datas


def _get_mysql_raw_sql(interval, table_name, field, start, end, limit):
    if interval == 'second':
        raw_sql = text('''
            SELECT sensor.timestamp, sensor.value
            FROM {} as sensor
            LEFT JOIN field on field.id = sensor.field
            WHERE field.name = '{}' and
                  sensor.timestamp >= '{}' and
                  sensor.timestamp <= '{}'
            ORDER BY sensor.timestamp DESC
        '''.format(table_name, field, start, end))
    elif interval == 'minute':
        raw_sql = text('''
            SELECT MINUTE(sensor.timestamp) as minute,
                   HOUR(sensor.timestamp) AS hour,
                   DATE(sensor.timestamp) AS date,
                   AVG(sensor.value) AS value
            FROM {} as sensor
            LEFT JOIN field on field.id = sensor.field
            WHERE field.name = '{}' and
                  sensor.timestamp >= '{}' and
                  sensor.timestamp <= '{}'
            GROUP BY minute, hour, date
            ORDER BY date DESC, hour DESC, minute DESC
        '''.format(table_name, field, start, end))
    elif interval == 'hour':
        raw_sql = text('''
            SELECT HOUR(sensor.timestamp) AS hour,
                   DATE(sensor.timestamp) AS date,
                   AVG(sensor.value) AS value
            FROM {} as sensor
            LEFT JOIN field on field.id = sensor.field
            WHERE field.name = '{}' and
                  sensor.timestamp >= '{}' and
                  sensor.timestamp <= '{}'
            GROUP BY hour, date
            ORDER BY date DESC, hour DESC
        '''.format(table_name, field, start, end))
    elif interval == 'day':
        raw_sql = text('''
            SELECT DATE(sensor.timestamp) AS date,
                   AVG(sensor.value) AS value
            FROM {} as sensor
            LEFT JOIN field on field.id = sensor.field
            WHERE field.name = '{}' and
                  sensor.timestamp >= '{}' and
                  sensor.timestamp <= '{}'
            GROUP BY date
            ORDER BY date DESC
        '''.format(table_name, field, start, end))
    else:
        abort(404)

    if limit:
        raw_sql += 'LIMIT {}'.format(limit)

    return raw_sql


@api.route('/user/pwd', methods=['POST'])
@utils.required_login
def api_user_change_pwd():
    user_id = session.get('id')
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')

    if not new_password:
        return 'new password should be given.', 404
    elif old_password == new_password:
        return 'New password can not be identical to the original one', 404
    elif len(new_password) < 6:
        return 'Password length must be greater than or equal to 6', 404
    elif not utils.validate_password_combination(new_password):
        return 'Password must contain at least three of them: Uppercase letters, ' \
               'Lowercase letters, numbers and special symbols', 404

    user = g.session.query(db.models.user).filter(db.models.user.id == user_id).first()

    if not user:
        return 'Who are you?', 404

    if not check_password_hash(user.password, old_password):
        return 'Old passwrod not match.', 404

    user.password = generate_password_hash(new_password)
    g.session.commit()

    return 'ok'


@api.route('/user/delete', methods=['POST'])
@utils.required_login
def api_user_delete_account():
    user_id = session.get('id')
    username = request.json.get('username')
    password = request.json.get('password')

    if not password:
        return 'Password should be given.', 404

    user = g.session.query(db.models.user).filter(db.models.user.id == user_id).first()

    if not user:
        return 'Who are you?', 404

    if user.username != username:
        return 'username not match', 404

    if not check_password_hash(user.password, password):
        return 'Passwrod not match.', 404

    g.session.query(db.models.user_access).filter(db.models.user_access.user == user_id).delete()
    g.session.query(db.models.user).filter(db.models.user.id == user_id).delete()
    g.session.commit()

    if session.get('username'):
        del session['username']

    if session.get('id'):
        del session['id']

    if session.get('is_superuser'):
        del session['is_superuser']

    return redirect('/')
    return 'ok'


@api.route('/user/memo', methods=['POST'])
@utils.required_login
def api_user_update_memo():
    if request.method != 'POST':
        abort(404)

    user_id = session.get('id')
    if not user_id:
        abort(404)

    memo = request.json.get('memo')
    g.session.query(db.models.user).filter(db.models.user.id == user_id).update({'memo': memo})
    g.session.commit()

    return 'ok'


@api.route('/user', methods=['GET', 'POST', 'PUT', 'DELETE'])
@utils.required_superuser
def api_user():
    if request.method == 'GET':
        # Read user
        # GET /api/user[?id=<id>&username=<username>]
        users = []

        query = g.session.query(db.models.user)
        for key, value in request.args.items():
            attr = getattr(db.models.user, key, None)
            if attr:
                query = query.filter(attr == value)
        query = query.order_by(db.models.user.id).all()

        for user in query:
            query_access = (g.session
                             .query(db.models.field, db.models.user_access)
                             .select_from(db.models.user_access)
                             .join(db.models.field)
                             .filter(db.models.user_access.user == user.id)
                             .order_by(db.models.user_access.id)
                             .all())
            access = []
            active = None
            for field, acc in query_access:
                access.append(utils.row2dict(field))
                if acc.is_active:
                    active = acc.field

            users.append({
                'id': user.id,
                'username': user.username,
                'is_superuser': user.is_superuser,
                'access': access,
                'active': active
            })
        return json.dumps(users)
    elif request.method == 'POST':
        # Create user
        # POST /api/user
        # {username:<username>, password:<password>, is_superuser:<is_superuser>}
        username = request.json.get('username')
        password = request.json.get('password', '')
        is_superuser = request.json.get('is_superuser')
        access = request.json.get('access', [])
        active = request.json.get('active')

        if not username:
            return 'No username', 404
        elif len(password) < 6:
            return 'Password length must be greater or equal to 6', 404
        elif not utils.validate_password_combination(password):
            return 'Password must contain at least three of them: Uppercase letters, ' \
                   'Lowercase letters, numbers and special symbols', 404

        # duplicate check
        user_record = g.session.query(db.models.user).filter(db.models.user.username == username).count()
        if user_record > 0:
            return 'The username "{}" already exists'.format(username), 404

        password = generate_password_hash(password)

        new_user = db.models.user(username=username,
                                  password=password,
                                  is_superuser=is_superuser)
        g.session.add(new_user)
        g.session.commit()

        for field in access:
            new_access = db.models.user_access(user=new_user.id, field=field.get('id'))
            if field.get('id') == active:
                new_access.is_active = True
            g.session.add(new_access)
        g.session.commit()

        return json.dumps(utils.row2dict(new_user))
    elif request.method == 'PUT':
        # Update user
        # PUT /api/user
        # {id:<id>, username:<username>, is_superuser:<is_superuser>}
        id_ = request.json.get('id')
        username = request.json.get('username')
        is_superuser = request.json.get('is_superuser')
        access = request.json.get('access', [])
        active = request.json.get('active')

        # duplicate check
        user_record = (g.session
                        .query(db.models.user)
                        .filter(db.models.user.username == username,
                                db.models.user.id != id_)
                        .count())
        if user_record > 0:
            return 'The username "{}" already exists'.format(username), 404

        (g.session
          .query(db.models.user)
          .filter(db.models.user.id == id_)
          .update({'username': username,
                   'is_superuser': is_superuser}))
        (g.session
          .query(db.models.user_access)
          .filter(db.models.user_access.user == id_)
          .delete())
        for field in access:
            new_access = db.models.user_access(user=id_, field=field.get('id'))
            if field.get('id') == active:
                new_access.is_active = True
            g.session.add(new_access)
        g.session.commit()

        return 'ok'
    elif request.method == 'DELETE':
        # Delete user
        # DELETE /api/user?id=<id>
        id_ = request.args.get('id')
        (g.session
          .query(db.models.user_access)
          .filter(db.models.user_access.user == id_)
          .delete())
        (g.session
          .query(db.models.user)
          .filter(db.models.user.id == id_)
          .delete())
        g.session.commit()

        return 'ok'

    abort(404)


@api.route('/sensor', methods=['GET', 'POST', 'PUT', 'DELETE'])
@utils.required_superuser
def api_sensor():
    if request.method == 'GET':
        # Read sensor
        # GET /api/sensor
        sensors = g.session.query(db.models.sensor).order_by(db.models.sensor.id).all()
        return json.dumps([utils.row2dict(sensor) for sensor in sensors])
    elif request.method == 'POST':
        # Create sensor
        # POST /api/sensor
        # {name:<string>, df_name:<string>, alias:<string>, unit:<string>,
        #  icon:<string>, bg_color:<string>}
        df_name = request.json.get('df_name')
        name = request.json.get('name')
        if not df_name:
            return 'No df_name', 404
        if not name:
            return 'No name', 404

        # duplicate check
        sensor_record = (g.session
                          .query(db.models.sensor)
                          .filter(or_(db.models.sensor.name == name,
                                      db.models.sensor.df_name == df_name))
                          .count())
        if sensor_record > 0:
            return 'The sensor name "{}" or df_name "{}" already exists'.format(name, df_name), 404

        db.inject_new_model(re.sub(r'-O[\d]*$', '', df_name))

        new_sensor = db.models.sensor(df_name=df_name,
                                      name=request.json.get('name'),
                                      alias=request.json.get('alias'),
                                      unit=request.json.get('unit'),
                                      icon=request.json.get('icon'),
                                      bg_color=request.json.get('bg_color'))
        g.session.add(new_sensor)
        g.session.commit()

        return json.dumps(utils.row2dict(new_sensor))
    elif request.method == 'PUT':
        # Update sensor
        # PUT /api/sensor
        # {id:<int>, name:<string>, df_name:<string>, alias:<string>,
        #  unit:<string>, icon:<string>, bg_color:<string>}
        id_ = request.json.get('id')
        df_name = request.json.get('df_name')
        name = request.json.get('name')

        if not df_name:
            return 'No df_name', 404
        if not name:
            return 'No name', 404

        # duplicate check
        sensor_record = (g.session
                          .query(db.models.sensor)
                          .filter(or_(db.models.sensor.name == name,
                                      db.models.sensor.df_name == df_name),
                                  db.models.sensor.id != id_)
                          .count())
        if sensor_record > 0:
            return 'The sensor name "{}" or df_name "{}" already exists'.format(name, df_name), 404

        db.inject_new_model(re.sub(r'-O[\d]*$', '', df_name))

        (g.session
          .query(db.models.sensor)
          .filter(db.models.sensor.id == id_)
          .update(request.json))
        g.session.commit()

        return 'ok'
    elif request.method == 'DELETE':
        # Delete sensor
        # DELETE /api/sensor?id=<id>
        id_ = request.args.get('id')
        (g.session
          .query(db.models.sensor)
          .filter(db.models.sensor.id == id_)
          .delete())
        g.session.commit()

        return 'ok'

    abort(404)


@api.route('/field', methods=['GET', 'POST', 'PUT', 'DELETE'])
@utils.required_superuser
def api_field():
    if request.method == 'GET':

        fields = []
        query_fields = (g.session
                         .query(db.models.field)
                         .order_by(db.models.field.id)
                         .all())

        for field in query_fields:
            temp_field = utils.row2dict(field)
            query_field_sensor = (g.session
                                   .query(db.models.sensor.name,
                                          db.models.field_sensor.sensor,
                                          db.models.field_sensor.df_name,
                                          db.models.field_sensor.alias,
                                          db.models.field_sensor.unit,
                                          db.models.field_sensor.icon,
                                          db.models.field_sensor.bg_color,
                                          db.models.field_sensor.alert_min,
                                          db.models.field_sensor.alert_max)
                                   .select_from(db.models.field_sensor)
                                   .join(db.models.sensor)
                                   .filter(db.models.field_sensor.field == field.id)
                                   .order_by(db.models.field_sensor.id)
                                   .all())
            temp_field['sensors'] = []
            for sensor in query_field_sensor:
                temp_sensor = {
                    'name': sensor.name,
                    'sensor': sensor.sensor,
                    'df_name': sensor.df_name,
                    'alias': sensor.alias,
                    'unit': sensor.unit,
                    'icon': sensor.icon,
                    'bg_color': sensor.bg_color,
                    'alert_min': sensor.alert_min,
                    'alert_max': sensor.alert_max,
                }
                temp_field['sensors'].append(temp_sensor)
            fields.append(temp_field)

        return json.dumps(fields)
    elif request.method == 'POST':
        # Create field
        # POST /api/field
        # {name:<string>, alias:<string>, sensors: [<sensor>, ...]}
        name = request.json.get('name')
        if not name:
            return 'No field name', 404

        # duplicate check
        field_record = g.session.query(db.models.field).filter(db.models.field.name == name).count()
        if field_record > 0:
            return 'The field name "{}" already exists'.format(name), 404

        new_field = db.models.field(name=request.json.get('name'),
                                    alias=request.json.get('alias'),
                                    iframe=request.json.get('iframe', ''))
        g.session.add(new_field)
        g.session.commit()

        for sensor in request.json.get('sensors', []):
            new_sensor = db.models.field_sensor(
                field=new_field.id,
                sensor=sensor.get('sensor'),
                df_name=sensor.get('df_name'),
                alias=sensor.get('alias'),
                unit=sensor.get('unit'),
                icon=sensor.get('icon'),
                bg_color=sensor.get('bg_color'),
                alert_min=sensor.get('alert_min'),
                alert_max=sensor.get('alert_max'))
            g.session.add(new_sensor)
            g.session.commit()

        return json.dumps(utils.row2dict(new_field))
    elif request.method == 'PUT':
        # Update field
        # PUT /api/field
        # {name:<string>, alias:<string>, sensors: [<sensor>, ...]}
        id_ = request.json.get('id')
        name = request.json.get('name')
        alias = request.json.get('alias')
        iframe = request.json.get('iframe', '')
        sensors = request.json.get('sensors', [])

        if not name:
            return 'No field name', 404

        # duplicate check
        field_record = (g.session
                         .query(db.models.field)
                         .filter(db.models.field.name == name,
                                 db.models.field.id != id_)
                         .count())
        if field_record > 0:
            return 'The field name "{}" already exists'.format(name), 404

        (g.session
          .query(db.models.field)
          .filter(db.models.field.id == id_)
          .update({'name': name,
                   'alias': alias,
                   'iframe': iframe}))
        (g.session
          .query(db.models.field_sensor)
          .filter(db.models.field_sensor.field == id_)
          .delete())
        for sensor in sensors:
            df_name = sensor.get('df_name')
            db.inject_new_model(df_name.replace('-O', ''))

            new_sensor = db.models.field_sensor(
                field=id_,
                sensor=sensor.get('sensor'),
                df_name=sensor.get('df_name'),
                alias=sensor.get('alias'),
                unit=sensor.get('unit'),
                icon=sensor.get('icon'),
                bg_color=sensor.get('bg_color'),
                alert_min=sensor.get('alert_min'),
                alert_max=sensor.get('alert_max'))
            new_sensor.field = id_
            new_sensor.id = None
            g.session.add(new_sensor)
            g.session.commit()
        g.session.commit()

        return 'ok'
    elif request.method == 'DELETE':
        # Delete field
        # DELETE /api/field?id=<id>
        id_ = request.args.get('id')

        for attr in db.models.__dict__.values():
            if inspect.isclass(attr) and hasattr(attr, 'timestamp'):
                (g.session
                  .query(attr)
                  .filter(attr.field == id_)
                  .delete())
        (g.session
          .query(db.models.field_sensor)
          .filter(db.models.field_sensor.field == id_)
          .delete())
        (g.session
          .query(db.models.user_access)
          .filter(db.models.user_access.field == id_)
          .delete())
        (g.session
          .query(db.models.field)
          .filter(db.models.field.id == id_)
          .delete())
        g.session.commit()

        return 'ok'

    abort(404)


def get_dm_id_by_name(dm_name: str):
    dm_info = get_dm(dm_name)
    return dm_info['dm_id'] if isinstance(dm_info, dict) and 'dm_id' in dm_info else None  


# 根據 iottalk project 資訊，自動創建 sensors 與 field
def auto_create_fieldsensor(updated_info):
    try:
        session = g.session
        project_name = updated_info['p_name']

        # Step 1: 擷取所有 df_name（從 ODO 的 DFO）
        output_df_names = [
            dfo.get('alias_name')
            for odo in updated_info.get('odo', [])
            for dfo in odo.get('dfo', [])
            if dfo.get('alias_name')
        ]

        # Step 2: 建立 field（以 project_name 為名）
        device_name = project_name+'_Dashboard'
        field = session.query(db.models.field).filter_by(name=device_name).first()
        created_field = False
        #如果field不存在，則創建，並且restart_da
        if not field:
            field = db.models.field(name=device_name, alias=project_name, iframe='')
            session.add(field)
            session.commit()
            created_field = True
            #requests.get('http://localhost:5001/restart_da/')
            #requests.get('http://localhost:5001/signal_da_sync/', params={'project': project_name})
        field_id = field.id

        # Step 3: 建立 field_sensor 關聯（若不存在）
        sensor_map = {
            s.df_name: s for s in session.query(db.models.sensor).all()
        }
        existing_links = {
            row.df_name for row in session.query(db.models.field_sensor.df_name).filter_by(field=field_id).all()
        }

        updated_field_sensors = []
        for df_name in output_df_names:
            if df_name in sensor_map and df_name not in existing_links:
                sensor = sensor_map[df_name]
                fs = db.models.field_sensor(
                    field=field_id,
                    sensor=sensor.id,
                    df_name=df_name,
                    alias=sensor.alias,
                    unit=sensor.unit,
                    icon=sensor.icon,
                    bg_color=sensor.bg_color,
                    alert_min=0,
                    alert_max=0
                )
                session.add(fs)
                updated_field_sensors.append(df_name)

        session.commit()


        return jsonify({
            'status': 'success',
            'created_field': created_field,
            'updated_field_sensors': updated_field_sensors
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def wait_for_device_registration(p_id, do_id, device_name, timeout=20, interval=1):
    """
    等待設備完成註冊，並返回相應的 d_id。
    """
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        # 獲取設備清單
        device_list = ccm_utils.get_device_list(p_id, do_id)["device_info"]
        print('wait_for_device_registration')
        for d in device_list:
            if d[0] == device_name:  # 檢查是否註冊完成
                return d[2]  # 返回 d_id
        time.sleep(interval)  # 等待一段時間再重新檢查
    raise TimeoutError(f"Device '{device_name}' registration timed out.")


def auto_create_fieldsensor_next(project_name):
    try:
        success, project_info = ccm_utils.get_project_by_name(project_name)
        if not success or not isinstance(project_info, dict):
            raise TypeError("Invalid project response")

        session = g.session
        device_name = project_name + "_Dashboard"

        # === Step 1: 建立 NA-based Mapping ===
        widget_mapping = {}
        for idx, na in enumerate(project_info.get("na", [])):
            input_dfo = na["input"][0]
            output_dfo = na["output"][0]

            # 找 output alias
            alias_out = None
            for odo in project_info.get("odo", []):
                for dfo in odo.get("dfo", []):
                    if dfo["dfo_id"] == output_dfo["dfo_id"]:
                        alias_out = dfo["alias_name"]
                        break
                if alias_out:
                    break

            if alias_out:
                widget_name = f"Widget{idx+1}-O"   # 與 NA index 一致
                widget_mapping[widget_name] = alias_out

        print("📌 widget_mapping (NA based):", widget_mapping)

        # === Step 2: 更新 DB ===
        field = session.query(db.models.field).filter_by(name=device_name).first()
        if not field:
            raise Exception(f"Field {device_name} not found.")
        field_id = field.id

        updated_aliases = []
        for df_name, alias in widget_mapping.items():
            fs = session.query(db.models.field_sensor).filter_by(field=field_id, df_name=df_name).first()
            if fs:
                fs.alias = alias.replace("-O", "")
                updated_aliases.append({"df_name": df_name, "alias": alias})

        # 移除多餘
        valid_df_names = set(widget_mapping.keys())
        all_fs = session.query(db.models.field_sensor).filter_by(field=field_id).all()
        for fs in all_fs:
            if fs.df_name not in valid_df_names:
                session.delete(fs)
                print(f"🗑️ 刪除多餘的 field_sensor: {fs.df_name}")

        session.commit()
        return jsonify({"status": "success", "updated_aliases": updated_aliases})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


#排序收到的ODF為數字，原本使用字典，導致10會在2前面
def widget_sort_key(dfo):
    name = dfo.get('alias_name', '')
    if name.startswith("Widget") and name.endswith("-O"):
        try:
            # 把 "Widget10-O" → 取中間的數字 10
            return int(name.replace("Widget", "").replace("-O", ""))
        except ValueError:
            return float("inf")  # 無法轉數字的放最後
    return float("inf")


##測試使用widget{i}-O動態產生對應的alias name
@api.route('/<path:project_name>', methods=["GET"])
def sync_odf_from_idf(project_name):
    global _last_project_cache
    project_name = unquote(project_name)
    device_name = project_name + '_Dashboard'
    print(f"🔍 Received request for project: {project_name}")

    try:
        # === Step 1: 載入 Project 資訊 ===
        success, project_info = ccm_utils.get_project_by_name(project_name)
        if not success or not isinstance(project_info, dict):
            raise TypeError(f"Invalid project response: {success, project_info}")
        
        p_id = project_info['p_id']
        print(f"✅ project_info loaded for p_id={p_id}")

        # === Step 2: 收集所有輸入 alias (跨所有 IDO) ===
        all_inputs = []
        for ido in project_info.get("ido", []):
            for dfo in ido.get("dfo", []):
                all_inputs.append(dfo["alias_name"])
        print(f"📥 all_inputs: {all_inputs}")

        # === 判斷是否已有 Dashboard DO，避免重複建立 ===
        has_dashboard_do = any(
            odo.get("dm_name") == "Dashboard"
            for odo in project_info.get("odo", [])
        )
        if has_dashboard_do:
            print(f"⚠️ 專案 {project_name} 已存在 Dashboard DO，跳過建立")
            return jsonify({
                "url": f"https://1iaolo.iottalk.tw/api/active_field/{device_name}",
                "error": None
            })

        # === Step 3: 為每個 input 建立對應 DF (WidgetX-O) ===
        created_df_ids = []
        for i in range(len(all_inputs)):
            df_name = f"Widget{i+1}-O"
            success, df_info = ccm_utils.get_devicefeature(df_name)
            if not success or not isinstance(df_info, dict):
                raise Exception(f"❌ DeviceFeature not found: {df_name}")
            created_df_ids.append(df_info["df_id"])
            print(f"✅ Collected DF: {df_name} → df_id={df_info['df_id']}")

        # === Step 4: 建立 Dashboard DO ===
        print("🔧 Creating DeviceObject...")
        #dm_id = get_dm_id_by_name("Dashboard")
        dm_info = get_dm("Dashboard") # 取得"Dashboard"DM的dm_id
        success, do_id_list = ccm_utils.create_deviceobject(p_id, dm_info['dm_id'], created_df_ids)
        if not success:
            raise Exception("❌ Failed to create DeviceObject")
        print(f"🧩 DOs created: {do_id_list}")

        # === Step 5: 重新載入 Project info，建立 Field (此時還是 WidgetX-O) ===
        success, updated_info = ccm_utils.get_project_by_name(project_name)
        if not success:
            raise Exception("❌ Failed to reload project info after DO creation")
            
        auto_create_fieldsensor(updated_info)

        # === Step 6: 收集 ODO (Dashboard) ===
        dashboard_odo = next(
            (odo for odo in updated_info.get("odo", []) if odo.get("dm_name") == "Dashboard"),
            None
        )
        if not dashboard_odo:
            raise Exception("❌ Dashboard ODO not found after creation")

        dashboard_outputs = sorted(dashboard_odo["dfo"], key=widget_sort_key)

        # === Step 7: 建立 Network Applications (一一對應) ===
        #requests.get('http://localhost:5001/restart_da/')
        for input_dfo, output_dfo in zip(
            [dfo for ido in updated_info["ido"] for dfo in ido["dfo"]],
            dashboard_outputs
        ):
            success, na_id = ccm_utils.create_networkapplication(
                project_id=p_id,
                input_dfo_id=input_dfo["dfo_id"],
                output_dfo_id=output_dfo["dfo_id"]
            )
            if success:
                print(f"✅ NA created: {na_id} (Input: {input_dfo['dfo_id']}, Output: {output_dfo['dfo_id']})")
            else:
                print(f"❌ Failed to create NA for Input {input_dfo['dfo_id']} → Output {output_dfo['dfo_id']}")

        # === Step 8: 等待 DA 註冊並綁定 ===
        requests.get('http://localhost:5001/restart_da/')
        #requests.get('http://localhost:5001/signal_da_sync/', params={'project': project_name})
        try:
            do_id = do_id_list[0]
            d_id = wait_for_device_registration(p_id, do_id, device_name, 20, 1)
            ccm_utils.bind_device(p_id, do_id, d_id)
            print(f"🔗 Device {device_name} successfully bound!")
        except TimeoutError as e:
            print(f"⚠️ {e}")

        # === Step 9: 設定 alias (依輸入對應輸出) ===
        print(f"🛠️ Setting aliases")
        for idx, alias_in in enumerate(all_inputs):
            alias_out = alias_in.replace("-I", "-O") if alias_in.endswith("-I") else alias_in + "-O"
            widget_name = f"Widget{idx+1}-O"
            try:
                set_alias(device_name, widget_name, alias_out)
                print(f"✅ 成功設定 alias: {widget_name} → {alias_out}")
            except Exception as e:
                print(f"❌ 設定 alias 失敗: {widget_name} → {alias_out}, 錯誤: {e}")

        # === Step 10: 更新 field_sensor alias ===
        auto_create_fieldsensor_next(project_name)
        #requests.get('http://localhost:5001/restart_da/')

        # === Step 11: 回傳 URL ===
        return jsonify({
            "url": f"https://1iaolo.iottalk.tw/api/active_field/{device_name}",
            "error": None
        })

    except CCMAPIError as e:
        print(f"[CCMAPI ERROR] {e}")
        return jsonify({"status": "error", "message": f"CCMAPIError: {e}"}), 500
    except Exception as e:
        print(f"[GENERAL ERROR] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@api.route('/active_field/<field_name>', methods=['GET'])
@utils.required_login
def active_field(field_name):
    try:
        session_db = g.session
        username = session.get('username')
        if not username:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        user = session_db.query(db.models.user).filter_by(username=username).first()
        if not user:
            return jsonify({'status': 'error', 'message': f'User \"{username}\" not found'}), 404

        # 將這個 field 設為 active，其他設為 False
        field = session_db.query(db.models.field).filter_by(name=field_name).first()
        if not field:
            return jsonify({'status': 'error', 'message': f'Field \"{field_name}\" not found'}), 404

        # 取消該 user 現有的 active
        session_db.query(db.models.user_access) \
                  .filter_by(user=user.id) \
                  .update({db.models.user_access.is_active: False})

        # 設定這個 field 為 active（若沒有就建立）
        access = session_db.query(db.models.user_access) \
                           .filter_by(user=user.id, field=field.id) \
                           .first()
        if not access:
            access = db.models.user_access(user=user.id, field=field.id, is_active=True)
            session_db.add(access)
        else:
            access.is_active = True

        session_db.commit()

        # ✅ 回到來源頁（沒有就回 dashboard）
        nxt = request.args.get('next') or '/en/dashboard_dropdown'
        return redirect(nxt)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500
