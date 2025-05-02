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
from model.m_xiaohongshu import CreatorUrlInfo, NoteUrlInfo
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from pkg.tools import utils
from pkg.tools.downloader import MediaDownloader
from repo.platform_save_data import xhs as xhs_store
from var import crawler_type_var, source_keyword_var

from .client import XiaoHongShuClient
from .exception import DataFetchError
from .field import SearchSortType
from .help import parse_creator_info_from_creator_url, parse_note_info_from_note_url


class XiaoHongShuCrawler(AbstractCrawler):
    def __init__(self) -> None:
        self.xhs_client = XiaoHongShuClient()
        self.downloader = MediaDownloader()

    async def async_initialize(self):
        """
        Asynchronous Initialization
        Returns:

        """
        utils.logger.info(
            "[XiaoHongShuCrawler.async_initialize] Begin async initialize"
        )

        # 账号池和IP池的初始化
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # xhs对代理验证还行，可以选择长时长的IP，比如30分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为30分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )

        # 初始化账号池
        account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.XHS_PLATFORM_NAME,
            account_save_type=config.ACCOUNT_POOL_SAVE_TYPE,
            proxy_ip_pool=proxy_ip_pool,
        )
        await account_with_ip_pool.async_initialize()

        self.xhs_client.account_with_ip_pool = account_with_ip_pool
        await self.xhs_client.update_account_info()

        # 设置爬虫类型
        crawler_type_var.set(config.CRAWLER_TYPE)

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        if config.CRAWLER_TYPE == "search":
            # Search for notes and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_notes()
        elif config.CRAWLER_TYPE == "creator":
            # Get creator's information and their notes and comments
            await self.get_creators_and_notes()
        else:
            pass

        utils.logger.info("[XiaoHongShuCrawler.start] Xhs Crawler finished ...")

    async def search(self) -> None:
        """
        Search for notes and retrieve their comment information.
        Returns:

        """
        utils.logger.info(
            "[XiaoHongShuCrawler.search] Begin search xiaohongshu keywords"
        )
        xhs_limit_count = 20  # xhs limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < xhs_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = xhs_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[XiaoHongShuCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            while (
                page - start_page + 1
            ) * xhs_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[XiaoHongShuCrawler.search] Skip page {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(
                        f"[XiaoHongShuCrawler.search] search xhs keyword: {keyword}, page: {page}"
                    )
                    note_id_list: List[str] = []
                    xsec_tokens: List[str] = []
                    notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        sort=(
                            SearchSortType(config.SORT_TYPE)
                            if config.SORT_TYPE != ""
                            else SearchSortType.GENERAL
                        ),
                    )
                    utils.logger.info(
                        f"[XiaoHongShuCrawler.search] Search notes res count:{len(notes_res.get('items', []))}"
                    )
                    if not notes_res or not notes_res.get("has_more", False):
                        utils.logger.info("No more content!")
                        break
                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_note_detail_async_task(
                            note_id=post_item.get("id"),
                            xsec_source=post_item.get("xsec_source"),
                            xsec_token=post_item.get("xsec_token"),
                            semaphore=semaphore,
                        )
                        for post_item in notes_res.get("items", {})
                        if post_item.get("model_type") not in ("rec_query", "hot_query")
                    ]
                    note_details = await asyncio.gather(*task_list)
                    for note_detail in note_details:
                        if note_detail:
                            await xhs_store.update_xhs_note(note_detail)
                            note_id_list.append(note_detail.get("note_id", ""))
                            xsec_tokens.append(note_detail.get("xsec_token", ""))
                    page += 1
                    utils.logger.info(
                        f"[XiaoHongShuCrawler.search] Note details: {note_details}"
                    )
                    await self.batch_get_note_comments(note_id_list, xsec_tokens)

                except Exception as ex:
                    utils.logger.error(
                        f"[XiaoHongShuCrawler.search] Search notes error: {ex}"
                    )
                    # 发生异常了，则打印当前爬取的关键词和页码，用于后续继续爬取
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码------------------------------------------"
                    )
                    for i in range(10):
                        utils.logger.error(
                            f"[XiaoHongShuCrawler.search] Current keyword: {keyword}, page: {page}"
                        )
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------"
                    )
                    return

    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info(
            "[XiaoHongShuCrawler.get_creators_and_notes] Begin get xiaohongshu creators"
        )
        for creator_url in config.XHS_CREATOR_URL_LIST:
            creator_url_info: CreatorUrlInfo = parse_creator_info_from_creator_url(
                creator_url
            )
            createor_info: Dict = await self.xhs_client.get_creator_info(
                user_id=creator_url_info.creator_id,
                xsec_token=creator_url_info.xsec_token,
                xsec_source=creator_url_info.xsec_source,
            )
            if createor_info:
                await xhs_store.save_creator(
                    creator_url_info.creator_id, creator=createor_info
                )
            else:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_creators_and_notes] Get creator info error, user_id: {creator_url_info.creator_id}"
                )
                continue

            # Get all note information of the creator
            all_notes_list = await self.xhs_client.get_all_notes_by_creator(
                user_id=creator_url_info.creator_id,
                crawl_interval=0,
                callback=self.fetch_creator_notes_detail,
                xsec_token=creator_url_info.xsec_token,
                xsec_source=creator_url_info.xsec_source,
            )

            note_ids = [note_item.get("note_id", "") for note_item in all_notes_list]
            xsec_tokens = [
                note_item.get("xsec_token", "") for note_item in all_notes_list
            ]
            await self.batch_get_note_comments(note_ids, xsec_tokens)

    async def fetch_creator_notes_detail(self, note_list: List[Dict]):
        """
         Concurrently obtain the specified post list and save the data
        Args:
            note_list:

        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(
                note_id=post_item.get("note_id", ""),
                xsec_source=post_item.get("xsec_source", ""),
                xsec_token=post_item.get("xsec_token", ""),
                semaphore=semaphore,
            )
            for post_item in note_list
        ]

        note_details = await asyncio.gather(*task_list)
        for note_detail in note_details:
            if note_detail:
                await xhs_store.update_xhs_note(note_detail)

    async def get_specified_notes(self):
        """
        Get the information and comments of the specified post
        must be specified note_id, xsec_source, xsec_token
        Returns:

        """
        get_note_detail_task_list = []
        for full_note_url in config.XHS_SPECIFIED_NOTE_URL_LIST:
            note_url_info: NoteUrlInfo = parse_note_info_from_note_url(full_note_url)
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_specified_notes] Parse note url info: {note_url_info}"
            )
            crawler_task = self.get_note_detail_async_task(
                note_id=note_url_info.note_id,
                xsec_source=note_url_info.xsec_source,
                xsec_token=note_url_info.xsec_token,
                semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
            )
            get_note_detail_task_list.append(crawler_task)

        need_get_comment_note_ids = []
        xsec_tokens = []
        note_details = await asyncio.gather(*get_note_detail_task_list)
        for note_detail in note_details:
            if note_detail:
                need_get_comment_note_ids.append(note_detail.get("note_id", ""))
                xsec_tokens.append(note_detail.get("xsec_token", ""))
                await xhs_store.update_xhs_note(note_detail)
        await self.batch_get_note_comments(need_get_comment_note_ids, xsec_tokens)

    async def get_note_detail_async_task(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict]:
        """
        Get note detail task
        Args:
            note_id: note id
            xsec_source: xsec source
            xsec_token: xsec token
            semaphore: semaphore

        Returns:

        """
        async with semaphore:
            try:
                # Try to get note detail from HTML first
                note_detail = await self.xhs_client.get_note_by_id_from_html(
                    note_id=note_id,
                    xsec_source=xsec_source,
                    xsec_token=xsec_token,
                    )
                
                # If HTML method fails, try API method
                if not note_detail:
                    note_detail = await self.xhs_client.get_note_by_id(
                        note_id=note_id,
                        xsec_source=xsec_source,
                        xsec_token=xsec_token,
                    )
                
                if note_detail:
                    # Download media content if available
                    if config.DOWNLOAD_MEDIA:
                        if note_detail.get("type") == "video" and config.DOWNLOAD_VIDEO:
                            video_urls = note_detail.get("video", {}).get("media", {}).get("stream", {}).get("h264", [])
                            if video_urls:
                                await self.download_media_content(video_urls[0].get("master_url"), "video")
                        elif note_detail.get("type") == "normal" and config.DOWNLOAD_IMAGE:
                            image_list = note_detail.get("image_list", [])
                            if image_list:
                                image_urls = [img.get("url_default") for img in image_list if img.get("url_default")]
                                await self.download_media_batch(image_urls, "image")
                
                    return note_detail
            except DataFetchError as ex:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] Get note detail error: {ex}"
                )
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail_async_task] have not fund note detail note_id:{note_id}, err: {ex}"
                )
                return None

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
            account_with_ip = await self.xhs_client.account_with_ip_pool.get_account_with_ip_info()
            if not account_with_ip or not account_with_ip.account:
                utils.logger.error("[XiaoHongShuCrawler.download_media_content] No available account in pool")
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
                    f"[XiaoHongShuCrawler.download_media_content] Successfully downloaded {content_type} from {content_url}"
                )
                return True
            else:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.download_media_content] Failed to download {content_type} from {content_url}"
                )
                return False
                
        except Exception as e:
            utils.logger.error(
                f"[XiaoHongShuCrawler.download_media_content] Error downloading {content_type} from {content_url}: {str(e)}"
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
            utils.logger.info(f"[XiaoHongShuCrawler.download_media_batch] Successfully downloaded {len(urls)} {content_type}s")
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuCrawler.download_media_batch] Failed to download {content_type}s: {str(e)}")

    async def batch_get_note_comments(
        self, note_list: List[str], xsec_tokens: List[str] = []
    ):
        """
        Batch get note comments
        Args:
            note_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[XiaoHongShuCrawler.batch_get_note_comments] Crawling comment mode is not enabled"
            )
            return

        utils.logger.info(
            f"[XiaoHongShuCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}"
        )
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for index, note_id in enumerate(note_list):
            task = asyncio.create_task(
                self.get_comments_async_task(
                    note_id, semaphore, xsec_token=xsec_tokens[index]
                ),
                name=note_id,
            )
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments_async_task(
        self, note_id: str, semaphore: asyncio.Semaphore, xsec_token: str = ""
    ):
        """
        Get note comments with keyword filtering and quantity limitation
        Args:
            note_id:
            semaphore:
            xsec_token:

        Returns:

        """
        async with semaphore:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_comments_async_task] Begin get note id comments {note_id}"
            )
            await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                crawl_interval=random.random(),
                callback=xhs_store.batch_update_xhs_note_comments,
                xsec_token=xsec_token,
            )
