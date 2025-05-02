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
import logging
from abc import ABC, abstractmethod
from typing import Tuple

from playwright.async_api import Page
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

from constant import (BILIBILI_API_URL, BILIBILI_INDEX_URL,
                      BILIBILI_PLAYWRIGHT_SIGN, BILIBILI_PYTHON_SIGN,
                      ONE_MINUTE)
from context_vars import bilibili_manager_ctx_var
from logic.bilibili.help import BilibiliSign
from params.bilibili_sign import BilibliSignRequest, BilibliSignResponse
from pkg.async_http_client import AsyncHTTPClient
from pkg.cache.cache_factory import CacheFactory
from pkg.playwright.bilibili_manager import BilibiliPlaywrightManager
from pkg.utils import get_user_agent

logger = logging.getLogger(__name__)


class AbstractBilibiliSign(ABC):
    @abstractmethod
    async def sign(self, req_data: BilibliSignRequest, force_init: bool = False) -> BilibliSignResponse:
        raise NotImplementedError


class BilibiliPlaywrightSign(AbstractBilibiliSign):
    def __init__(self):
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    async def sign(self, req: BilibliSignRequest, force_init: bool = False) -> BilibliSignResponse:
        """
        Bilibili请求签名playwright版本, 如果发生异常默认重试3次，每次间隔500ms
        Args:
            req :
            force_init:

        Returns:

        """
        bilibili_browser_manager: BilibiliPlaywrightManager = bilibili_manager_ctx_var.get()
        if force_init:
            await bilibili_browser_manager.reload_page()

        page_obj: Page = bilibili_browser_manager.context_page
        local_storage = await page_obj.evaluate("() => window.localStorage")
        wbi_img_urls = local_storage.get("wbi_img_urls", "") or local_storage.get(
            "wbi_img_url") + "-" + local_storage.get("wbi_sub_url")

        if wbi_img_urls and "-" in wbi_img_urls:
            img_url, sub_url = wbi_img_urls.split("-")
            img_key = img_url.rsplit('/', 1)[1].split('.')[0]
            sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
            sign_result = BilibiliSign(img_key, sub_key).sign(req.req_data)
            return BilibliSignResponse(wts=sign_result.get("wts"), w_rid=sign_result.get("w_rid"))

        raise Exception("[BilibiliPlaywrightSign.sign] 获取wbi_img_urls失败")


class BilibiliPythonSign(AbstractBilibiliSign):
    def __init__(self):
        self._cache = CacheFactory.create_cache(cache_type="memory")
        self._defaut_cache_expire_time = ONE_MINUTE * 10

    async def _get_img_sub_key(self, req: BilibliSignRequest) -> Tuple[str, str]:
        """
        获取图片加密盐值
        Args:
            req:

        Returns:

        """
        uri = "/x/web-interface/nav"
        img_key = self._cache.get("bilibili_img_key")
        sub_key = self._cache.get("bilibili_sub_key")
        if not img_key or not sub_key:
            async with AsyncHTTPClient(BILIBILI_API_URL) as client:
                headers = {
                    "Cookie": req.cookies,
                    "User-Agent": get_user_agent(),
                    "Referer": BILIBILI_INDEX_URL
                }
                response = await client.get(uri, headers=headers)
                resp = response.json()
                if response.status_code == 200 and resp.get("code") == 0:
                    img_url: str = resp['data']['wbi_img']['img_url']
                    sub_url: str = resp['data']['wbi_img']['sub_url']
                    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
                    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
                    self._cache.set("bilibili_img_key", img_key, self._defaut_cache_expire_time)
                    self._cache.set("bilibili_sub_key", sub_key, self._defaut_cache_expire_time)
                else:
                    logger.error(f"[BilibiliPythonSign._get_img_sub_key] 获取图片加密失败, {response.text}")
                    raise Exception("获取图片加密失败")
        return img_key, sub_key

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
    async def sign(self, req: BilibliSignRequest, force_init: bool = False) -> BilibliSignResponse:
        """
        bilibi签名python版本, 如果发生异常默认重试3次，每次间隔500ms
        Args:
            req :
            force_init:

        Returns:

        """
        if force_init:
            # 如果重试了几次还是失败，使用固定值
            img_key = "7cd084941338484aae1ad9425b84077c"
            sub_key = "4932caff0ff746eab6f01bf08b70ac45"
        else:
            img_key, sub_key = await self._get_img_sub_key(req)
            if not img_key or not sub_key:
                raise Exception("获取图片加密失败")

        sign_result = BilibiliSign(img_key, sub_key).sign(req.req_data)
        return BilibliSignResponse(wts=sign_result.get("wts"), w_rid=sign_result.get("w_rid"))


class BilibiliSignFactory:
    @staticmethod
    def get_sign(sign_type: str) -> AbstractBilibiliSign:
        if sign_type == BILIBILI_PLAYWRIGHT_SIGN:
            return BilibiliPlaywrightSign()
        elif sign_type == BILIBILI_PYTHON_SIGN:
            return BilibiliPythonSign()
        else:
            raise NotImplementedError


class BilibiliSignLogic:
    def __init__(self, sign_type: str):
        """
        初始化
        :param sign_type:
        """
        self.sign_server = BilibiliSignFactory.get_sign(sign_type)

    async def sign(self, req_data: BilibliSignRequest) -> BilibliSignResponse:
        """
        签名
        :param req_data:
        :return:
        """
        try:
            return await self.sign_server.sign(req_data)
        except RetryError:
            return await self.sign_server.sign(req_data, force_init=True)
