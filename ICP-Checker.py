# -*- coding: utf-8 -*-
import base64
import hashlib
import os
import re
import time
import uuid

import cv2
import requests
from flask import Flask, json, jsonify, request
from flask_caching import Cache

app = Flask(__name__)


os.environ['no_proxy'] = '*'

app.config['JSON_AS_ASCII'] = False
json.provider.DefaultJSONProvider.ensure_ascii = False


def query_base(info):
    # print("项目地址：https://github.com/wongzeon/ICP-Checker\n")
    while True:
        try:
            info = info.replace(" ", "").replace("https://www.", "").replace("http://www.", "").replace("http://", "")
            # 过滤空值和特殊字符，只允许 - . () 分别用于域名和公司名
            if info == "":
                raise ValueError("InputNone")
            info = re.sub("[^\\u4e00-\\u9fa5-A-Za-z0-9,-.()（）]", "", info)
            input_zh = re.compile(u'[\u4e00-\u9fa5]')
            zh_match = input_zh.search(info)
            if zh_match:
                info_result = info
            else:
                # 检测是否为可备案的域名类型（类型同步日期2022/01/06）
                # TODO 部分特殊域名, 如51.la也能备案, 可能是特事特办
                input_url = re.compile(
                    r'([^.]+)(?:\.(?:GOV\.cn|ORG\.cn|AC\.cn|MIL\.cn|NET\.cn|EDU\.cn|COM\.cn|BJ\.cn|TJ\.cn|SH\.cn|CQ\.cn|HE\.cn|SX\.cn|NM\.cn|LN\.cn|JL\.cn|HL\.cn|JS\.cn|ZJ\.cn|AH\.cn|FJ\.cn|JX\.cn|SD\.cn|HA\.cn|HB\.cn|HN\.cn|GD\.cn|GX\.cn|HI\.cn|SC\.cn|GZ\.cn|YN\.cn|XZ\.cn|SN\.cn|GS\.cn|QH\.cn|NX\.cn|XJ\.cn|TW\.cn|HK\.cn|MO\.cn|cn|REN|WANG|CITIC|TOP|SOHU|XIN|COM|NET|CLUB|XYZ|VIP|SITE|SHOP|INK|INFO|MOBI|RED|PRO|KIM|LTD|GROUP|BIZ|AUTO|LINK|WORK|LAW|BEER|STORE|TECH|FUN|ONLINE|ART|DESIGN|WIKI|LOVE|CENTER|VIDEO|SOCIAL|TEAM|SHOW|COOL|ZONE|WORLD|TODAY|CITY|CHAT|COMPANY|LIVE|FUND|GOLD|PLUS|GURU|RUN|PUB|EMAIL|LIFE|CO|FASHION|FIT|LUXE|YOGA|BAIDU|CLOUD|HOST|SPACE|PRESS|WEBSITE|ARCHI|ASIA|BIO|BLACK|BLUE|GREEN|LOTTO|ORGANIC|PET|PINK|POKER|PROMO|SKI|VOTE|VOTO|ICU))',
                    flags=re.IGNORECASE)
                info_result = input_url.search(info)
                if info_result is None:
                    if info.split(".")[0] == "":
                        raise ValueError("OnlyDomainInput")
                    raise ValueError("ValidType")
                else:
                    info_result = info_result.group()
            info_data = {'pageNum': '1', 'pageSize': '40', 'unitName': info_result}
            return info_data
        except ValueError as e:
            if str(e) == 'InputNone' or str(e) == 'OnlyDomainInput':
                return ("\n ************** 请正确输入域名 **************\n")
            else:
                return ("\n*** 该域名不支持备案，请查阅：http://xn--fiq8ituh5mn9d1qbc28lu5dusc.xn--vuq861b/ ***\n")


def get_cookies():
    cookie_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32'}
    err_num = 0
    while err_num < 3:
        try:
            cookie = requests.utils.dict_from_cookiejar(requests.get('https://beian.miit.gov.cn/', headers=cookie_headers).cookies)['__jsluid_s']
            return cookie
        except:
            err_num += 1
            time.sleep(3)
    return -1


def get_token():
    timeStamp = round(time.time() * 1000)
    authSecret = 'testtest' + str(timeStamp)
    authKey = hashlib.md5(authSecret.encode(encoding='UTF-8')).hexdigest()
    auth_data = {'authKey': authKey, 'timeStamp': timeStamp}
    url = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth'
    try:
        t_response = requests.post(url=url, data=auth_data, headers=base_header).json()
        token = t_response['params']['bussiness']
    except:
        return -1
    return token


def get_check_pic(token):
    url = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/getCheckImage'
    base_header['Accept'] = 'application/json, text/plain, */*'
    base_header.update({'Content-Length': '0', 'token': token})
    try:
        p_request = requests.post(url=url, data='', headers=base_header).json()
        p_uuid = p_request['params']['uuid']
        big_image = p_request['params']['bigImage']
        small_image = p_request['params']['smallImage']
    except:
        return -1
    rand_str = uuid.uuid4().hex
    # 解码图片，写入并计算图片缺口位置
    with open('bigImage.jpg' + rand_str, 'wb') as f:
        f.write(base64.b64decode(big_image))
    with open('smallImage.jpg' + rand_str, 'wb') as f:
        f.write(base64.b64decode(small_image))
    background_image = cv2.imread('bigImage.jpg' + rand_str, cv2.COLOR_GRAY2RGB)
    fill_image = cv2.imread('smallImage.jpg' + rand_str, cv2.COLOR_GRAY2RGB)
    position_match = cv2.matchTemplate(background_image, fill_image, cv2.TM_CCOEFF_NORMED)
    max_loc = cv2.minMaxLoc(position_match)[3][0]
    mouse_length = max_loc + 1
    os.remove('bigImage.jpg' + rand_str)
    os.remove('smallImage.jpg' + rand_str)
    check_data = {'key': p_uuid, 'value': mouse_length}
    return check_data


def get_sign(check_data, token):
    check_url = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/image/checkImage'
    base_header.update({'Content-Length': '60', 'token': token, 'Content-Type': 'application/json'})
    try:
        pic_sign = requests.post(check_url, json=check_data, headers=base_header).json()
        sign = pic_sign['params']
    except:
        return -1
    return sign


def get_beian_info(info_data, p_uuid, token, sign):
    domain_list = []
    info_url = 'https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition'
    base_header.update({'Content-Length': '78', 'uuid': p_uuid, 'token': token, 'sign': sign})
    try:
        beian_info = requests.post(url=info_url, json=info_data, headers=base_header).json()
        if not beian_info["success"]:
            print(f'请求错误: CODE {beian_info["code"]} MSG {beian_info["msg"]}')
            return domain_list
        domain_total = beian_info['params']['total']
        page_total = beian_info['params']['lastPage']
        end_row = beian_info['params']['endRow']
        info = info_data['unitName']
        print(f"\n查询对象：{info} 共有 {domain_total} 个已备案域名\n")
        for i in range(0, page_total):
            print(f"正在查询第{i+1}页……\n")
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
            info_data = {'pageNum': i + 2, 'pageSize': '40', 'unitName': info}
            if beian_info['params']['isLastPage'] is True:
                break
            else:
                beian_info = requests.post(info_url, json=info_data, headers=base_header).json()
                end_row = beian_info['params']['endRow']
                time.sleep(3)
    except Exception as e:
        print(f"意外错误: {e}")
        return domain_list
    return domain_list


cookie = get_cookies()
cache = Cache(config={'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': '/tmp/icp_app_cache', })
cache.init_app(app)


@app.route('/query/<item>')
def main(item):
    info = query_base(item)
    if cache.get(item) is not None and not request.args.get('no_cache'):
        data = json.loads(cache.get(item))
        data['cached'] = True
        return jsonify(data)
    try:
        global base_header, cookie
        base_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36 Edg/101.0.1210.32',
            'Origin': 'https://beian.miit.gov.cn',
            'Referer': 'https://beian.miit.gov.cn/',
            'Cookie': f'__jsluid_s={cookie}'
        }
        # -1代表对应步骤失败了，不是-1则正常执行下一步
        if cookie != -1:
            token = get_token()
            if token != -1:
                check_data = get_check_pic(token)
                if check_data != -1:
                    sign = get_sign(check_data, token)
                    p_uuid = check_data['key']
                    if sign != -1:
                        domain_list = get_beian_info(info, p_uuid, token, sign)
                        """columns domain_owner, domain_name, domain_licence, website_licence, domain_type, domain_content_approved, domain_status, domain_approve_date"""
                        domain_list = [dict(
                            zip(['domain_owner', 'domain_name', 'domain_licence', 'website_licence', 'domain_type',
                                 'domain_content_approved', 'domain_status', 'domain_approve_date'], row)) for row in
                            domain_list]
                        rtn_value = {'code': 200, 'msg': 'success', 'data': domain_list}
                        cache.set(item, json.dumps(rtn_value), timeout=60 * 60 * 24)
                        return jsonify(rtn_value)
                    else:
                        raise ValueError("获取Sign遇到错误，请重试！")
                else:
                    raise ValueError("计算图片缺口位置错误，请重试！")
            else:
                raise ValueError("获取Token失败，如频繁失败请关闭程序后等待几分钟再试！")
        else:
            cookie = get_cookies()
            raise ValueError("获取Cookie失败，请重试！")
    except Exception as e:
        print(f'{e}\n')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
