host = '0'
port = None

DEBUG = False

# use random string for your secret key,
# ex: "FDSDFGHksoyHisHtheHauthorHFDSWERE"
FLASK_SECRET_KEY = 'FDSDFGHksoIyHoTistHtahelHakuthorHFDSWERE'

# DB_CONFIG = '<database>[+<orm_lib>]://[<user>[:<password>]]<host>[:<port>]/[db_name][?charset=utf8]'
# ex: DB_CONFIG = 'mysql+pymysql://user:pass@localhost:3306/db_name?charset=utf8'
# ex: DB_CONFIG = 'sqlite+pysqlite:///db.sqlite3'
DB_CONFIG = ''
DB_POOL_RECYCLE = 600
DB_POOL_SIZE = 100
QUERY_LIMIT = 100
REQUEST_TIMEOUT = 10

# IoTtalk server's URL, for example, 'https://DomainName' or 'http://IP:9999'
CSM_HOST = 'http://127.0.0.1:9999'

#MQTT connection information (optional)
MQTT_broker = None
MQTT_port = 1883
MQTT_encryption = False
MQTT_User = '?'
MQTT_PW = '?'

# IoTtalk CCM GUI URL, used by ccmapi and app/ccm_utils.py
# ex: 'https://classgui.iottalk.tw/'
IOTTALK_GUI_URL = 'https://<IoTtalk_CCMAPI_URL>/'

# This Dashboard's URL, returned to IoTtalk after project automation
# ex: 'https://<Your Server IP>'; leave empty to use http://localhost:<port>
SERVER_URL = ''

# DataTalk databank (Analysis page)
DATATALK_DATABANK_URL = 'https://aitalk.danny.iottalk.tw/datatalk/databank/third-databank/'
DATATALK_USER = '<datatalk_user>'

# DeepSeek (Ollama) analysis server
DEEPSEEK_API_URL = 'http://<DeepSeek_Server_IP>:<port>/api/generate'

# For the demo page without login
# The data format is '<Field Name>':'<token>', examples are shown as follows.
demo_token = {
    'Field1': '65761609-0f1e-4b72-adcf-1ed092454d53',
}

TIMEOUT_STRIKETHROUGH = False

# For login redirect url path check, avoid Open Redirect (ref: CWE-601)
# Allow pattern: http[s]://*.iottalk.tw/* or /*
REDIRECT_REGEX = r"^http[s]?:\/\/[\w.-]*iottalk[2]?\.tw\/|^\/"

SESSION_COOKIE_SECURE = False

RESTART_SERVER_PORT = 5001

i18n = {'English': 'en', '中文': 'zh_Hant_TW', 'ไทย': 'th'}

# 個人 / 機密設定請寫在 config_local.py（已列入 .gitignore，不會上傳），
# 會覆蓋上方同名設定。範本：config_local.example.py
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
