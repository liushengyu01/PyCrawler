# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
import hashlib
import json
import os
import time
import uuid
from random import Random
from typing import Union


def get_md5(bytes_content: Union[str, bytes]) -> str:
    """
    获取MD5值
    :param bytes_content:
    :return:
    """
    if type(bytes_content) == str:
        bytes_content = bytes_content.encode()
    md5obj = hashlib.md5()
    md5obj.update(bytes_content)
    hash_value = md5obj.hexdigest()
    return hash_value


def get_uuid_md5_value(default_len: int = 16) -> str:
    """
    根据UUID以及MD5生成一个唯一的识别码 16, 32位
    :param default_len: 默认长度
    :return:
    """
    if default_len == 16:
        return get_md5(uuid.uuid1().hex)[8:24]
    return get_md5(uuid.uuid1().hex)


def custom_getenv(key, default=None):
    """
    自定义环境变量获取函数，让环境变量中的数据能够转换成python这边的对象
    用法见单元测试：test/test_custom_getenv.py
    :param key:
    :param default:
    :return:
    """
    value = os.getenv(key, default)
    if value is not None:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
    return value


def get_random_str(random_len: int = 12) -> str:
    """
    获取随机字符串
    :param random_len:
    :return:
    """
    random_str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    length = len(chars) - 1
    random = Random()
    for i in range(random_len):
        random_str += chars[random.randint(0, length)]
    return random_str


def get_unix_timestamp():
    return int(time.time())