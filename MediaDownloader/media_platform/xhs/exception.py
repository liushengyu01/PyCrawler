# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# copy from https://github.com/ReaJason/xhs/blob/master/xhs/exception.py
# modify by Relakkes
from enum import Enum
from typing import NamedTuple

from httpx import RequestError


class ErrorTuple(NamedTuple):
    code: int
    msg: str


class ErrorEnum(Enum):
    IP_BLOCK = ErrorTuple(300012, "网络连接异常，请检查网络设置或重启试试")
    NOTE_ABNORMAL = ErrorTuple(-510001, "笔记状态异常，请稍后查看")
    NOTE_SECRETE_FAULT = ErrorTuple(-510001, "当前内容无法展示")
    SIGN_FAULT = ErrorTuple(300015, "浏览器异常，请尝试关闭/卸载风险插件或重启试试！")
    SESSION_EXPIRED = ErrorTuple(-100, "登录已过期")
    ACCEESS_FREQUENCY_ERROR= ErrorTuple(300013, "访问频次异常，请勿频繁操作或重启试试")


class DataFetchError(RequestError):
    """something error when fetch"""


class IPBlockError(RequestError):
    """fetch so fast that the server block us ip"""


class SignError(RequestError):
    """fetch error because x-s sign verror"""


class AccessFrequencyError(RequestError):
    """
    fetch error because access frequency
    """

class NeedVerifyError(RequestError):
    """fetch error because need captcha"""

    def __init__(self, *args, **kwargs):
        self.verify_type = kwargs.pop("verify_type", None)
        self.verify_uuid = kwargs.pop("verify_uuid", None)
        super().__init__(*args, **kwargs)