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
import random
from asyncio import Task
from typing import List, Optional, cast

import config
import constant
from base.base_crawler import AbstractCrawler
from model.m_zhihu import ZhihuContent, ZhihuCreator
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from pkg.tools import utils
from repo.platform_save_data import zhihu as zhihu_store
from var import crawler_type_var, source_keyword_var

from .client import ZhiHuClient
from .exception import DataFetchError
from .help import judge_zhihu_url


class ZhihuCrawler(AbstractCrawler):

    def __init__(self) -> None:
        self.zhihu_client = ZhiHuClient()

    async def async_initialize(self):
        """
        Asynchronous Initialization
        Returns:

        """
        utils.logger.info("[ZhihuCrawler.async_initialize] Begin async initialize")
        utils.logger.info(
            "[ZhihuCrawler.start] Zhihu Crawler start（提醒：zhihu的cookies要用搜索结果页面的cookies，否则搜索接口无法使用） ..."
        )
        # 账号池和IP池的初始化
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # zhihu对代理验证还行，可以选择长时长的IP，比如30分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为30分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )

        # 初始化账号池
        account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.ZHIHU_PLATFORM_NAME,
            account_save_type=config.ACCOUNT_POOL_SAVE_TYPE,
            proxy_ip_pool=proxy_ip_pool,
        )
        await account_with_ip_pool.async_initialize()

        self.zhihu_client.account_with_ip_pool = account_with_ip_pool
        await self.zhihu_client.update_account_info()

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

        utils.logger.info("[ZhihuCrawler.start] Zhihu Crawler finished ...")

    async def search(self) -> None:
        """
        Search for notes and retrieve their comment information
        Returns:

        """
        utils.logger.info("[ZhihuCrawler.search] Begin search zhihu keywords")
        zhihu_limit_count = 20  # zhihu limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < zhihu_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = zhihu_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(
                f"[ZhihuCrawler.search] Current search keyword: {keyword}"
            )
            page = 1
            while (
                page - start_page + 1
            ) * zhihu_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[ZhihuCrawler.search] Skip page {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(
                        f"[ZhihuCrawler.search] search zhihu keyword: {keyword}, page: {page}"
                    )
                    content_list: List[ZhihuContent] = (
                        await self.zhihu_client.get_note_by_keyword(
                            keyword=keyword,
                            page=page,
                        )
                    )
                    utils.logger.info(
                        f"[ZhihuCrawler.search] Search contents :{content_list}"
                    )
                    if not content_list:
                        utils.logger.info("No more content!")
                        break

                    page += 1
                    for content in content_list:
                        await zhihu_store.update_zhihu_content(content)
                        
                        # Download media content if available
                        if content.content_type == "video" and content.content_url:
                            await self.download_media_content(content.content_url, "video")
                        elif content.content_type == "article" and content.content_url:
                            # For articles, we might want to download images
                            if hasattr(content, 'images') and content.images:
                                await self.download_media_batch(content.images, "image")

                    await self.batch_get_content_comments(content_list)
                except DataFetchError:
                    utils.logger.error("[ZhihuCrawler.search] Search content error")
                    return

    async def batch_get_content_comments(self, content_list: List[ZhihuContent]):
        """
        Batch get content comments
        Args:
            content_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[ZhihuCrawler.batch_get_content_comments] Crawling comment mode is not enabled"
            )
            return

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for content_item in content_list:
            task = asyncio.create_task(
                self.get_comments(content_item, semaphore), name=content_item.content_id
            )
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments(
        self, content_item: ZhihuContent, semaphore: asyncio.Semaphore
    ):
        """
        Get note comments with keyword filtering and quantity limitation
        Args:
            content_item:
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(
                f"[ZhihuCrawler.get_comments] Begin get note id comments {content_item.content_id}"
            )
            await self.zhihu_client.get_note_all_comments(
                content=content_item,
                crawl_interval=random.random(),
                callback=zhihu_store.batch_update_zhihu_note_comments,
            )

    async def get_creators_and_notes(self) -> None:
        """
        Get creator's information and their notes and comments
        Returns:

        """
        utils.logger.info(
            "[ZhihuCrawler.get_creators_and_notes] Begin get xiaohongshu creators"
        )
        for user_link in config.ZHIHU_CREATOR_URL_LIST:
            utils.logger.info(
                f"[ZhihuCrawler.get_creators_and_notes] Begin get creator {user_link}"
            )
            user_url_token = user_link.split("/")[-1]
            # get creator detail info from web html content
            createor_info: ZhihuCreator = await self.zhihu_client.get_creator_info(
                url_token=user_url_token
            )
            if not createor_info:
                utils.logger.info(
                    f"[ZhihuCrawler.get_creators_and_notes] Creator {user_url_token} not found"
                )
                continue

            utils.logger.info(
                f"[ZhihuCrawler.get_creators_and_notes] Creator info: {createor_info}"
            )
            await zhihu_store.save_creator(creator=createor_info)

            # 默认只提取回答信息，如果需要文章和视频，把下面的注释打开即可

            # Get all anwser information of the creator
            all_content_list = await self.zhihu_client.get_all_anwser_by_creator(
                creator=createor_info,
                crawl_interval=random.random(),
                callback=zhihu_store.batch_update_zhihu_contents,
            )
            
            # Download media content for all answers
            for content in all_content_list:
                if content.content_type == "video" and content.content_url:
                    await self.download_media_content(content.content_url, "video")
                elif content.content_type == "article" and content.content_url:
                    # For articles, we might want to download images
                    if hasattr(content, 'images') and content.images:
                        await self.download_media_batch(content.images, "image")

            # Get all articles of the creator's contents
            # all_content_list = await self.zhihu_client.get_all_articles_by_creator(
            #     creator=createor_info,
            #     crawl_interval=random.random(),
            #     callback=zhihu_store.batch_update_zhihu_contents
            # )

            # Get all videos of the creator's contents
            # all_content_list = await self.zhihu_client.get_all_videos_by_creator(
            #     creator=createor_info,
            #     crawl_interval=random.random(),
            #     callback=zhihu_store.batch_update_zhihu_contents
            # )

            # Get all comments of the creator's contents
            await self.batch_get_content_comments(all_content_list)

    async def get_note_detail(
        self, full_note_url: str, semaphore: asyncio.Semaphore, note_type: str
    ) -> Optional[ZhihuContent]:
        """
        Get note detail
        Args:
            full_note_url: str
            semaphore:
            note_type:

        Returns:

        """
        async with semaphore:
            utils.logger.info(
                f"[ZhihuCrawler.get_specified_notes] Begin get specified note {full_note_url}"
            )
            if note_type == constant.ANSWER_NAME:
                question_id = full_note_url.split("/")[-3]
                answer_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get answer info, question_id: {question_id}, answer_id: {answer_id}"
                )
                return await self.zhihu_client.get_answer_info(question_id, answer_id)

            elif note_type == constant.ARTICLE_NAME:
                article_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get article info, article_id: {article_id}"
                )
                return await self.zhihu_client.get_article_info(article_id)

            elif note_type == constant.VIDEO_NAME:
                video_id = full_note_url.split("/")[-1]
                utils.logger.info(
                    f"[ZhihuCrawler.get_specified_notes] Get video info, video_id: {video_id}"
                )
                return await self.zhihu_client.get_video_info(video_id)

    async def get_specified_notes(self):
        """
        Get the information and comments of the specified post
        Returns:

        """
        need_get_comment_notes: List[ZhihuContent] = []
        note_details: List[ZhihuContent] = []
        for full_note_url in config.ZHIHU_SPECIFIED_ID_LIST:
            full_note_url = full_note_url.split("?")[0]
            note_type: str = judge_zhihu_url(full_note_url)

            # 问题下的回答列表 for issue support #135
            if note_type == constant.QUESTION_NAME:
                question_id = full_note_url.split("/")[-1]
                all_answer_contents = (
                    await self.zhihu_client.get_all_answers_by_question_id(
                        question_id,
                        crawl_interval=0,
                        max_answers=config.CRAWLER_MAX_NOTES_COUNT,
                        order="default",
                        callback=zhihu_store.batch_update_zhihu_contents,
                    )
                )
                note_details.extend(all_answer_contents)
            else:
                note_detail = await self.get_note_detail(
                    full_note_url=full_note_url,
                    semaphore=asyncio.Semaphore(config.MAX_CONCURRENCY_NUM),
                    note_type=note_type,
                )
                note_details.append(note_detail)
                await zhihu_store.update_zhihu_content(note_detail)

        await self.batch_get_content_comments(need_get_comment_notes)
