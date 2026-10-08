# FarmDashboard

* [Dashboard操作教學影片](https://drive.google.com/drive/folders/1FzIw1JNRFQnolcPIUbQeKGKvFmZ63EKW?usp=drive_link)

***Field 的名稱不可以包含特如符號如 . $ # & @ 等等，請使用全英文字母***

## 簡易安裝說明

1. 安裝 **tmux**：

    ubuntu: 

    ```sh
    sudo apt-get install tmux
    ```

2. 安裝 python 相關需要套件：

    ```sh
    sudo pip3 install -r requirements.txt
    ```

3. 安裝Database，使用 MySQL
    * 安裝 MySQL (version >= 5.7) (注意1)

        ```sh
        sudo apt-get install mysql-server
        ```
    * Login mysql(以root使用者登入)
        ```
        sudo mysql -u root -p     
        ```
    * Check characterset status
        ```
        status
        ```
        編碼應該要如下圖:四個都是utf8

        https://i.imgur.com/4P5Dobl.png

        若不是，則修改 my.cnf       
        ```
        sudo vim /etc/mysql/my.cnf
        ```
        加入設定:複製下列程式碼，於my.cnf貼上
        ```
        [mysqld]
        init_connect = 'SET collation_connection = utf8_bin'
        init_connect = 'SET NAMES utf8'
        character-set-server = utf8
        collation-server = utf8_bin
        ```

    * 重啟mysql以更新設定

        ```
        sudo service mysql restart
        ```
        
    * 登進mysql新增 MySQL 內的 user，允許連線 IP，與資料庫( **db_name** )，以及權限 (注意2)
        ```
        CREATE USER '<user_name>'@'%' IDENTIFIED BY '<user_password>';
        GRANT ALL PRIVILEGES ON *.* TO '<user_name>'@'%';
        CREATE DATABASE <db_name>;
        ```
        
    * 另需安裝 **ccmapi**（PyPI 上沒有）：

        ```sh
        pip3 install git+ssh://git@gitlab.com/IoTtalk/ccmapi-py.git
        ```

4. 建立個人設定檔 **config_local.py**

    密碼、網址等個人資訊請寫在 `config_local.py`，**不要**直接改 `config.py`。
    `config_local.py` 已列入 `.gitignore`，不會上傳到 GitHub，其中的設定會覆蓋 `config.py` 中同名的設定。

    ```sh
    cp config_local.example.py config_local.py
    ```

    依 *注意2* 填入 **DB_CONFIG**

        DB_CONFIG = 'mysql+pymysql://<user_name>:<user_password>@localhost:3306/<db_name>?charset=utf8'

    填入 **CSM_HOST**

        CSM_HOST = 'https://<IoTtalk Server>'

5. 在 **config_local.py** 填寫 **IoTtalk CCMAPI URL**（ccmapi 與 app/ccm_utils.py 共用）

        IOTTALK_GUI_URL = 'https://<IoTtalk_CCMAPI_URL>/'

6. 在 **config_local.py** 填寫自己的 **Dashboard 網址**

    專案自動化完成後，會回傳 `<SERVER_URL>/api/active_field/<device_name>` 給 IoTtalk。
    留空則使用 `http://localhost:<port>`。

        SERVER_URL = 'https://<Your Server IP>'

7. 設定 **admin** 密碼

    ```sh
    cp db/db_init.json db/db_init_local.json
    ```

    修改 **db/db_init_local.json** 中的 admin 密碼（此檔不會上傳，初始化時會優先讀取）。

8. 資料庫初始化：

    ```sh
    python3 -m db.db init
    ```

    * 注意：此步只能執行一次 (只會新加入，並不會抹除舊的資料，所以執行一次以上會錯誤)

    * 在MAC上面使用時可能會遇到加密錯誤的錯誤訊息，這時需要安裝套件 cryptography

9. 啟動 Server：

    ```sh
    bash startup.sh
    ```

至此 Dashboard 已啟動完成，可用指令 ```tmux a``` 查看運行狀況
(按ctrl+b 1 查看 dashboard 主程式與 DA 運行狀況)。

* Windows：建立 venv 並安裝套件後，雙擊 `start_windows.bat` 即可啟動（取代 `startup.sh`）。

### 注意

* 注意1: 安裝mysql時，常會遇到安裝過程中，完全沒問密碼，這表示以前曾經裝過mysql，或是裝過相關套件，這時就比需要重設密碼，執行下列指令進行重設，

    ```sh
    sudo mysqladmin -u root password
    ```
    Reference: https://emn178.pixnet.net/blog/post/87659567

  或是查看系統預設的 帳號 與 密碼
  ```
  sudo vim /etc/mysql/debian.cnf
  ```
  Reference: https://andy6804tw.github.io/2019/01/31/ubuntu-mysql-password/

* 注意2: **DB_CONFIG=mysql+pymysql://<user>:<pass>@localhost:3306/<db_name>?charset=utf8**

  其中的 **db_name**，就是打算要建立的資料庫名稱，例如要給 Dashboard 用的，就取名為 ***dashboard***，該主表名稱不是隨便亂輸入的，  通常是在db內建立 user 時，就順道建立一同名的 table，這樣最簡單   (例如，假設使用 phpmyadmin 建立使用者時，就勾選 "建立與使用者同名的資料庫並授予所有權限。")，  權限部分，如果不確定怎麼使用，就全開吧。所以 **db_name** 必須是已存在的資料庫，  而不是隨便亂輸入的。
   
  然後，在建立使用者時，很高的機率會發生錯誤 
  "Your password does not satisfy the current policy requirements"，
  這時要去調降密碼強度限制，解決方法為連上mysql應用，使用如下指令後，  就可以順利建立 user/table 了。

  執行 `mysql -u root -p` 打完密碼後進入 MySQL 命令列，然後執行下方指令::
    ```sql
    mysql> set global validate_password_policy=0;    
    mysql> exit
    ```
  如果是遠端連線，要注意兩點 
  * 要設定該使用者允許連線的 IP，沒去設定的話，絕對是連不上的
  * 記得去掉設定檔內的 `bind 127.0.0.1`


### 多語系使用說明

#### 文字準備

##### python
---

use `gettext('')` to the needing change words.
```python
from flask_babel import gettext
msg = gettext('Babel is good.')
```
or if you want to use constant strings somewhere in your application and define them outside of a request, you can use a lazy strings `lazy_gettext('')`.

```python
from flask_babel import lazy_gettext
msg = lazy_gettext('Babel is good.')
```

##### Javascript
---

use `{{ _('') }}` to the needing change words.

```html
<div class="title">{{ _('System Management') }}</div>
```

#### 使用語言包

* 首次使用

    1. 將所有 python 及 html 所用到的字串頡取出來：
        ```sh
        pybabel extract -F app/babel.cfg -o messages.pot .
        ```

    2. 建立字典檔 (儲放於 `app/translations` 下)：
        ```sh
        pybabel init -i messages.pot -d app/translations/ -l <lang_code>
        ```

    3. 翻譯文字，修改前一步產生的 po 檔，翻譯對應語系的文字，檔案路徑為：
        ```sh
        app/translations/<lang_code>/LC_MESSAGES/messages.po
        ```

    4. 編譯字典 po 檔成 mo 檔，供 babel 使用：
        ```sh
        pybabel compile -f -d app/translations
        ```

* 更新字典檔 (與首次使用相同，差別在於第二步的 update 用 `update` 取代 `init`)

    1. 將所有 python 及 html 所用到的字串頡取出來：
        ```sh
        pybabel extract -F app/babel.cfg -o messages.pot .
        ```

    2. 更新字典檔：
        ```sh
        pybabel update -i messages.pot -d app/translations/ -l <lang_code>
        ```

    3. 翻譯文字，修改前一步產生的 po 檔，翻譯對應語系的文字，檔案路徑為：
        ```sh
        app/translations/<lang_code>/LC_MESSAGES/messages.po
        ```

    4. 編譯字典 po 檔成 mo 檔，供 babel 使用：
        ```sh
        pybabel compile -f -d app/translations
        ```

* [詳細安裝說明](https://hackmd.io/5LqVk4MBSCinRXQderD_Jw) (此文件已久未更新，僅供參考)



#### **備註**
Python 3.11.6 安裝方式:
```
wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz
sudo apt update
sudo -H apt-get install libsqlite3-dev libffi-dev libssl-dev openssl zlib1g-dev build-essential -y
tar xzvf Python-3.11.6.tgz
cd Python-3.11.6
./configure --prefix=/usr/local
make -j
sudo make install
cd ..
```
