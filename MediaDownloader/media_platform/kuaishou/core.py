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
from typing import Dict, List, Optional

import config
import constant
from base.base_crawler import AbstractCrawler
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from pkg.tools import utils
from pkg.tools.downloader import MediaDownloader
from repo.platform_save_data import kuaishou as kuaishou_store
from var import crawler_type_var, source_keyword_var

from .client import KuaiShouApiClient
from .exception import DataFetchError


class KuaiShouCrawler(AbstractCrawler):
    def __init__(self):
        self.ks_client = KuaiShouApiClient()
        self.downloader = MediaDownloader()

    async def async_initialize(self):
        """
        Asynchronous Initialization
        Returns:

        """
        utils.logger.info(
            "[KuaiShouCrawler.async_initialize] Begin async initialize"
        )

        # 账号池和IP池的初始化
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # 快手对代理验证还行，可以选择长时长的IP，比如30分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为30分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )

        # 初始化账号池
        account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.KUAISHOU_PLATFORM_NAME,
            account_save_type=config.ACCOUNT_POOL_SAVE_TYPE,
            proxy_ip_pool=proxy_ip_pool,
        )
        await account_with_ip_pool.async_initialize()

        self.ks_client.account_with_ip_pool = account_with_ip_pool
        await self.ks_client.update_account_info()

        # 设置爬虫类型
        crawler_type_var.set(config.CRAWLER_TYPE)

    async def start(self):
        """
        Start the crawler
        Returns:

        """
        if config.CRAWLER_TYPE == "search":
            # Search for videos and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_videos()
        elif config.CRAWLER_TYPE == "creator":
            # Get creator's information and their videos and comments
            await self.get_creators_and_videos()
        else:
            pass

        utils.logger.info("[KuaiShouCrawler.start] Kuaishou Crawler finished ...")

    async def search(self):
        """
        Search for videos and retrieve their comment information.
        Returns:

        """
        utils.logger.info("[KuaiShouCrawler.search] Begin search kuaishou keywords")
        ks_limit_count = 20  # kuaishou limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < ks_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = ks_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            search_session_id = ""
            utils.logger.info(
                f"[KuaiShouCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            while (
                page - start_page + 1
            ) * ks_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[KuaiShouCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                utils.logger.info(
                    f"[KuaiShouCrawler.search] search kuaishou keyword: {keyword}, page: {page}"
                )
                video_id_list: List[str] = []
                videos_res = await self.ks_client.search_info_by_keyword(
                    keyword=keyword,
                    pcursor=str(page),
                    search_session_id=search_session_id,
                )
                if not videos_res:
                    utils.logger.error(
                        f"[KuaiShouCrawler.search] search info by keyword:{keyword} not found data"
                    )
                    continue

                vision_search_photo: Dict = videos_res.get("visionSearchPhoto")
                if vision_search_photo.get("result") != 1:
                    utils.logger.error(
                        f"[KuaiShouCrawler.search] search info by keyword:{keyword} not found data "
                    )
                    continue
                search_session_id = vision_search_photo.get("searchSessionId", "")
                for video_detail in vision_search_photo.get("feeds"):
                    video_id_list.append(video_detail.get("photo", {}).get("id"))
                    await kuaishou_store.update_kuaishou_video(video_item=video_detail)
                    
                    # Download media content if available
                    if config.DOWNLOAD_MEDIA:
                        photo_info = video_detail.get("photo", {})
                        if config.DOWNLOAD_VIDEO and photo_info.get("photoUrl"):
                            await self.download_media_content(photo_info.get("photoUrl"), "video")
                        if config.DOWNLOAD_IMAGE and photo_info.get("coverUrl"):
                            await self.download_media_content(photo_info.get("coverUrl"), "image")

                # batch fetch video comments
                page += 1
                await self.batch_get_video_comments(video_id_list)

    async def get_specified_videos(self):
        """
        Get the information and comments of the specified post
        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(video_id=video_id, semaphore=semaphore)
            for video_id in config.KS_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await kuaishou_store.update_kuaishou_video(video_detail)
                
                # Download media content if available
                if config.DOWNLOAD_MEDIA:
                    photo_info = video_detail.get("photo", {})
                    if config.DOWNLOAD_VIDEO and photo_info.get("photoUrl"):
                        await self.download_media_content(photo_info.get("photoUrl"), "video")
                    if config.DOWNLOAD_IMAGE and photo_info.get("coverUrl"):
                        await self.download_media_content(photo_info.get("coverUrl"), "image")
                        
        await self.batch_get_video_comments(config.KS_SPECIFIED_ID_LIST)

    async def get_video_info_task(
        self, video_id: str, semaphore: asyncio.Semaphore
    ) -> Optional[Dict]:
        """
        Get video detail task
        Args:
            video_id:
            semaphore:

        Returns:

        """
        async with semaphore:
            try:
                result = await self.ks_client.get_video_info(video_id)
                utils.logger.info(
                    f"[KuaiShouCrawler.get_video_info_task] Get video_id:{video_id} info result: {result} ..."
                )
                return result.get("visionVideoDetail")
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaiShouCrawler.get_video_info_task] Get video detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[KuaiShouCrawler.get_video_info_task] have not fund video detail video_id:{video_id}, err: {ex}"
                )
                return None

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        Batch get video comments
        Args:
            video_id_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[KuaiShouCrawler.batch_get_video_comments] Crawling comment mode is not enabled"
            )
            return

        utils.logger.info(
            f"[KuaiShouCrawler.batch_get_video_comments] video ids:{video_id_list}"
        )
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(
                self.get_comments_async_task(video_id, semaphore), name=video_id
            )
            task_list.append(task)

        await asyncio.gather(*task_list)

    async def get_comments_async_task(
        self, video_id: str, semaphore: asyncio.Semaphore
    ):
        """
        Get comment for video id
        Args:
            video_id:
            semaphore:

        Returns:

        """
        async with semaphore:
            try:
                utils.logger.info(
                    f"[KuaiShouCrawler.get_comments_async_task] begin get video_id: {video_id} comments ..."
                )
                await self.ks_client.get_video_all_comments(
                    photo_id=video_id,
                    crawl_interval=random.random(),
                    callback=kuaishou_store.batch_update_ks_video_comments,
                )
            except DataFetchError as ex:
                utils.logger.error(
                    f"[KuaiShouCrawler.get_comments_async_task] get video_id: {video_id} comment error: {ex}"
                )
            except Exception as e:
                utils.logger.error(
                    f"[KuaiShouCrawler.get_comments_async_task] may be been blocked, err:{e}"
                )

    async def get_creators_and_videos(self) -> None:
        """
        Get creator's information and their videos and comments
        Returns:

        """
        utils.logger.info(
            "[KuaiShouCrawler.get_creators_and_videos] Begin get kuaishou creators"
        )
        for user_id in config.KS_CREATOR_ID_LIST:
            # get creator detail info from web html content
            createor_info: Dict = await self.ks_client.get_creator_info(user_id=user_id)
            if not createor_info:
                utils.logger.error(
                    f"[KuaiShouCrawler.get_creators_and_videos] get creator: {user_id} info error: {createor_info}"
                )
                continue

            await kuaishou_store.save_creator(user_id, creator=createor_info)
            # Get all video information of the creator
            all_video_list = await self.ks_client.get_all_videos_by_creator(
                user_id=user_id,
                crawl_interval=random.random(),
                callback=self.fetch_creator_video_detail,
            )

            video_ids = [
                video_item.get("photo", {}).get("id") for video_item in all_video_list
            ]
            await self.batch_get_video_comments(video_ids)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Fetch creator video detail
        Args:
            video_list:

        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(post_item.get("photo", {}).get("id"), semaphore)
            for post_item in video_list
        ]

        video_details = await asyncio.gather(*task_list)
        for video_detail in video_details:
            if video_detail is not None:
                await kuaishou_store.update_kuaishou_video(video_detail)
                
                # Download media content if available
                if config.DOWNLOAD_MEDIA:
                    photo_info = video_detail.get("photo", {})
                    if config.DOWNLOAD_VIDEO and photo_info.get("photoUrl"):
                        await self.download_media_content(photo_info.get("photoUrl"), "video")
                    if config.DOWNLOAD_IMAGE and photo_info.get("coverUrl"):
                        await self.download_media_content(photo_info.get("coverUrl"), "image")

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
            account_with_ip = await self.ks_client.account_with_ip_pool.get_account_with_ip_info()
            if not account_with_ip or not account_with_ip.account:
                utils.logger.error("[KuaiShouCrawler.download_media_content] No available account in pool")
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
                    f"[KuaiShouCrawler.download_media_content] Successfully downloaded {content_type} from {content_url}"
                )
                return True
            else:
                utils.logger.error(
                    f"[KuaiShouCrawler.download_media_content] Failed to download {content_type} from {content_url}"
                )
                return False
                
        except Exception as e:
            utils.logger.error(
                f"[KuaiShouCrawler.download_media_content] Error downloading {content_type} from {content_url}: {str(e)}"
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
            utils.logger.info(f"[KuaiShouCrawler.download_media_batch] Successfully downloaded {len(urls)} {content_type}s")
        except Exception as e:
            utils.logger.error(f"[KuaiShouCrawler.download_media_batch] Failed to download {content_type}s: {str(e)}")
