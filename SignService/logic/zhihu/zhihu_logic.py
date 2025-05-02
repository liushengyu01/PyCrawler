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

from abc import ABC, abstractmethod

import execjs
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from constant import ZHIHU_JAVASCRIPT_SIGN
from params.zhihu_sign import ZhihuSignRequest, ZhihuSignResponse


class AbstractZhihuSign(ABC):
    @abstractmethod
    async def sign(self, req_data: ZhihuSignRequest) -> ZhihuSignResponse:
        raise NotImplementedError


class ZhihuJavascriptSign(AbstractZhihuSign):
    def __init__(self):
        self.xhs_sign_obj = execjs.compile(open('pkg/js/zhihu.js', encoding='utf-8').read())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    async def sign(self, req: ZhihuSignRequest) -> ZhihuSignResponse:
        """
        zhihu请求签名, js纯算版本
        :param req:
        :return:
        """
        sign_reslut = self.xhs_sign_obj.call("get_sign", req.uri, req.cookies)
        return ZhihuSignResponse(
            x_zst_81=sign_reslut.get("x-zst-81"),
            x_zse_96=sign_reslut.get("x-zse-96"),
        )


class ZhihuSignFactory:
    @staticmethod
    def get_sign(sign_type: str) -> AbstractZhihuSign:
        if sign_type == ZHIHU_JAVASCRIPT_SIGN:
            return ZhihuJavascriptSign()
        else:
            raise NotImplementedError


class ZhihuSignLogic:
    def __init__(self, sign_type: str):
        """
        初始化
        :param sign_type:
        """
        self.sign_server = ZhihuSignFactory.get_sign(sign_type)

    async def sign(self, req_data: ZhihuSignRequest) -> ZhihuSignResponse:
        """
        签名
        :param req_data:
        :return:
        """
        try:
            return await self.sign_server.sign(req_data)
        except RetryError:
            return await self.sign_server.sign(req_data)
