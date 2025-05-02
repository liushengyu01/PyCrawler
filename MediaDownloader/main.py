# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import sys
from typing import Dict, Optional, Type

import cmd_arg
import config
import constant
import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaiShouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler
from media_platform.zhihu import ZhihuCrawler
from constant import MYSQL_ACCOUNT_SAVE


class CrawlerFactory:
    CRAWLERS: Dict[str, AbstractCrawler] = {
        constant.XHS_PLATFORM_NAME: XiaoHongShuCrawler,
        constant.WEIBO_PLATFORM_NAME: WeiboCrawler,
        constant.TIEBA_PLATFORM_NAME: TieBaCrawler,
        constant.BILIBILI_PLATFORM_NAME: BilibiliCrawler,
        constant.DOUYIN_PLATFORM_NAME: DouYinCrawler,
        constant.KUAISHOU_PLATFORM_NAME: KuaiShouCrawler,
        constant.ZHIHU_PLATFORM_NAME: ZhihuCrawler,
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        """
        Create a crawler instance by platform
        Args:
            platform:

        Returns:

        """
        crawler_class: Optional[Type[AbstractCrawler]] = CrawlerFactory.CRAWLERS.get(
            platform
        )
        if not crawler_class:
            raise ValueError(
                "Invalid Media Platform Currently only supported xhs or dy or ks or bili ..."
            )
        return crawler_class()


async def main():
    print(
        """
# ⚠️声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# ⚠️1. 不得用于任何商业用途。  
# ⚠️2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# ⚠️3. 不得进行大规模爬取或对平台造成运营干扰。  
# ⚠️4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# ⚠️5. 不得用于任何非法或不当的用途。
# ⚠️  
# ⚠️详细许可条款请参阅项目根目录下的LICENSE文件。  
# ⚠️使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。
"""
    )

    # parse cmd
    cmd_arg.parse_cmd()

    # store or read using database, init db
    if config.SAVE_DATA_OPTION == "db" or config.ACCOUNT_POOL_SAVE_TYPE in [
        MYSQL_ACCOUNT_SAVE
    ]:
        await db.init_db()

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.async_initialize()
    await crawler.start()

    # store or read using database, close db
    if config.SAVE_DATA_OPTION == "db" or config.ACCOUNT_POOL_SAVE_TYPE in [
        MYSQL_ACCOUNT_SAVE
    ]:
        await db.close()


if __name__ == "__main__":
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
