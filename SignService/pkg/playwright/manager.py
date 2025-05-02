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
import os
import shutil
from typing import Optional

from playwright.async_api import BrowserContext, Playwright

import config
from pkg import utils


class PlaywrightManager:
    """
    Playwright管理类
    """

    def __init__(self, platform_name: str, async_playwright: Playwright):
        """
        初始化
        :param platform_name: 平台名 constant.XHS_PLATFORM_NAME | constant.DOUYIN_PLATFORM_NAME
        :param async_playwright:
        """
        self.platfrom_name = platform_name
        self.async_playwright = async_playwright
        self.browser_context: Optional[BrowserContext] = None


    async def init_browser_context(self):
        """
        初始化浏览器
        :return:
        """
        self._remove_browser_data()
        user_data_dir = os.path.join(os.getcwd(), "browser_data", self.platfrom_name)
        stealth_js_path = os.path.join(os.getcwd(), "pkg/js/stealth.min.js")
        browser_context = await self.async_playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            accept_downloads=True,
            headless=config.playwright_headless,
            viewport={"width": 1920, "height": 1080},
            user_agent=utils.get_user_agent(),
        )
        await browser_context.add_init_script(path=stealth_js_path)
        self.browser_context = browser_context

    def _remove_browser_data(self):
        """
        删除浏览器数据
        :return:
        """
        user_data_dir = os.path.join(os.getcwd(), "browser_data", self.platfrom_name)
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

    async def reload_browser_context(self):
        """
        重新加载浏览器
        :return:
        """
        self._remove_browser_data()
        await self.init_browser_context()
