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
import asyncio
import logging
from typing import Optional

from playwright.async_api import Page, Playwright
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
import constant
from pkg import utils
from pkg.playwright.manager import PlaywrightManager

logger = logging.getLogger(__name__)


class DouYinPlaywrightManager(PlaywrightManager):
    def __init__(self, _async_playwright: Playwright):
        """
        Initialize
        :param _async_playwright:
        """
        super().__init__(constant.DOUYIN_PLATFORM_NAME, _async_playwright)
        self.context_page: Optional[Page] = None

    @retry(stop=stop_after_attempt(120), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_slider_captcha_exist(self) -> bool:
        """
        Check if the slider captcha exists
        :return:
        """
        current_page_content = await self.context_page.content()
        if "验证码中间页" in current_page_content:
            logger.info("[DouYinPlaywrightManager.check_slider_captcha_exist] 启动DY浏览器启动时出现验证码，请手动验证")
            return False
        return True

    async def load_page(self):
        """
        Initialize the page
        :return:
        """
        await self.init_browser_context()
        await self.add_fixed_cookies()
        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(constant.DOUYIN_INDEX_URL)
        await asyncio.sleep(constant.PLAYWRIGHT_INDEX_LOAD_TIME)
        try:
            await self.check_slider_captcha_exist()
            logger.info("[DouYinPlaywrightManager.load_page] Douyin浏览器启动成功，等待APP启动即可提供服务...")
        except RetryError:
            logger.info("[DouYinPlaywrightManager.load_page] Check slider captcha exist failed ...")
            raise RetryError

    async def add_fixed_cookies(self):
        """
        Add fixed cookies
        :return:
        """
        for key, value in utils.convert_str_cookie_to_dict(config.dy_fixed_cookie).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".douyin.com",
                'path': "/"
            }])

    async def reload_page(self):
        """
        Reload the page
        :return:
        """
        await self.reload_browser_context()
        await self.load_page()
