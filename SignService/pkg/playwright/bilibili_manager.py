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

import config
import constant
from pkg import utils
from pkg.playwright.manager import PlaywrightManager

logger = logging.getLogger(__name__)


class BilibiliPlaywrightManager(PlaywrightManager):
    def __init__(self, _async_playwright: Playwright):
        """
        Initialize
        :param _async_playwright:
        """
        super().__init__(constant.BILIBILI_PLATFORM_NAME, _async_playwright)
        self.context_page: Optional[Page] = None

    async def load_page(self):
        """
        Initialize the page
        :return:
        """
        await self.init_browser_context()
        await self.add_fixed_cookies()
        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(constant.BILIBILI_INDEX_URL)
        await asyncio.sleep(constant.PLAYWRIGHT_INDEX_LOAD_TIME)
        logger.info("[BilibiliPlaywrightManager.load_page] Bilibili浏览器启动成功，等待APP启动即可提供服务...")
    async def add_fixed_cookies(self):
        """
        Add fixed cookies
        :return:
        """
        for key, value in utils.convert_str_cookie_to_dict(config.bilibili_fixed_cookie).items():
            await self.browser_context.add_cookies([{
                'name': key,
                'value': value,
                'domain': ".bilibili.com",
                'path': "/"
            }])

    async def reload_page(self):
        """
        Reload the page
        :return:
        """
        await self.reload_browser_context()
        await self.load_page()
