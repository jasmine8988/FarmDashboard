# 個人 / 機密設定範本
# 使用方式：複製本檔為 config_local.py，再填入實際的值。
# config_local.py 已列入 .gitignore，不會上傳到 GitHub；
# 其中的設定會覆蓋 config.py 中同名的設定。

FLASK_SECRET_KEY = '<your_random_secret_key>'

DB_CONFIG = 'mysql+pymysql://<user_name>:<user_password>@localhost:3306/<db_name>?charset=utf8'

# IoTtalk server's URL, for example, 'https://DomainName' or 'http://IP:9999'
CSM_HOST = 'https://<IoTtalk Server>'

# MQTT（選用，不使用就保持 None）
MQTT_broker = None
MQTT_User = '<mqtt_user>'
MQTT_PW = '<mqtt_password>'

# IoTtalk CCM GUI 網址（ccmapi 與 app/ccm_utils.py 共用）
IOTTALK_GUI_URL = 'https://<IoTtalk_CCMAPI_URL>/'

# 自己的 Dashboard 網址（專案自動化完成後回傳給 IoTtalk 的連結）
# 留空則使用 http://localhost:<port>
SERVER_URL = 'https://<Your Server IP>'

DATATALK_USER = '<datatalk_user>'

DEEPSEEK_API_URL = 'http://<DeepSeek_Server_IP>:<port>/api/generate'

demo_token = {
    # '<Field Name>': '<token>',
}
