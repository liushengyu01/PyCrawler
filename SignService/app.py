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
import os
import sys

import tornado.web
from playwright.async_api import Playwright, async_playwright
from tornado.options import options

import config
import constant
import urls
from context_vars import (bilibili_manager_ctx_var, dy_manager_ctx_var,
                          request_id_var, xhs_manager_ctx_var)
from pkg.playwright.bilibili_manager import BilibiliPlaywrightManager
from pkg.playwright.douyin_manager import DouYinPlaywrightManager
from pkg.playwright.xhs_manager import XhsPlaywrightManager

logger = logging.getLogger(__name__)


def register_all_handlers(all_handlers):
    """
    注册路由
    :param all_handlers:
    :return:
    """
    all_handlers += urls.url_handlers


class Application(tornado.web.Application):
    all_handlers = []

    def __init__(self):
        register_all_handlers(Application.all_handlers)
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=config.IS_DEBUG,
            gzip=True,
            autoreload=False,
            user_cookie_name=config.user_cookie_name,
            login_url="/admin/login",
            xsrf_cookies=config.xsrf_cookies,
            cookie_secret=config.cookie_secret,
        )
        super(Application, self).__init__(Application.all_handlers, **settings)


class LoggerCustomFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get("-")
        return True


async def app_init():
    """
    程序启动前的初始化代码
    :return:
    """

    # 初始化logger，logger中包含了request id
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M:%S',
        level=config.logger_level,
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d req_id: %(request_id)s %(message)s",
    )
    log_filter = LoggerCustomFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(log_filter)

    # 将项目根目录添加到sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)


async def init_playwright_manager(playwright: Playwright):
    """
    初始化playwright manager
    :param playwright:
    :return:
    """
    logger.info("[init_playwright_manager] init playwright manager")
    xhs_playwright = XhsPlaywrightManager(playwright)
    douyin_playwright = DouYinPlaywrightManager(playwright)
    bilibili_playwright = BilibiliPlaywrightManager(playwright)
    await asyncio.gather(xhs_playwright.load_page(), douyin_playwright.load_page(), bilibili_playwright.load_page())
    xhs_manager_ctx_var.set(xhs_playwright)
    dy_manager_ctx_var.set(douyin_playwright)
    bilibili_manager_ctx_var.set(bilibili_playwright)


async def tornado_app():
    """
    创建tornado app
    :return:
    """
    await app_init()
    app = Application()
    app.listen(port=options.port, address=options.address)
    logger.info("app running at port %s", options.port)
    await asyncio.Event().wait()


async def create_app():
    if config.sign_type == constant.PLAYWRIGHT_SIGN_SERVER:
        logger.info("使用playwright签名服务")
        async with async_playwright() as playwright:
            logger.info("初始化前置依赖组件...")
            await app_init()
            await init_playwright_manager(playwright)

            await tornado_app()
    elif config.sign_type == constant.JAVASCRIPT_SIGN_SERVER:
        logger.info("使用js签名服务")
        await app_init()
        await tornado_app()
    else:
        logger.error("未知的签名服务类型")
        raise Exception("未知的签名服务类型")


if __name__ == '__main__':
    print("""
    # ⚠️声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
    # ⚠️1. 不得用于任何商业用途。  
    # ⚠️2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
    # ⚠️3. 不得进行大规模爬取或对平台造成运营干扰。  
    # ⚠️4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
    # ⚠️5. 不得用于任何非法或不当的用途。
    # ⚠️  
    # ⚠️详细许可条款请参阅项目根目录下的LICENSE文件。  
    # ⚠️使用本
    """)
    asyncio.run(create_app())
