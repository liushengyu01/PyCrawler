import hashlib
import execjs
import json
import requests
from typing import Dict, Optional

with open("./xhs_xs.js", "r", encoding="utf-8") as f:
    xs_js_code = f.read()

with open("./xhs_xmns.js", "r", encoding="utf-8") as f:
    xms_js_code = f.read()

xs_ctx = execjs.compile(xs_js_code)
xms_ctx = execjs.compile(xms_js_code)
cookies = "loadts=1742980395681;xsecappid=xhs-pc-web;x-user-id-creator.xiaohongshu.com=66e295f9000000001d0331b8;websectiga=29098a4cf41f76ee3f8db19051aaa60c0fc7c5e305572fec762da32d457d76ae;webBuild=4.61.1;sec_poison_id=ad6abccf-acd4-4480-aaaf-4f7b396e00a7;web_session=040069b5e1e37c6e09cfa2abd6354b5d627a1a;gid=yjyYdyW0K2i0yjyYdyW08yDDjjCKuMW6A9Ck2qW1hDdh62q82IhkED888yyY4y48YfY2WiJY;a1=1918e17a099x6zs7mqtxglvbevm5nvgwf155bbb3730000118414;abRequestId=40fd704f-5221-5d64-812c-25ebc80a8b3c;customerClientId=981287762407495;unread={%22ub%22:%2267e1197e000000001c007ead%22%2C%22ue%22:%2267e38e7e000000001d01fb60%22%2C%22uc%22:28};webId=273e57b8dea0cd6e98e6263baede6615"


base_url = "https://edith.xiaohongshu.com"
headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Cookie": cookies,
    "origin": "https://www.xiaohongshu.com",
    "referer": "https://www.xiaohongshu.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}

def make_md5_paramsd(api: str, data: Optional[Dict]):
    data_json_str = ""
    if data and isinstance(data, dict):
        data_json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    "".join([api, data_json_str])
    return hashlib.md5(data_json_str.encode()).hexdigest()

def get_homefeed():
    api = "/api/sns/web/v1/homefeed"
    data = {
        "cursor_score": "",
        "num": 30,
        "refresh_type": 1,
        "note_index": 35,
        "unread_begin_note_id": "",
        "unread_end_note_id": "",
        "unread_note_count": 0,
        "category": "homefeed_recommend",
        "search_key": "",
        "need_num": 15,
        "image_formats": ["jpg", "webp", "avif"],
        "need_filter_image": False,
    }
    xs_sign = xs_ctx.call("sign", api, data, cookies)
    xmns_params = xms_ctx.call("window.getMnsToken", api, data, make_md5_paramsd(api, data))
    headers["X-S"] = xs_sign["x-s"]
    headers["X-T"] = str(xs_sign["x-t"])
    headers["X-S-Common"] = xs_sign["x-s-common"]
    headers["x-b3-traceid"] = xs_sign["x-b3-traceid"]
    headers["X-Mns"] = xmns_params
    print(headers)
    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    response = requests.post(base_url + api, data=json_str, headers=headers)
    print(response.status_code)
    print(response.text)


def search_note_by_keyword(keyword):
    api = "/api/sns/web/v1/search/notes"
    data = {
        "keyword": "python",
        "page": 2,
        "page_size": 20,
        "search_id": "2el8d27lizyt79mkvrxy0",
        "sort": "general",
        "note_type": 0,
        "ext_flags": [],
        "geo": "",
        "image_formats": ["jpg", "webp", "avif"],
    }
    xs_sign = xs_ctx.call("sign", api, data, cookies)
    xmns_params = xms_ctx.call("window.getMnsToken", api, data, make_md5_paramsd(api, data))
    headers["X-S"] = xs_sign["x-s"]
    headers["X-T"] = str(xs_sign["x-t"])
    headers["X-S-Common"] = xs_sign["x-s-common"]
    headers["x-b3-traceid"] = xs_sign["x-b3-traceid"]
    headers["X-Mns"] = xmns_params
    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    response = requests.post(base_url + api, data=json_str, headers=headers)
    print(response.status_code)
    print(response.text)


def get_note_detail(note_id, xsec_token):
    api = "/api/sns/web/v1/feed"
    data = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": "1"},
        "xsec_source": "pc_search",
        "xsec_token": xsec_token,
    }
    xs_sign = xs_ctx.call("sign", api, data, cookies)
    xmns_params = xms_ctx.call("window.getMnsToken", api, data, make_md5_paramsd(api, data))
    headers["X-S"] = xs_sign["x-s"]
    headers["X-T"] = str(xs_sign["x-t"])
    headers["X-S-Common"] = xs_sign["x-s-common"]
    headers["x-b3-traceid"] = xs_sign["x-b3-traceid"]
    headers["X-Mns"] = xmns_params
    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    response = requests.post(base_url + api, data=json_str, headers=headers)
    print(response.status_code)
    print(response.text)


def get_note_comment_list(note_id, xsec_token):
    api = "/api/sns/web/v2/comment/page?note_id=67d92f09000000000302aa7d&cursor=67e1b585000000001f00850a&top_comment_id=&image_formats=jpg,webp,avif&xsec_token=ABGFPMh2PUw-5b-akbHua7P8m6YhazGeQPfKg1RF2ZKHA%3D"
    xs_sign = xs_ctx.call("sign", api, None, cookies)
    xmns_params = xms_ctx.call("window.getMnsToken", api, None, make_md5_paramsd(api, None))
    headers["X-S"] = xs_sign["x-s"]
    headers["X-T"] = str(xs_sign["x-t"])
    headers["X-S-Common"] = xs_sign["x-s-common"]
    headers["x-b3-traceid"] = xs_sign["x-b3-traceid"]
    headers["X-Mns"] = xmns_params
    response = requests.get(base_url + api, headers=headers)
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    get_homefeed()
    # search_note_by_keyword("python")
    # get_note_detail(
    #     "67de2105000000001d039299", "ABRL68IUEAkcczJn0ThHjYAcJtdbzSCLEYpk75GShlUo0="
    # )
    # get_note_comment_list(
    #     "67d92f09000000000302aa7d", "ABGFPMh2PUw-5b-akbHua7P8m6YhazGeQPfKg1RF2ZKHA="
    # )
