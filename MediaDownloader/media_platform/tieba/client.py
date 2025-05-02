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
import json
import traceback
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from config import PER_NOTE_MAX_COMMENTS_COUNT
from constant.baidu_tieba import TIEBA_URL
from model.m_baidu_tieba import TiebaComment, TiebaCreator, TiebaNote
from pkg.account_pool import AccountWithIpModel
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.tools import utils

from .field import SearchNoteType, SearchSortType
from .help import TieBaExtractor


class BaiduTieBaClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        account_with_ip_pool: AccountWithIpPoolManager = None,
    ):
        """
        tieba client constructor
        Args:
            timeout:
            user_agent:
            account_with_ip_pool:
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._page_extractor = TieBaExtractor()
        self.account_with_ip_pool = account_with_ip_pool
        self.account_info: Optional[AccountWithIpModel] = None

    @property
    def headers(self):
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Cookie": self._cookies,
            "origin": "https://tieba.baidu.com",
            "referer": "https://tieba.baidu.com",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

    @property
    def _proxies(self):
        return (
            self.account_info.ip_info.format_httpx_proxy()
            if self.account_info.ip_info
            else None
        )

    @property
    def _cookies(self):
        # return ""
        return self.account_info.account.cookies

    async def update_account_info(self):
        """
        更新客户端的账号信息, 该方法会一直尝试获取新的账号信息，直到获取到一个有效的账号信息
        Returns:

        """
        have_account = False
        while not have_account:
            utils.logger.info(
                f"[BaiduTieBaClient.update_account_info] try to get a new account"
            )
            self.account_info = (
                await self.account_with_ip_pool.get_account_with_ip_info()
            )
            have_account = await self.pong()
            if not have_account:
                utils.logger.info(
                    f"[BaiduTieBaClient.update_account_info] current account {self.account_info.account.account_name} is invalid, try to get a new one"
                )

    async def mark_account_invalid(self, account_with_ip: AccountWithIpModel):
        """
        标记账号为无效
        Args:
            account_with_ip:

        Returns:

        """
        if self.account_with_ip_pool:
            await self.account_with_ip_pool.mark_account_invalid(
                account_with_ip.account
            )
            await self.account_with_ip_pool.mark_ip_invalid(account_with_ip.ip_info)

    async def check_ip_expired(self):
        """
        检查IP是否过期, 由于IP的过期时间在运行中是不确定的，所以每次请求都需要验证下IP是否过期
        如果过期了，那么需要重新获取一个新的IP，赋值给当前账号信息
        Returns:

        """
        if (
            config.ENABLE_IP_PROXY
            and self.account_info.ip_info
            and self.account_info.ip_info.is_expired
        ):
            utils.logger.info(
                f"[BaiduTieBaClient.request] current ip {self.account_info.ip_info.ip} is expired, "
                f"mark it invalid and try to get a new one"
            )
            await self.account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
            self.account_info.ip_info = (
                await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
            )

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def request(self, method, url, **kwargs) -> Union[Response, Dict]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        await self.check_ip_expired()
        need_return_ori_response = kwargs.get("return_response", False)
        if "return_response" in kwargs:
            del kwargs["return_response"]

        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout, headers=self.headers, **kwargs
            )

        if response.status_code != 200:
            utils.logger.error(
                f"Request failed, method: {method}, url: {url}, status code: {response.status_code}"
            )
            utils.logger.error(f"Request failed, response: {response.text}")
            raise Exception(
                f"Request failed, method: {method}, url: {url}, status code: {response.status_code}"
            )

        if response.text == "" or response.text == "blocked":
            utils.logger.error(f"request params incrr, response.text: {response.text}")
            raise Exception("account blocked")

        if need_return_ori_response:
            return response

        return response.json()

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict]:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数

        Returns:

        """
        final_uri = uri
        if params and isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"
        try:
            return await self.request(
                method="GET", url=f"{TIEBA_URL}{final_uri}", **kwargs
            )
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__,
            )

            utils.logger.error(
                f"[BaiduTieBaClient.get] 请求uri:{uri} 重试均失败了，尝试更换账号与IP再次发起重试"
            )
            try:
                utils.logger.info(
                    f"[BaiduTieBaClient.get] 请求uri:{uri} 尝试更换IP再次发起重试..."
                )
                await self.account_with_ip_pool.mark_ip_invalid(
                    self.account_info.ip_info
                )
                if config.ENABLE_IP_PROXY:
                    self.account_info.ip_info = (
                        await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
                    )
                    return await self.request(
                        method="GET", url=f"{TIEBA_URL}{final_uri}", **kwargs
                    )

            except RetryError as ee:
                # 获取原始异常
                original_exception = ee.last_attempt.exception()
                traceback.print_exception(
                    type(original_exception),
                    original_exception,
                    original_exception.__traceback__,
                )

                utils.logger.error(
                    f"[BaiduTieBaClient.get] 请求uri:{uri}，IP更换后还是失败，尝试更换账号与IP再次发起重试"
                )
                await self.mark_account_invalid(self.account_info)
                await self.update_account_info()
                return await self.request(
                    method="GET", url=f"{TIEBA_URL}{final_uri}", **kwargs
                )

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        try:
            return await self.request(
                method="POST", url=f"{TIEBA_URL}{uri}", data=json_str, **kwargs
            )
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__,
            )

            utils.logger.error(
                f"[BaiduTieBaClient.post] 请求uri:{uri} 重试均失败了，尝试更换账号与IP再次发起重试"
            )
            try:
                utils.logger.info(
                    f"[BaiduTieBaClient.post] 请求uri:{uri} 尝试更换IP再次发起重试..."
                )
                await self.account_with_ip_pool.mark_ip_invalid(
                    self.account_info.ip_info
                )
                self.account_info.ip_info = (
                    await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
                )
                return await self.request(
                    method="POST", url=f"{TIEBA_URL}{uri}", data=json_str, **kwargs
                )
            except RetryError as ee:
                # 获取原始异常
                original_exception = ee.last_attempt.exception()
                traceback.print_exception(
                    type(original_exception),
                    original_exception,
                    original_exception.__traceback__,
                )

                utils.logger.error(
                    f"[BaiduTieBaClient.post]请求uri:{uri}，IP更换后还是失败，尝试更换账号与IP再次发起重试"
                )
                await self.mark_account_invalid(self.account_info)
                await self.update_account_info()
                return await self.request(
                    method="POST", url=f"{TIEBA_URL}{uri}", data=json_str, **kwargs
                )

    async def pong(self) -> bool:
        """
        用于检查登录态是否失效了
        Returns:

        """
        utils.logger.info("[BaiduTieBaClient.pong] Begin to pong tieba...")
        try:
            uri = "/mo/q/sync"
            async with httpx.AsyncClient(proxies=self._proxies) as client:
                response = await client.get(f"{TIEBA_URL}{uri}", headers=self.headers)

            res: Dict = response.json()
            if res and res.get("no") == 0:
                ping_flag = True
            else:
                utils.logger.warn(
                    f"[BaiduTieBaClient.pong] user not login, will try to login again..."
                )
                ping_flag = False
        except Exception as e:
            utils.logger.error(
                f"[BaiduTieBaClient.pong] Ping xhs failed: {e},current account: {self.account_info.account.account_name} and try to login again..."
            )
            ping_flag = False
        return ping_flag

    async def get_notes_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 10,
        sort: SearchSortType = SearchSortType.TIME_DESC,
        note_type: SearchNoteType = SearchNoteType.FIXED_THREAD,
    ) -> List[TiebaNote]:
        """
        根据关键词搜索贴吧帖子
        Args:
            keyword: 关键词
            page: 分页第几页
            page_size: 每页大小
            sort: 结果排序方式
            note_type: 帖子类型（主题贴｜主题+回复混合模式）
        Returns:

        """
        uri = "/f/search/res"
        params = {
            "isnew": 1,
            "qw": keyword,
            "rn": page_size,
            "pn": page,
            "sm": sort.value,
            "only_thread": note_type.value,
        }
        response = await self.get(uri, params=params, return_response=True)
        return self._page_extractor.extract_search_note_list(response.text)

    async def get_note_by_id(self, note_id: str) -> TiebaNote:
        """
        根据帖子ID获取帖子详情
        Args:
            note_id:

        Returns:

        """
        uri = f"/p/{note_id}"
        response = await self.get(uri, return_response=True)
        return self._page_extractor.extract_note_detail(response.text)

    async def get_note_all_comments(
        self,
        note_detail: TiebaNote,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[TiebaComment]:
        """
        获取指定帖子下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            note_detail: 帖子详情对象
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        uri = f"/p/{note_detail.note_id}"
        result: List[TiebaComment] = []
        current_page = 1
        while note_detail.total_replay_page >= current_page:
            params = {"pn": current_page}
            response = await self.get(uri, params=params, return_response=True)
            comments = self._page_extractor.extract_tieba_note_parment_comments(
                response.text, note_id=note_detail.note_id
            )
            if not comments:
                break
            if callback:
                await callback(note_detail.note_id, comments)
            result.extend(comments)
            if (
                PER_NOTE_MAX_COMMENTS_COUNT
                and len(result) >= PER_NOTE_MAX_COMMENTS_COUNT
            ):
                utils.logger.info(
                    f"[BaiduTieBaClient.get_note_all_comments] The number of comments exceeds the limit: {PER_NOTE_MAX_COMMENTS_COUNT}"
                )
                break
            # 获取所有子评论
            await self.get_comments_all_sub_comments(
                comments, crawl_interval=crawl_interval, callback=callback
            )
            await asyncio.sleep(crawl_interval)
            current_page += 1
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[TiebaComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[TiebaComment]:
        """
        获取指定评论下的所有子评论
        Args:
            comments: 评论列表
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        uri = "/p/comment"
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        all_sub_comments: List[TiebaComment] = []
        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            current_page = 1
            max_sub_page_num = parment_comment.sub_comment_count // 10 + 1
            while max_sub_page_num >= current_page:
                params = {
                    "tid": parment_comment.note_id,  # 帖子ID
                    "pid": parment_comment.comment_id,  # 父级评论ID
                    "fid": parment_comment.tieba_id,  # 贴吧ID
                    "pn": current_page,  # 页码
                }
                response = await self.get(uri, params=params, return_response=True)
                sub_comments = self._page_extractor.extract_tieba_note_sub_comments(
                    response.text, parent_comment=parment_comment
                )

                if not sub_comments:
                    break
                if callback:
                    await callback(parment_comment.note_id, sub_comments)
                all_sub_comments.extend(sub_comments)
                await asyncio.sleep(crawl_interval)
                current_page += 1
        return all_sub_comments

    async def get_notes_by_tieba_name(
        self, tieba_name: str, page_num: int
    ) -> List[TiebaNote]:
        """
        根据贴吧名称获取帖子列表
        Args:
            tieba_name: 贴吧名称
            page_num: 分页数量

        Returns:

        """
        uri = f"/f?kw={tieba_name}&pn={page_num}"
        response = await self.get(uri, return_response=True)
        return self._page_extractor.extract_tieba_note_list(response.text)

    async def get_creator_info_by_url(self, creator_url: str) -> str:
        """
        根据创作者ID获取创作者信息
        Args:
            creator_url: 创作者主页URL

        Returns:

        """
        creator_res = await self.request(
            method="GET", url=creator_url, return_response=True
        )
        return creator_res.text

    async def get_notes_by_creator(self, user_name: str, page_number: int) -> Dict:
        """
        根据创作者获取创作者的所有帖子
        Args:
            user_name:
            page_number:

        Returns:

        """
        uri = f"/home/get/getthread"
        params = {
            "un": user_name,
            "pn": page_number,
            "ie": "utf-8",
            "_": utils.get_current_timestamp(),
        }
        return await self.get(uri, params=params)

    async def get_all_notes_by_creator_user_name(
        self,
        user_name: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_note_count: int = 0,
        creator_page_html_content: str = None,
    ) -> List[TiebaNote]:
        """
        根据创作者用户名获取创作者所有帖子
        Args:
            user_name: 创作者用户名
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后的回调函数，是一个awaitable类型的函数
            max_note_count: 帖子最大获取数量，如果为 0则获取所有
            creator_page_html_content: 创作者主页的HTML内容
        Returns:

        """
        # 百度贴吧比较特殊一些，前10个帖子是直接展示在主页上的，要单独处理，通过API获取不到
        result: List[TiebaNote] = []
        if creator_page_html_content:
            thread_id_list = (
                self._page_extractor.extract_tieba_thread_id_list_from_creator_page(
                    creator_page_html_content
                )
            )
            utils.logger.info(
                f"[BaiduTieBaClient.get_all_notes_by_creator] got user_name:{user_name} thread_id_list len : {len(thread_id_list)}"
            )
            note_detail_task = [
                self.get_note_by_id(thread_id) for thread_id in thread_id_list
            ]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            result.extend(notes)

        notes_has_more = 1
        page_number = 1
        page_per_count = 20
        total_get_count = 0
        while notes_has_more == 1 and (
            max_note_count == 0 or total_get_count < max_note_count
        ):
            notes_res = await self.get_notes_by_creator(user_name, page_number)
            if not notes_res or notes_res.get("no") != 0:
                utils.logger.error(
                    f"[BaiduTieBaClient.get_notes_by_creator] got user_name:{user_name} notes failed, notes_res: {notes_res}"
                )
                break
            notes_data = notes_res.get("data")
            if not notes_data:
                break
            notes_has_more = notes_data.get("has_more")
            notes = notes_data["thread_list"]
            utils.logger.info(
                f"[BaiduTieBaClient.get_all_notes_by_creator] got user_name:{user_name} notes len : {len(notes)}"
            )

            note_detail_task = [
                self.get_note_by_id(note["thread_id"]) for note in notes
            ]
            notes = await asyncio.gather(*note_detail_task)
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
            page_number += 1
            total_get_count += page_per_count
        return result
