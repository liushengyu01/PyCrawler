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
from playwright.async_api import Page
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from constant import DOUYIN_JAVASCRIPT_SIGN, DOUYIN_PLAYWRIGHT_SIGN
from context_vars import dy_manager_ctx_var
from params.douyin_sign import DouyinSignRequest, DouyinSignResponse
from pkg.playwright.douyin_manager import DouYinPlaywrightManager


class AbstractDouyinSign(ABC):
    @abstractmethod
    async def sign(self, req_data: DouyinSignRequest, force_init: bool = False) -> DouyinSignResponse:
        raise NotImplementedError


class DouyinPlaywrightSign(AbstractDouyinSign):
    def __init__(self):
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    async def sign(self, req: DouyinSignRequest, force_init: bool = False) -> DouyinSignResponse:
        """
        抖音请求签名playwright版本, 如果发生异常默认重试3次，每次间隔500ms
        Args:
            req :
            force_init:

        Returns:

        """
        dy_browser_manager: DouYinPlaywrightManager = dy_manager_ctx_var.get()
        if force_init:
            await dy_browser_manager.reload_page()

        page_obj: Page = dy_browser_manager.context_page

        if req.uri.index("/reply") != -1:
            a_bogus = await page_obj.evaluate(
                "([params, post_data, ua]) => window.bdms.init._v[2].p[42].apply(null, [0, 1, 8, params, post_data, ua])",
                [req.query_params, "", req.user_agent]
            )
        else:
            a_bogus = await page_obj.evaluate(
                "([params, post_data, ua]) => window.bdms.init._v[2].p[42].apply(null, [0, 1, 14, params, post_data, ua])",
                [req.query_params, "", req.user_agent]
            )

        return DouyinSignResponse(a_bogus=a_bogus)


class DouyinJavascriptSign(AbstractDouyinSign):
    def __init__(self):
        self.douyin_sign_obj = execjs.compile(open('pkg/js/douyin.js', encoding='utf-8').read())

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    async def sign(self, req: DouyinSignRequest, force_init: bool = False) -> DouyinSignResponse:
        """
        抖音请求签名js版本, 如果发生异常默认重试3次，每次间隔500ms
        Args:
            req :
            force_init:

        Returns:

        """

        sign_js_name = "sign_datail"
        if "/reply" in req.uri:
            sign_js_name = "sign_reply"
        a_bogus = self.douyin_sign_obj.call(sign_js_name, req.query_params, req.user_agent)
        return DouyinSignResponse(a_bogus=a_bogus)


class DouyinSignFactory:
    @staticmethod
    def get_sign(sign_type: str) -> AbstractDouyinSign:
        if sign_type == DOUYIN_PLAYWRIGHT_SIGN:
            return DouyinPlaywrightSign()
        elif sign_type == DOUYIN_JAVASCRIPT_SIGN:
            return DouyinJavascriptSign()
        else:
            raise NotImplementedError


class DouyinSignLogic:
    def __init__(self, sign_type: str):
        """
        初始化
        :param sign_type:
        """
        self.sign_server = DouyinSignFactory.get_sign(sign_type)

    async def sign(self, req_data: DouyinSignRequest) -> DouyinSignResponse:
        """
        签名
        :param req_data:
        :return:
        """
        try:
            return await self.sign_server.sign(req_data)
        except RetryError:
            return await self.sign_server.sign(req_data, force_init=True)
