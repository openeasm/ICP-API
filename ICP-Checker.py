import base64
import hashlib
import json
import time
import uuid
from urllib import parse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask import Flask, request, jsonify
from flask_caching import Cache

from crack import Crack, generate_pointjson, checkImage

app = Flask(__name__)
cache = Cache(config={'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': '/tmp/icp_app_cache'})
cache.init_app(app)

crack = Crack()


def aes_ecb_encrypt(plaintext: bytes, key: bytes, block_size=16):
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key.encode()), modes.ECB(), backend=backend)
    padding_length = block_size - (len(plaintext) % block_size)
    padded = plaintext + bytes([padding_length]) * padding_length
    return base64.b64encode(cipher.encryptor().update(padded) + cipher.encryptor().finalize()).decode('utf-8')


def auth():
    t = str(round(time.time()))
    data = {
        "authKey": hashlib.md5(("testtest" + t).encode()).hexdigest(),
        "timeStamp": t
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://beian.miit.gov.cn/",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth",
                             headers=headers, data=parse.urlencode(data)).json()
        return resp["params"]["bussiness"]
    except Exception as e:
        print(f"auth error: {e}")
        return -1


def getImage(token):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://beian.miit.gov.cn/",
        "Token": token
    }
    payload = {
        "clientUid": "point-" + str(uuid.uuid4())
    }
    try:
        resp = requests.post("https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImagePoint",
                             headers=headers, json=payload).json()
        return resp["params"], payload["clientUid"]
    except Exception as e:
        print(f"getImage error: {e}")
        return -1, None


def query(sign, uuid_token, domain, token):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://beian.miit.gov.cn/",
        "Token": token,
        "Sign": sign,
        "Uuid": uuid_token,
        "Content-Type": "application/json",
        "Cookie": "__jsluid_s=" + str(uuid.uuid4().hex[:32])
    }
    data = {
        "pageNum": "",
        "pageSize": "40",
        "unitName": domain,
        "serviceType": 1
    }
    domain_list = []
    info_url = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition"
    try:
        beian_info = requests.post(info_url, headers=headers, data=json.dumps(data).replace(" ", "")).json()
        domain_total = beian_info['params']['total']
        page_total = beian_info['params']['lastPage']
        end_row = beian_info['params']['endRow']
        print("total_page:", page_total)
        for i in range(0, page_total):
            print(f"正在查询第{i + 1}页……\n")
            for k in range(0, end_row + 1):
                info_base = beian_info['params']['list'][k]
                domain_name = info_base['domain']
                domain_type = info_base['natureName']
                domain_licence = info_base['mainLicence']
                website_licence = info_base['serviceLicence']
                domain_status = info_base['limitAccess']
                domain_approve_date = info_base['updateRecordTime']
                domain_owner = info_base['unitName']
                try:
                    domain_content_approved = info_base['contentTypeName']
                    if domain_content_approved == "":
                        domain_content_approved = "无"
                except KeyError:
                    domain_content_approved = "无"
                row_data = domain_owner, domain_name, domain_licence, website_licence, domain_type, domain_content_approved, domain_status, domain_approve_date
                domain_list.append(row_data)
            data = {'pageNum': i + 2, 'pageSize': '40', 'unitName': domain, 'serviceType': 1}
            if beian_info['params']['isLastPage'] is True:
                break
            else:
                resp = requests.post(info_url, data=json.dumps(data).replace(" ", ""), headers=headers)
                print(resp.text)
                beian_info = resp.json()
                end_row = beian_info['params']['endRow']
                time.sleep(3)
    except Exception as e:
        print(f"query error: {e}")
        return {"code": 500, "msg": "查询出错"}
    else:
        domain_list = [dict(
            zip(['domain_owner', 'domain_name', 'domain_licence', 'website_licence', 'domain_type',
                 'domain_content_approved', 'domain_status', 'domain_approve_date'], row)) for row in
            domain_list]
        return {"code": 200, "msg": "success", "data": domain_list, "total": domain_total}


@app.route('/')
def index():
    return "请访问 /query/<域名> 查询备案信息"


@app.route('/query/<item>')
def main(item):
    if cache.get(item) is not None and not request.args.get('no_cache'):
        data = json.loads(cache.get(item))
        data['cached'] = True
        return jsonify(data)
    if cache.get('sign_info'):
        sign = json.loads(cache.get('sign_info'))
        sign, uuid_, token = sign['sign'], sign['uuid'], sign['token']
        try:
            print("使用缓存的密钥查询")
            rtn_value = query(sign, uuid_, item, token)
            print("使用缓存的密钥查询成功")
            return jsonify(rtn_value)
        except Exception as e:
            cache.delete('sign_info')
    token = auth()
    if token == -1:
        raise Exception("获取Token失败")
    params, clientUid = getImage(token)
    if params == -1:
        raise Exception("获取图形验证码失败")
    pointjson = generate_pointjson(params["bigImage"], params["smallImage"], params["secretKey"])
    print("point_json is ", pointjson)
    # uuid_token, secretKey, clientUid, pointJson
    sign = checkImage(params["uuid"], params["secretKey"], clientUid, pointjson, token)
    if sign == -1:
        raise Exception("图形验证码识别失败")
    result = query(sign, params["uuid"], item, token)
    sign = json.dumps({'sign': sign, 'uuid': params["uuid"], 'token': token})
    cache.set('sign_info', sign, timeout=60 * 60 * 5)
    return jsonify(result)


if __name__ == '__main__':
    app.json.ensure_ascii = False
    app.run(host='0.0.0.0', port=5001)
