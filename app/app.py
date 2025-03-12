from flask import Flask, render_template, jsonify, g, abort
from flask_cors import CORS
import logging
import json
import requests
from datetime import datetime
from dateutil import parser
from sqlalchemy import text, or_

from api import api  # Import the Blueprint from api.py

app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE"]}})  # 允許所有來源訪問 Flask API
app.register_blueprint(api, url_prefix='/api')  # Register the Blueprint

# 配置記錄
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/en/plot_number')
def plot_number():
    fields = get_fields()
    #custom_methods = get_custom_methods()
    return render_template('plot_number_of_datas.html', fields=json.dumps(fields))
    #return render_template('0927_analysis.html', fields=json.dumps(fields))

def get_fields():
    fields = []
    query_fields = g.session.query(db.models.field).order_by(db.models.field.id).all()
    for field in query_fields:
        temp_field = utils.row2dict(field)
        query_field_sensor = (
            g.session
            .query(
                db.models.sensor.name,
                db.models.field_sensor.sensor,
                db.models.field_sensor.df_name,
                db.models.field_sensor.alias,
                db.models.field_sensor.unit,
                db.models.field_sensor.icon,
                db.models.field_sensor.bg_color,
                db.models.field_sensor.alert_min,
                db.models.field_sensor.alert_max
            )
            .select_from(db.models.field_sensor)
            .join(db.models.sensor)
            .filter(db.models.field_sensor.field == field.id)
            .order_by(db.models.field_sensor.id)
            .all()
        )
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
    return fields


if __name__ == '__main__':
     app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True)
