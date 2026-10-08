import requests
import json

import config

GUI_SERVER_URL = config.IOTTALK_GUI_URL.rstrip('/') + '/'
CCM_API_URL = GUI_SERVER_URL + "api/v0/"
CCM_URL = GUI_SERVER_URL + "api/v0"  # 不含結尾斜線，供 f"{CCM_URL}/..." 與 ccmapi 使用

def create_project(project_name: str):
    response = requests.put(CCM_API_URL + 'project/', json={"p_name": project_name}).json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res
    
def get_project(project_name: str):
    # 如果專案名稱是一串數字的話會變成以 p id 查詢，所以改用 get_project_by_name
    response = requests.get(CCM_API_URL + 'project/' + project_name + '/').json()
    print(CCM_API_URL + 'project/' + project_name + '/')
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def get_project_by_name(project_name: str):
    response = requests.get(CCM_API_URL + 'project/prj_name/' + project_name + '/').json()
    print(CCM_API_URL + 'project/prj_name/' + project_name + '/')
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_project(project_id: int):
    response = requests.delete(CCM_API_URL + 'project/' + str(project_id) + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def get_devicemodel(dm: str):
    response = requests.get(CCM_API_URL + 'devicemodel/' + dm + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res
    
def get_devicemodel_list():
    response = requests.get(CCM_API_URL + f"devicemodel/").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res


'''
def create_devicemodel(dm_info: str):
    # Request:
    #     {
    #         'dm_name': 'Foo',
    #         'df_list': [
    #             {
    #                 'df_id': 12,  // required
    #                 'df_parameter': [{}, ...]  // required
    #                 'tags': [],  // optional
    #             },
    #             ...
    #         ],
    #         'dm_type': 'other',  // optional
    #     }
    # Response:
    #     {
    #         'state': 'ok',
    #         'dm_id': 42,
    #     }
    # Response if name already exists with HTTP code 400:
    #     {
    #         'state': 'error',
    #         'reason': 'Device Model "..." already exists',
    
    #     }
    
    try:
        resp = requests.put(CCM_API_URL + 'devicemodel/', json=dm_info)
        if resp.status_code == 200:
            response = resp.json()
            status = response["state"] == "ok"
            res = response["dm_id"] if status else response["reason"]
            return status, res
        else:
            # 若不是 200，要避免直接 .json()
            return False, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, str(e)
    
    response = requests.put(CCM_API_URL + 'devicemodel/', json = dm_info).json()
    status = response["state"] =="ok"
    res = response["dm_id"] if status else response["reason"]
    return status, res
'''

def create_devicemodel(dm_info: dict):
    try:
        resp = requests.put(CCM_API_URL + 'devicemodel/', json=dm_info)
        try:
            response = resp.json()
        except Exception:
            return False, f"Invalid JSON Response: {resp.text}"

        if response.get("state") == "ok":
            return True, response.get("dm_id")
        else:
            return False, response.get("reason", "Unknown error")
    except Exception as e:
        return False, str(e)


def create_deviceobject(project_id: int, dm_id: int, df_ids: list[int]):
    # Request:
    #     {
    #         'dm_id': 42,  // Device Model id
    #         'df': [  // list of Device Feature id
    #             123,
    #             ...
    #         ],
    #     }
    # Response:
    #     {
    #         'state': 'ok',
    #         'do_id': [42, 57]
    #     }
    # Response error if Device Model or Device Feature not found:
    #     {
    #         'state': 'error',
    #         'reason': '... not found',
    #     }
    response = requests.put(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/', json={"dm_id": dm_id, "df": df_ids}).json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def get_deviceobject(project_id: int, do_id: int):
    # 不會取得 dfo_id
    # 會列出此 dm 中所有 df，再列出有使用的 df
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/' + str(do_id) + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_deviceobject(project_id: int, do_id: int):
    response = requests.delete(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/' + str(do_id) + '/').json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def create_networkapplication(project_id: int, input_dfo_id: int, output_dfo_id: int):
    dfo_ids = [input_dfo_id, output_dfo_id]
    status, na_list = get_networkapplication(project_id)
    n = len(na_list)
    data = {'na_name': 'Join {}'.format(n + 1), 'na_idx': n, 'dfo_ids': dfo_ids}
    response = requests.put(CCM_API_URL + "project/" + str(project_id) + '/na/', json=data).json()
    status = response["state"] =="ok"
    res = response["na_id"] if status else response["reason"]
    return status, res

def get_networkapplication(project_id: int):
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + '/na/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_networkapplication(project_id: int, na_id: int):
    response = requests.delete(CCM_API_URL + "project/" + str(project_id) + '/na/' + str(na_id) + '/').json()
    status = response["state"] =="ok"
    res = response if status else response["reason"]
    return status, res

def get_device(project_id: int, do_id: int):
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + "/deviceobject/" + str(do_id) + "/device").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def bind_device(project_id: int, do_id: int, d_id: int):
    response = requests.post(CCM_API_URL + f"project/{project_id}/deviceobject/{do_id}/device/bind/{d_id}/").json()
    status = response["state"] =="ok"
    res = response["d_name"] if status else response["reason"]
    return status, res

def unbind_device(project_id: int, do_id: int):
    response = requests.post(CCM_API_URL + f"project/{project_id}/deviceobject/{do_id}/device/unbind/").json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def get_devicefeature(devicefeature_name: str):
    response = requests.get(CCM_API_URL + f"devicefeature/{devicefeature_name}").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def get_devicefeature_list():
    response = requests.get(CCM_API_URL + f"devicefeature/").json()
    status = response["state"] =="ok"
    res = response if status else response["reason"]
    return status, res

def create_devicefeature(df_data: dict):
    url = CCM_API_URL + "devicefeature"
    try:
        response = requests.put(url, json=df_data)
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("state") == "ok":
                df_id = json_data["data"]["df_id"]
                return True, {"df_id": df_id}  # ✅ 改成 dict 格式
            else:
                return False, json_data.get("reason", "Unknown error")
        else:
            return False, f"HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return False, str(e)



def get_unit_list():
    response = requests.post(GUI_SERVER_URL + f"get_unit_list").json()
    return response

def get_device_list(p_id, do_id):
    payload = {
        "feature_info": json.dumps({
            "mount_info": {
                "device_feature_list": ["在 iottalk server 裡沒用到，但還是要有這個 key。詳細內容可看 iottalk-v1/lib/ccm/main.py 的 @app.route('/get_device_list')"],
                "do_id": do_id
            },
            "p_id": p_id
        })
    }
    response = requests.post(GUI_SERVER_URL + f"get_device_list", data=payload).json()
    return response
    
def update_devicemodel(payload):
    """
    更新指定 dm_id 的 device model，加入或更改 df_ids。

    payload 範例：
    {
        "dm_id": 123,
        "dfs": [1, 2, 3]
    }
    """
    url = f"{CCM_URL}/devicemodel/"
    try:
        response = requests.put(url, json=payload)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)


def get_devicemodel_by_name(dm_name):
    """
    根據 device model 名稱查詢對應資訊
    """
    try:
        url = f"{CCM_URL}/devicemodel/name/{dm_name}"
        response = requests.get(url)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)
        
        
def set_alias(mac_addr, df_name, alias_name):
    """
    安全地設定 DF 的 alias，避免因 ccmapi 回傳格式錯誤導致程式崩潰
    """
    url = f"{CCM_API_URL}alias/{mac_addr}/{df_name}"
    try:
        response = requests.post(url, json={"alias_name": alias_name})
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("state") == "ok":
                return True, json_data.get("data", {}).get("alias_name", alias_name)
            else:
                return False, json_data.get("reason", "Unknown error")
        else:
            return False, f"HTTP {response.status_code} - {response.text}"
    except Exception as e:
        return False, str(e)

# 在 ccm_utils.py 中加入：


from ccmapi.v0 import devicemodel, devicefeature

def replace_devicemodel(dm_name, df_ids):
    try:
        # 刪除舊 DM
        dm_info = devicemodel.get(dm_name)
        if dm_info and "dm_id" in dm_info:
            dm_id = dm_info["dm_id"]
            delete_success, _ = devicemodel.delete(dm_id)
            if delete_success:
                print(f"🗑 Deleted old DeviceModel '{dm_name}'")

        # 構建 df_list
        df_list = []
        for df_id in df_ids:
            df_info = devicefeature.get(df_id)
            if not df_info or "df_id" not in df_info:
                print(f"⚠️ Cannot find DF id={df_id}, skipping...")
                continue
            df_param = df_info.get("df_parameter", [])
            if not df_param:
                print(f"⚠️ DF id={df_id} has no df_parameter, skipping...")
                continue
            df_list.append({
                "df_id": df_info["df_id"],
                "df_parameter": df_param
            })

        if not df_list:
            raise Exception("❌ No valid DF with parameters to create new DeviceModel.")

        dm_payload = {
            "dm_name": dm_name,
            "dm_type": "other",
            "df_list": df_list,
        }

        success, result = create_devicemodel(dm_payload)
        if success:
            print(f"✅ Created DeviceModel '{dm_name}', dm_id={result}")
            return True, result
        else:
            print(f"[⚠️] Failed to create new DM: {result}")
            return False, str(result)

    except Exception as e:
        print(f"[❌] Exception in replace_devicemodel: {e}")
        return False, str(e)


