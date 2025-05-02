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
import random
from asyncio import Task
from typing import Any, Dict, List, Optional

import config
import constant
from base.base_crawler import AbstractCrawler
from constant.douyin import DOUYIN_FIXED_USER_AGENT
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from pkg.tools import utils
from repo.platform_save_data import douyin as douyin_store
from repo.platform_save_data.douyin.douyin_store_sql import (
    get_all_creators_list,
    get_aweme_list_by_creator_id,
)
from var import crawler_type_var, source_keyword_var

from .client import DouYinApiClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import get_common_verify_params
from pkg.tools.downloader import MediaDownloader


class DouYinCrawler(AbstractCrawler):

    def __init__(self) -> None:
        self.dy_client = DouYinApiClient()
        self.downloader = MediaDownloader()

    async def async_initialize(self):
        """
        Asynchronous Initialization
        Returns:

        """
        utils.logger.info("[DouYinCrawler.async_initialize] Begin async initialize")
        self.dy_client.common_verfiy_params = await get_common_verify_params(
            DOUYIN_FIXED_USER_AGENT
        )

        # 账号池和IP池的初始化
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # dy对代理验证还行，可以选择长时长的IP，比如30分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为30分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )

        # 初始化账号池
        account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.DOUYIN_PLATFORM_NAME,
            account_save_type=config.ACCOUNT_POOL_SAVE_TYPE,
            proxy_ip_pool=proxy_ip_pool,
        )
        await account_with_ip_pool.async_initialize()

        self.dy_client.account_with_ip_pool = account_with_ip_pool
        await self.dy_client.update_account_info()

        # 设置爬虫类型
        crawler_type_var.set(config.CRAWLER_TYPE)

    async def start(self) -> None:
        """
        Start crawler
        Returns:

        """
        if config.CRAWLER_TYPE == "search":
            # Search for notes and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_awemes()
        elif config.CRAWLER_TYPE == "creator":
            # Get the information and comments of the specified creator
            await self.get_creators_and_videos()

        utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        """
        Search for video list and retrieve their comment information.
        Returns:

        """
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            page = 1
            dy_search_id = ""
            while (
                page - start_page + 1
            ) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    aweme_list: List[str] = []
                    utils.logger.info(
                        f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}"
                    )
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=(page - 1) * dy_limit_count,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )

                    page += 1
                    if "data" not in posts_res:
                        utils.logger.error(
                            f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。"
                        )
                        break
                    dy_search_id = posts_res.get("extra", {}).get("logid", "")
                    for post_item in posts_res.get("data"):
                        try:
                            aweme_info: Dict = (
                                post_item.get("aweme_info")
                                or post_item.get("aweme_mix_info", {}).get("mix_items")[
                                    0
                                ]
                            )
                        except TypeError:
                            continue
                        aweme_list.append(aweme_info.get("aweme_id", ""))
                        await douyin_store.update_douyin_aweme(aweme_item=aweme_info)
                        
                        # Download video content if available
                        if config.DOWNLOAD_MEDIA and config.DOWNLOAD_VIDEO:
                            video_url = aweme_info.get("video", {}).get("play_addr", {}).get("url_list", [])
                            if video_url:
                                await self.download_media_content(video_url[0], "video")

                    utils.logger.info(
                        f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}"
                    )
                    await self.batch_get_note_comments(aweme_list)

                except Exception as ex:
                    utils.logger.error(
                        f"[DouYinCrawler.search] Search videos error: {ex}"
                    )
                    # 发生异常了，则打印当前爬取的关键词和页码，用于后续继续爬取
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码------------------------------------------"
                    )
                    for i in range(10):
                        utils.logger.error(
                            f"[DouYinCrawler.search] Current keyword: {keyword}, page: {page}"
                        )
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------"
                    )
                    return

    async def get_specified_awemes(self):
        """
        Get the information and comments of the specified post
        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore)
            for aweme_id in config.DY_SPECIFIED_ID_LIST
        ]
        aweme_details = await asyncio.gather(*task_list)
        aweme_id_list = []
        for aweme_detail in aweme_details:
            if aweme_detail:
                aweme_id_list.append(aweme_detail.get("aweme_id"))
                await douyin_store.update_douyin_aweme(aweme_detail)
                
                # Download video content if available
                if config.DOWNLOAD_MEDIA and config.DOWNLOAD_VIDEO:
                    video_url = aweme_detail.get("video", {}).get("play_addr", {}).get("url_list", [])
                    if video_url:
                        await self.download_media_content(video_url[0], "video")

        await self.batch_get_note_comments(aweme_id_list)

    async def get_specified_awemes_only_comments_with_db_data(self):
        """
        获取指定创作者的视频列表，只获取评论
        Returns:

        """
        aweme_id_list = []
        creators_list = await get_all_creators_list()
        for creator in creators_list:
            aweme_list = await get_aweme_list_by_creator_id(creator.get("user_id"))
            for aweme in aweme_list:
                aweme_id_list.append(aweme.get("aweme_id"))
        await self.batch_get_note_comments(aweme_id_list)

    async def get_aweme_detail(
        self, aweme_id: str, semaphore: asyncio.Semaphore
    ) -> Any:
        """
        Get note detail
        Args:
            aweme_id:
            semaphore:

        Returns:

        """
        async with semaphore:
            try:
                return await self.dy_client.get_video_by_id(aweme_id)
            except DataFetchError as ex:
                utils.logger.error(
                    f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}"
                )
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled"
            )
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            utils.logger.info(
                f"[DouYinCrawler.batch_get_note_comments] aweme_id: {aweme_id}"
            )
            task = asyncio.create_task(
                self.get_comments_async_task(aweme_id, semaphore), name=aweme_id
            )
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments_async_task(
        self, aweme_id: str, semaphore: asyncio.Semaphore
    ) -> None:
        async with semaphore:
            try:
                # 将关键词列表传递给 get_aweme_all_comments 方法
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=random.random(),
                    callback=douyin_store.batch_update_dy_aweme_comments,
                )
                utils.logger.info(
                    f"[DouYinCrawler.get_comments_async_task] aweme_id: {aweme_id} comments have all been obtained and filtered ..."
                )
            except DataFetchError as e:
                utils.logger.error(
                    f"[DouYinCrawler.get_comments_async_task] aweme_id: {aweme_id} get comments failed, error: {e}"
                )

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator
        """
        utils.logger.info(
            "[DouYinCrawler.get_creators_and_videos] Begin get douyin creators"
        )
        for user_id in config.DY_CREATOR_ID_LIST:
            creator_info: Dict = await self.dy_client.get_user_info(user_id)
            if creator_info:
                await douyin_store.save_creator(user_id, creator=creator_info)

            # Get all video information of the creator
            all_video_list = await self.dy_client.get_all_user_aweme_posts(
                sec_user_id=user_id,
                callback=douyin_store.batch_update_douyin_aweme,
                max_count=config.CRAWLER_MAX_NOTES_COUNT,
            )

            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Get the details of the specified post list concurrently
        Args:
            video_list:

        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_aweme_detail(post_item.get("aweme_id"), semaphore)
            for post_item in video_list
        ]

        video_details = await asyncio.gather(*task_list)
        for aweme_item in video_details:
            if aweme_item:
                await douyin_store.update_douyin_aweme(aweme_item)
                
                # Download video content if available
                if config.DOWNLOAD_MEDIA and config.DOWNLOAD_VIDEO:
                    video_url = aweme_item.get("video", {}).get("play_addr", {}).get("url_list", [])
                    if video_url:
                        await self.download_media_content(video_url[0], "video")

    async def download_media_content(self, content_url: str, content_type: str = None) -> bool:
        """
        Download media content
        
        Args:
            content_url: Content URL
            content_type: Content type (video/image)
            
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            # Get a fresh account from the pool
            account_with_ip = await self.dy_client.account_with_ip_pool.get_account_with_ip_info()
            if not account_with_ip or not account_with_ip.account:
                utils.logger.error("[DouYinCrawler.download_media_content] No available account in pool")
                return False
                
            cookies = account_with_ip.account.cookies
            
            # Download content with cookies
            filepath = await self.downloader.download_content(
                content_url=content_url,
                content_type=content_type,
                cookies=cookies
            )
            
            if filepath:
                utils.logger.info(
                    f"[DouYinCrawler.download_media_content] Successfully downloaded {content_type} from {content_url}"
                )
                return True
            else:
                utils.logger.error(
                    f"[DouYinCrawler.download_media_content] Failed to download {content_type} from {content_url}"
                )
                return False
                
        except Exception as e:
            utils.logger.error(
                f"[DouYinCrawler.download_media_content] Error downloading {content_type} from {content_url}: {str(e)}"
            )
            return False

    async def download_media_batch(self, urls: List[str], content_type: str) -> None:
        """
        Download multiple media contents in batch
        
        Args:
            urls: List of media content URLs
            content_type: Content type (video/image)
        """
        try:
            await self.downloader.download_batch(urls, content_type)
            utils.logger.info(f"[DouYinCrawler.download_media_batch] Successfully downloaded {len(urls)} {content_type}s")
        except Exception as e:
            utils.logger.error(f"[DouYinCrawler.download_media_batch] Failed to download {content_type}s: {str(e)}")
