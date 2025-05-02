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
import copy
import json
import traceback
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from config import PER_NOTE_MAX_COMMENTS_COUNT
from constant.douyin import DOUYIN_API_URL, DOUYIN_FIXED_USER_AGENT
from pkg.account_pool import AccountWithIpModel
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.rpc.sign_srv_client import DouyinSignRequest, SignServerClient
from pkg.tools import utils
from var import request_keyword_var

from .exception import *
from .field import *
from .help import CommonVerfiyParams


class DouYinApiClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        common_verfiy_params: CommonVerfiyParams = None,
        account_with_ip_pool: AccountWithIpPoolManager = None,
    ):
        """
        dy client constructor
        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            account_with_ip_pool: 账号池管理器
            common_verfiy_params: 通用验证参数模型
        """
        self.timeout = timeout
        self._user_agent = user_agent or DOUYIN_FIXED_USER_AGENT
        self._sign_client = SignServerClient()
        self.common_verfiy_params = common_verfiy_params
        self.account_with_ip_pool = account_with_ip_pool
        self.account_info: Optional[AccountWithIpModel] = None

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "Cookie": self._cookies,
            "origin": "https://www.douyin.com",
            "referer": "https://www.douyin.com/",
            "user-agent": self._user_agent,
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
        return self.account_info.account.cookies

    @property
    def _common_params(self):
        return {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "publish_video_strategy_type": 2,
            "update_version_code": 170400,
            "pc_client_type": 1,
            "version_code": 170400,
            "version_name": "17.4.0",
            "cookie_enabled": "true",
            "screen_width": 2560,
            "screen_height": 1440,
            "browser_language": "zh-CN",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "127.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "engine_version": "127.0.0.0",
            "os_name": "Mac+OS",
            "os_version": "10.15.7",
            "cpu_core_num": 8,
            "device_memory": 8,
            "platform": "PC",
            "downlink": 4.45,
            "effective_type": "4g",
            "round_trip_time": 100,
        }

    @property
    def _verify_params(self):
        return {
            "webid": self.common_verfiy_params.webid,
            "msToken": self.common_verfiy_params.ms_token,
        }

    async def update_account_info(self):
        """
        更新客户端的账号信息
        Returns:

        """
        have_account = False
        while not have_account:
            utils.logger.info(
                f"[DouYinApiClient.update_account_info] try to get a new account"
            )
            account_info = await self.account_with_ip_pool.get_account_with_ip_info()
            self.account_info = account_info
            have_account = await self.pong()
            if not have_account:
                utils.logger.info(
                    f"[DouYinApiClient.update_account_info] current account {account_info.account.account_name} is invalid, try to get a new one"
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

    async def _pre_url_params(self, uri: str, url_params: Dict) -> Dict:
        """
        预处理URL参数，获取a_bogus参数
        Args:
            uri:
            url_params:

        Returns:

        """
        final_url_params = copy.copy(url_params)
        final_url_params.update(self._common_params)
        final_url_params.update(self._verify_params)
        query_params = urllib.parse.urlencode(final_url_params)
        sign_req: DouyinSignRequest = DouyinSignRequest(
            uri=uri,
            query_params=query_params,
            user_agent=self._user_agent,
            cookies=self._cookies,
        )
        dy_sign_resp = await self._sign_client.douyin_sign(sign_req=sign_req)
        final_url_params["a_bogus"] = dy_sign_resp.data.a_bogus
        return final_url_params

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
                f"[DouYinApiClient.request] current ip {self.account_info.ip_info.ip} is expired, "
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

        if "headers" not in kwargs:
            kwargs["headers"] = self._headers

        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if need_return_ori_response:
            return response

        try:
            if response.text == "" or response.text == "blocked":
                utils.logger.error(
                    f"request params incrr, response.text: {response.text}"
                )
                raise Exception("account blocked")
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, **kwargs):
        """
        GET请求
        Args:
            uri: 请求的URI
            params: 请求参数

        Returns:

        """
        try:
            params = await self._pre_url_params(uri, params)
            return await self.request(
                method="GET", url=f"{DOUYIN_API_URL}{uri}", params=params, **kwargs
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
                f"[DouYinApiClient.get] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
            )

            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            params = await self._pre_url_params(uri, params)
            return await self.request(
                method="GET", url=f"{DOUYIN_API_URL}{uri}", params=params, **kwargs
            )

    async def pong(self) -> bool:
        """
        测试接口是否可用
        Returns:

        """
        try:
            res = await self.query_user_self_info()
            if res and res.get("user_uid") and res.get("id"):
                # 这个res中会返回当前登录用户的相关信息，其中包含了：user_agent,则更新当前的user_agent
                if res.get("user_agent"):
                    self._user_agent = res.get("user_agent")
                return True
        except Exception as e:
            utils.logger.error(
                f"[DouYinApiClient.pong] pong failed, query user self response: {e}"
            )
        return False

    async def query_user_self_info(self) -> Dict:
        """
        查询用户自己的信息
        Returns:

        """
        uri = "/aweme/v1/web/query/user/"
        params = {}
        params.update(self._common_params)
        params.update(self._verify_params)
        # params = await self._pre_url_params(uri, params)
        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.get(
                f"{DOUYIN_API_URL}{uri}", params=params, headers=self._headers
            )

        return response.json()

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = 0,
        search_channel: SearchChannelType = SearchChannelType.GENERAL,
        sort_type: SearchSortType = SearchSortType.GENERAL,
        publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
        search_id: str = "",
    ):
        """
        搜索信息
        Args:
            keyword: 搜索关键字
            offset: 分页偏移量
            search_channel: 搜索渠道
            sort_type: 排序类型
            publish_time: 发布时间
            search_id: 搜索ID

        Returns:

        """
        query_params = {
            "search_channel": search_channel.value,
            "enable_history": "1",
            "keyword": keyword,
            "search_source": "tab_search",
            "query_correct_type": "1",
            "is_filter_search": "0",
            "from_group_id": "7378810571505847586",
            "offset": offset,
            "count": "10",
            "need_filter_settings": "1",
            "list_type": "multi",
            "search_id": search_id,
        }
        if (
            sort_type.value != SearchSortType.GENERAL.value
            or publish_time.value != PublishTimeType.UNLIMITED.value
        ):
            query_params["filter_selected"] = json.dumps(
                {
                    "sort_type": str(sort_type.value),
                    "publish_time": str(publish_time.value),
                },
                separators=(",", ":"),
            )
            query_params["is_filter_search"] = 1
            query_params["search_source"] = "tab_search"
        return await self.get("/aweme/v1/web/general/search/single/", query_params)

    async def get_video_by_id(self, aweme_id: str) -> Any:
        """
        DouYin Video Detail API
        Args:
            aweme_id: 视频ID

        Returns:

        """
        params = {
            "aweme_id": aweme_id,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        params.update(self._verify_params)
        headers = copy.copy(self._headers)
        if "Origin" in headers:
            del headers["Origin"]
        res = await self.get("/aweme/v1/web/aweme/detail/", params, headers=headers)
        return res.get("aweme_detail", {})

    async def get_aweme_comments(self, aweme_id: str, cursor: int = 0):
        """
        获取帖子的评论
        Args:
            aweme_id: 视频ID
            cursor: 分页游标

        Returns:

        """
        uri = "/aweme/v1/web/comment/list/"
        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": 20,
            "item_type": 0,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        params.update(self._verify_params)
        keywords = request_keyword_var.get()
        referer_url = (
            "https://www.douyin.com/search/"
            + keywords
            + "?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general"
        )
        headers = copy.copy(self._headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=":/")
        return await self.get(uri, params, headers=headers)

    async def get_sub_comments(self, comment_id: str, cursor: int = 0):
        """
        获取子评论
        Args:
            comment_id: 父评论ID
            cursor: 分页游标

        Returns:

        """
        uri = "/aweme/v1/web/comment/list/reply/"
        params = {
            "comment_id": comment_id,
            "cursor": cursor,
            "count": 20,
            "item_type": 0,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        params.update(self._verify_params)
        keywords = request_keyword_var.get()
        referer_url = (
            "https://www.douyin.com/search/"
            + keywords
            + "?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general"
        )
        headers = copy.copy(self._headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=":/")
        return await self.get(uri, params, headers=headers)

    async def get_aweme_all_comments(
        self,
        aweme_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ):
        """
        获取视频的所有评论
        Args:
            aweme_id: 视频ID
            crawl_interval: 延时
            callback: 回调函数

        Returns:

        """
        result = []
        comments_has_more = 1
        comments_cursor = 0
        while comments_has_more:
            comments_res = await self.get_aweme_comments(aweme_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", 0)
            comments_cursor = comments_res.get("cursor", 0)
            comments = comments_res.get("comments", [])
            if not comments:
                continue
            result.extend(comments)
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(aweme_id, comments)
            if (
                PER_NOTE_MAX_COMMENTS_COUNT
                and len(result) >= PER_NOTE_MAX_COMMENTS_COUNT
            ):
                utils.logger.info(
                    f"[DouYinApiClient.get_note_all_comments] The number of comments exceeds the limit: {PER_NOTE_MAX_COMMENTS_COUNT}"
                )
                break
            await asyncio.sleep(crawl_interval)
            sub_comments = await self.get_comments_all_sub_comments(
                aweme_id, comments, crawl_interval, callback
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        aweme_id: str,
        comments: List[Dict],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            aweme_id: 视频ID
            comments: 评论列表
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[DouYinApiClient.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled"
            )
            return []
        result = []
        for comment in comments:
            reply_comment_total = comment.get("reply_comment_total")
            if reply_comment_total > 0:
                comment_id = comment.get("cid")
                sub_comments_has_more = 1
                sub_comments_cursor = 0
                while sub_comments_has_more:
                    sub_comments_res = await self.get_sub_comments(
                        comment_id, sub_comments_cursor
                    )
                    sub_comments_has_more = sub_comments_res.get("has_more", 0)
                    sub_comments_cursor = sub_comments_res.get("cursor", 0)
                    sub_comments = sub_comments_res.get("comments", [])
                    if not sub_comments:
                        continue
                    result.extend(sub_comments)
                    if callback:  # 如果有回调函数，就执行回调函数
                        await callback(aweme_id, sub_comments)
                    await asyncio.sleep(crawl_interval)
        return result

    async def get_user_info(self, sec_user_id: str):
        """
        获取指定sec_user_id用户信息
        Args:
            sec_user_id:

        Returns:

        """
        uri = "/aweme/v1/web/user/profile/other/"
        params = {
            "sec_user_id": sec_user_id,
            "publish_video_strategy_type": 2,
            "personal_center_strategy": 1,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        return await self.get(uri, params)

    async def get_user_aweme_posts(
        self, sec_user_id: str, max_cursor: str = ""
    ) -> Dict:
        """
        获取指定用户的所有视频
        Args:
            sec_user_id:
            max_cursor:

        Returns:

        """
        uri = "/aweme/v1/web/aweme/post/"
        params = {
            "sec_user_id": sec_user_id,
            "count": 44,
            "max_cursor": max_cursor,
            "locate_query": "false",
            "publish_video_strategy_type": 2,
            "verifyFp": self.common_verfiy_params.verify_fp,
            "fp": self.common_verfiy_params.verify_fp,
        }
        return await self.get(uri, params)

    async def get_all_user_aweme_posts(
        self,
        sec_user_id: str,
        callback: Optional[Callable] = None,
        max_count: int = 100,
    ):
        """
        获取指定用户的所有视频
        Args:
            sec_user_id:
            callback:
            max_count:

        Returns:

        """
        posts_has_more = 1
        max_cursor = ""
        result = []
        while posts_has_more == 1 and len(result) < max_count:
            aweme_post_res = await self.get_user_aweme_posts(sec_user_id, max_cursor)
            posts_has_more = aweme_post_res.get("has_more", 0)
            max_cursor = aweme_post_res.get("max_cursor")
            aweme_list = (
                aweme_post_res.get("aweme_list")
                if aweme_post_res.get("aweme_list")
                else []
            )
            if not aweme_list:
                # 如果获取到的视频列表为空，则认为该用户没有视频，直接跳出循环 还有一种可能是私密账号
                utils.logger.info(
                    f"[DouYinApiClient.get_all_user_aweme_posts] sec_user_id:{sec_user_id} has no video"
                )
                break
            utils.logger.info(
                f"[DouYinApiClient.get_all_user_aweme_posts] got sec_user_id:{sec_user_id} video len : {len(aweme_list)}"
            )
            if callback:
                await callback(aweme_list)
            result.extend(aweme_list)
        return result
