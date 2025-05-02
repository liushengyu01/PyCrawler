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
import random
import re
import traceback
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed, wait_random

import config
from base.base_crawler import AbstractApiClient
from config import PER_NOTE_MAX_COMMENTS_COUNT
from constant.xiaohongshu import XHS_API_URL, XHS_INDEX_URL
from pkg.account_pool import AccountWithIpModel
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.rpc.sign_srv_client import SignServerClient, XhsSignRequest
from pkg.tools import utils

from .exception import (
    AccessFrequencyError,
    DataFetchError,
    ErrorEnum,
    IPBlockError,
    NeedVerifyError,
    SignError,
)
from .extractor import XiaoHongShuExtractor
from .field import SearchNoteType, SearchSortType
from .help import get_search_id


class XiaoHongShuClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        account_with_ip_pool: AccountWithIpPoolManager = None,
    ):
        """
        xhs client constructor
        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            account_with_ip_pool: 账号池管理器
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._sign_client = SignServerClient()
        self.account_with_ip_pool = account_with_ip_pool
        self.account_info: Optional[AccountWithIpModel] = None
        self._extractor = XiaoHongShuExtractor()

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": "https://www.xiaohongshu.com",
            "referer": "https://www.xiaohongshu.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
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

    async def update_account_info(self):
        """
        更新客户端的账号信息, 该方法会一直尝试获取新的账号信息，直到获取到一个有效的账号信息
        Returns:

        """
        have_account = False
        while not have_account:
            utils.logger.info(
                f"[XiaoHongShuClient.update_account_info] try to get a new account"
            )
            account_info = await self.account_with_ip_pool.get_account_with_ip_info()
            self.account_info = account_info
            have_account = await self.pong()
            if not have_account:
                utils.logger.info(
                    f"[XiaoHongShuClient.update_account_info] current account {account_info.account.account_name} is invalid, try to get a new one"
                )

    async def mark_account_invalid(
        self, account_with_ip: AccountWithIpModel, is_again_check: bool = True
    ):
        """
        标记账号为无效
        Args:
            account_with_ip: 账号信息
            is_again_check: 是否再次检查登录态

        Returns:

        """
        if self.account_with_ip_pool:
            # 如果登录态失效了，那么标记账号为无效（有时候可能只是获取帖子详情被block，实际cookies还是可以用的，所以这里加一层判断）
            if is_again_check and not await self.pong():
                utils.logger.info(
                    f"[XiaoHongShuClient.mark_account_invalid] mark account invalid: {account_with_ip.account}"
                )
                await self.account_with_ip_pool.mark_account_invalid(
                    account_with_ip.account
                )
            await self.account_with_ip_pool.mark_ip_invalid(account_with_ip.ip_info)

    async def _pre_headers(self, uri: str, data=None) -> Dict:
        """
        请求头参数签名
        Args:
            uri:
            data:

        Returns:

        """
        sign_req: XhsSignRequest = XhsSignRequest(
            uri=uri,
            data=data,
            cookies=self._cookies,
        )
        xhs_sign_resp = await self._sign_client.xiaohongshu_sign(sign_req)
        headers = {
            "X-S": xhs_sign_resp.data.x_s,
            "X-T": xhs_sign_resp.data.x_t,
            "x-S-Common": xhs_sign_resp.data.x_s_common,
            "X-B3-Traceid": xhs_sign_resp.data.x_b3_traceid,
            "X-Mns": xhs_sign_resp.data.x_mns,
        }
        headers.update(self.headers)
        return headers

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
                f"[XiaoHongShuClient.request] current ip {self.account_info.ip_info.ip} is expired, "
                f"mark it invalid and try to get a new one"
            )
            await self.account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
            self.account_info.ip_info = (
                await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
            )

    @retry(stop=stop_after_attempt(5), wait=wait_random(2, 10))
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
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if need_return_ori_response:
            return response

        try:
            data = response.json()
        except json.decoder.JSONDecodeError:
            return response

        if response.status_code == 471 or response.status_code == 461:
            # someday someone maybe will bypass captcha
            verify_type = response.headers["Verifytype"]
            verify_uuid = response.headers["Verifyuuid"]
            raise Exception(
                f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}, Response: {response}"
            )
        elif data.get("success"):
            return data.get("data", data.get("success"))
        elif data.get("code") == ErrorEnum.IP_BLOCK.value.code:
            raise IPBlockError(ErrorEnum.IP_BLOCK.value.msg)
        elif data.get("code") == ErrorEnum.SIGN_FAULT.value.code:
            raise SignError(ErrorEnum.SIGN_FAULT.value.msg)
        elif data.get("code") == ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.code:
            # 访问频次异常, 再随机延时一下
            utils.logger.error(
                f"[XiaoHongShuClient.request] 访问频次异常，尝试随机延时一下..."
            )
            await asyncio.sleep(utils.random_delay_time(2, 10))
            raise AccessFrequencyError(ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.msg)
        else:
            raise DataFetchError(data)

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict]:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = f"{uri}?" f"{urlencode(params)}"
        try:
            headers = await self._pre_headers(final_uri)
            res = await self.request(
                method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
            )
            return res
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__,
            )

            utils.logger.error(
                f"[XiaoHongShuClient.post] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
            )
            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            headers = await self._pre_headers(final_uri)
            return await self.request(
                method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
            )

    async def post(self, uri: str, data: dict, **kwargs) -> Union[Dict, Response]:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        try:
            headers = await self._pre_headers(uri, data)
            res = await self.request(
                method="POST",
                url=f"{XHS_API_URL}{uri}",
                data=json_str,
                headers=headers,
                **kwargs,
            )
            return res
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__,
            )

            utils.logger.error(
                f"[XiaoHongShuClient.post] 重试了5次:{uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
            )
            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            headers = await self._pre_headers(uri, data)
            return await self.request(
                method="POST",
                url=f"{XHS_API_URL}{uri}",
                data=json_str,
                headers=headers,
                **kwargs,
            )

    async def query_self(self) -> Optional[Dict]:
        """
        查询自己信息
        """
        uri = "/api/sns/web/v1/user/selfinfo"
        headers = await self._pre_headers(uri)
        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.get(f"{XHS_API_URL}{uri}", headers=headers)
            if response.status_code == 200:
                return response.json()
        return None

    async def pong(self) -> bool:
        """
        用于检查登录态和签名服务是否失效了
        Returns:

        """
        await self._sign_client.pong_sign_server()
        utils.logger.info(
            f"[XiaoHongShuClient.pong] Begin to check account: {self.account_info.account.account_name} login state..."
        )
        ping_flag = False
        try:
            self_info: Dict = await self.query_self()
            if self_info and self_info.get("data", {}).get("result", {}).get("success"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(
                f"[XiaoHongShuClient.pong] Ping xhs failed: {e},current account: {self.account_info.account.account_name} and try to login again..."
            )
            ping_flag = False
            await self.mark_account_invalid(self.account_info, is_again_check=False)
        utils.logger.info(f"[XiaoHongShuClient.pong] Login state result: {ping_flag}")
        return ping_flag

    async def get_note_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: SearchSortType = SearchSortType.GENERAL,
        note_type: SearchNoteType = SearchNoteType.ALL,
    ) -> Dict:
        """
        根据关键词搜索笔记
        Args:
            keyword: 关键词参数
            page: 分页第几页
            page_size: 分页数据长度
            sort: 搜索结果排序指定
            note_type: 搜索的笔记类型

        Returns:

        """
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": get_search_id(),
            "sort": sort.value,
            "note_type": note_type.value,
        }
        return await self.post(uri, data)

    async def get_note_by_id(
        self, note_id: str, xsec_source: str = "", xsec_token: str = ""
    ) -> Dict:
        """
        获取笔记详情API
        Args:
            note_id:笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
        }
        # 开启xsec_token详情接口特别容易出现滑块验证，所以暂时不开启
        if xsec_token:
            data["xsec_token"] = xsec_token
            data["xsec_source"] = xsec_source

        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        # 爬取频繁了可能会出现有的笔记能有结果有的没有
        utils.logger.error(
            f"[XiaoHongShuClient.get_note_by_id] get note id:{note_id} empty and res:{res}"
        )
        return dict()

    async def get_note_comments(
        self, note_id: str, cursor: str = "", xsec_token: str = ""
    ) -> Dict:
        """
        获取一级评论的API
        Args:
            note_id: 笔记ID
            cursor: 分页游标
            xsec_token: 验证token
        Returns:

        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
        }
        if xsec_token:
            params["xsec_token"] = xsec_token
        return await self.get(uri, params)

    async def get_note_sub_comments(
        self,
        note_id: str,
        root_comment_id: str,
        num: int = 10,
        cursor: str = "",
        xsec_token: str = "",
    ):
        """
        获取指定父评论下的子评论的API
        Args:
            note_id: 子评论的帖子ID
            root_comment_id: 根评论ID
            num: 分页数量
            cursor: 分页游标
            xsec_token: 验证token
        Returns:

        """
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": num,
            "cursor": cursor,
        }
        if xsec_token:
            params["xsec_token"] = xsec_token
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        note_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        xsec_token: str = "",
    ) -> List[Dict]:
        """
        获取指定笔记下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            note_id: 笔记ID
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more:
            comments_res = await self.get_note_comments(
                note_id, comments_cursor, xsec_token
            )
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            if "comments" not in comments_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_note_all_comments] No 'comments' key found in response: {comments_res}"
                )
                break
            comments = comments_res["comments"]
            if callback:
                await callback(note_id, comments, xsec_token)
            await asyncio.sleep(crawl_interval)
            result.extend(comments)
            if (
                PER_NOTE_MAX_COMMENTS_COUNT
                and len(result) >= PER_NOTE_MAX_COMMENTS_COUNT
            ):
                utils.logger.info(
                    f"[XiaoHongShuClient.get_note_all_comments] The number of comments exceeds the limit: {PER_NOTE_MAX_COMMENTS_COUNT}"
                )
                break
            sub_comments = await self.get_comments_all_sub_comments(
                comments, crawl_interval, callback, xsec_token
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[Dict],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        xsec_token: str = "",
    ) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            comments: 评论列表
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后
            xsec_token: 验证token

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled"
            )
            return []

        result = []
        for comment in comments:
            note_id = comment.get("note_id")
            sub_comments = comment.get("sub_comments")
            if sub_comments and callback:
                await callback(note_id, sub_comments, xsec_token)

            sub_comment_has_more = comment.get("sub_comment_has_more")
            if not sub_comment_has_more:
                continue

            root_comment_id = comment.get("id")
            sub_comment_cursor = comment.get("sub_comment_cursor")

            while sub_comment_has_more:
                comments_res = await self.get_note_sub_comments(
                    note_id,
                    root_comment_id,
                    10,
                    sub_comment_cursor,
                    xsec_token,
                )
                sub_comment_has_more = comments_res.get("has_more", False)
                sub_comment_cursor = comments_res.get("cursor", "")
                if "comments" not in comments_res:
                    utils.logger.info(
                        f"[XiaoHongShuClient.get_comments_all_sub_comments] No 'comments' key found in response: {comments_res}"
                    )
                    break
                comments = comments_res["comments"]
                if callback:
                    await callback(note_id, comments, xsec_token)
                await asyncio.sleep(crawl_interval)
                result.extend(comments)
        return result

    async def get_creator_info(
        self, user_id: str, xsec_token: str, xsec_source: str
    ) -> Optional[Dict]:
        """
        通过解析网页版的用户主页HTML，获取用户个人简要信息
        PC端用户主页的网页存在window.__INITIAL_STATE__这个变量上的，解析它即可

        Args:
            user_id: 用户ID
            xsec_token: 验证token
            xsec_source: 渠道来源

        Returns:

        """
        uri = (
            f"/user/profile/{user_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"
        )
        response: Response = await self.request(
            "GET",
            XHS_INDEX_URL + uri,
            return_response=True,
            follow_redirects=True,
            headers=self.headers,
        )
        creator_info = self._extractor.extract_creator_info_from_html(response.text)
        return creator_info

    async def get_notes_by_creator(
        self,
        creator: str,
        cursor: str,
        page_size: int = 30,
        xsec_token: str = "",
        xsec_source: str = "",
    ) -> Dict:
        """
        获取博主的笔记
        Args:
            creator: 博主ID
            cursor: 上一页最后一条笔记的ID
            page_size: 分页数据长度
            xsec_token: 验证token
            xsec_source: 渠道来源

        Returns:

        """
        uri = "/api/sns/web/v1/user_posted"
        data = {
            "user_id": creator,
            "cursor": cursor,
            "num": page_size,
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
        }
        return await self.get(uri, data)

    async def get_all_notes_by_creator(
        self,
        user_id: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        xsec_token: str = "",
        xsec_source: str = "",
    ) -> List[Dict]:
        """
        获取指定用户下的所有发过的帖子，该方法会一直查找一个用户下的所有帖子信息
        Args:
            user_id: 用户ID
            crawl_interval: 爬取一次的延迟单位（秒）
            callback: 一次分页爬取结束后的更新回调函数
            xsec_token: 验证token
            xsec_source: 渠道来源

        Returns:

        """
        result = []
        notes_has_more = True
        notes_cursor = ""
        while notes_has_more:
            notes_res = await self.get_notes_by_creator(
                user_id,
                notes_cursor,
                xsec_token=xsec_token,
                xsec_source=xsec_source,
            )
            if not notes_res:
                utils.logger.error(
                    f"[XiaoHongShuClient.get_notes_by_creator] The current creator may have been banned by xhs, so they cannot access the data."
                )
                break
            notes_has_more = notes_res.get("has_more", False)
            notes_cursor = notes_res.get("cursor", "")
            if "notes" not in notes_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_all_notes_by_creator] No 'notes' key found in response: {notes_res}"
                )
                break

            notes = notes_res["notes"]
            utils.logger.info(
                f"[XiaoHongShuClient.get_all_notes_by_creator] got user_id:{user_id} notes len : {len(notes)}, notes_cursor: {notes_cursor}"
            )
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
        return result

    async def get_note_by_id_from_html(
        self, note_id: str, xsec_source: str, xsec_token: str
    ) -> Optional[Dict]:
        """
        通过解析网页版的笔记详情页HTML，获取笔记详情

        Args:
            note_id: 笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        req_url = f"{XHS_INDEX_URL}/explore/{note_id}?xsec_token={xsec_token}&xsec_source={xsec_source}"
        retry_times = 5
        ip_proxies = self._proxies
        for current_retry in range(1, retry_times + 1):
            copy_headers = self.headers.copy()
            if current_retry <= 3:
                # 前三次删除cookie，直接不带登录态请求网页
                del copy_headers["Cookie"]

            async with httpx.AsyncClient(proxies=ip_proxies) as client:
                try:
                    reponse = await client.get(req_url, headers=copy_headers)
                    note_dict = self._extractor.extract_note_detail_from_html(
                        note_id, reponse.text
                    )
                    if note_dict:
                        utils.logger.info(
                            f"[XiaoHongShuClient.get_note_by_id_from_html] get note_id:{note_id} detail from html success"
                        )
                        return note_dict

                    utils.logger.info(
                        f"[XiaoHongShuClient.get_note_by_id_from_html] current retried times: {current_retry}"
                    )
                    await asyncio.sleep(random.random())
                    if config.ENABLE_IP_PROXY and 1 < current_retry <= 3:
                        try:
                            ip_proxies = (
                                await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
                            ).format_httpx_proxy()
                        except Exception as e:
                            utils.logger.error(
                                f"[XiaoHongShuClient.get_note_by_id_from_html] get proxy error: {e}"
                            )
                            ip_proxies = None
                except Exception as e:
                    utils.logger.error(
                        f"[XiaoHongShuClient.get_note_by_id_from_html] 请求笔记详情页失败: {e}"
                    )
                    await asyncio.sleep(random.random())

    async def get_note_short_url(self, note_id: str) -> Dict:
        """
        获取笔记的短链接
        Args:
            note_id: 笔记ID

        Returns:

        """
        uri = f"/api/sns/web/short_url"
        data = {"original_url": f"{XHS_INDEX_URL}/discovery/item/{note_id}?a=1"}
        response: Response = await self.post(uri, data=data, return_response=True)
        return response.json()
