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
import json
import traceback
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from constant import zhihu as zhihu_constant
from model.m_zhihu import ZhihuComment, ZhihuContent, ZhihuCreator
from pkg.account_pool import AccountWithIpModel
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.rpc.sign_srv_client import SignServerClient, ZhihuSignRequest
from pkg.tools import utils

from .exception import DataFetchError, ForbiddenError
from .field import SearchSort, SearchTime, SearchType
from .help import ZhihuExtractor


class ZhiHuClient(AbstractApiClient):
    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = None,
        account_with_ip_pool: AccountWithIpPoolManager = None,
    ):
        """
        zhihu client constructor
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
        self._extractor = ZhihuExtractor()

    @property
    def headers(self):
        return {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cookie": self._cookies,
            "priority": "u=1, i",
            "referer": "https://www.zhihu.com/search?q=python&time_interval=a_year&type=content",
            "user-agent": self._user_agent,
            "x-api-version": "3.0.91",
            "x-app-za": "OS=Web",
            "x-requested-with": "fetch",
            "x-zse-93": "101_3_3.0",
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
                f"[ZhiHuClient.update_account_info] try to get a new account"
            )
            self.account_info = (
                await self.account_with_ip_pool.get_account_with_ip_info()
            )
            have_account = await self.pong()
            if not have_account:
                utils.logger.info(
                    f"[ZhiHuClient.update_account_info] current account {self.account_info.account.account_name} is invalid, try to get a new one"
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
                f"[ZhiHuClient.request] current ip {self.account_info.ip_info.ip} is expired, "
                f"mark it invalid and try to get a new one"
            )
            await self.account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
            self.account_info.ip_info = (
                await self.account_with_ip_pool.proxy_ip_pool.get_proxy()
            )

    async def _pre_headers(self, url: str) -> Dict:
        """
        请求头参数签名
        Args:
            url:  请求的URL需要包含请求的参数
        Returns:

        """
        sign_request = ZhihuSignRequest(
            uri=url,
            cookies=self._cookies,
        )
        sign_res = await self._sign_client.zhihu_sign(sign_request)
        headers = self.headers.copy()
        headers["x-zst-81"] = sign_res.data.x_zst_81
        headers["x-zse-96"] = sign_res.data.x_zse_96
        return headers

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def request(self, method, url, **kwargs) -> Union[str, Any]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        await self.check_ip_expired()
        # return response.text
        return_response = kwargs.pop("return_response", False)

        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code != 200:
            utils.logger.error(
                f"[ZhiHuClient.request] Requset Url: {url}, Request error: {response.text}"
            )
            if response.status_code == 403:
                raise ForbiddenError(response.text)
            elif response.status_code == 404:  # 如果一个content没有评论也是404
                return {}

            raise DataFetchError(response.text)

        if return_response:
            return response.text
        try:
            data: Dict = response.json()
            if data.get("error"):
                utils.logger.error(f"[ZhiHuClient.request] Request error: {data}")
                raise DataFetchError(data.get("error", {}).get("message"))
            return data
        except json.JSONDecodeError:
            utils.logger.error(f"[ZhiHuClient.request] Request error: {response.text}")
            raise DataFetchError(response.text)

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict, str]:
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
            base_url = (
                zhihu_constant.ZHIHU_URL
                if "/p/" not in uri
                else zhihu_constant.ZHIHU_ZHUANLAN_URL
            )
            res = await self.request(
                method="GET", url=f"{base_url}{final_uri}", headers=headers, **kwargs
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
                f"[ZhiHuClient.post] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
            )

            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            headers = await self._pre_headers(final_uri)
            return await self.request(
                method="GET",
                url=f"{zhihu_constant.ZHIHU_URL}{final_uri}",
                headers=headers,
                **kwargs,
            )

    async def pong(self) -> bool:
        """
        用于检查登录态是否失效了
        Returns:

        """
        utils.logger.info(
            f"[ZhiHuClient.pong] Begin to check account: {self.account_info.account.account_name} login state..."
        )
        ping_flag = False
        try:
            res = await self.get_current_user_info()
            if res.get("uid") and res.get("name"):
                ping_flag = True
                utils.logger.info("[ZhiHuClient.pong] Ping zhihu successfully")
            else:
                utils.logger.error(
                    f"[ZhiHuClient.pong] Ping zhihu failed, response data: {res}"
                )
        except Exception as e:
            utils.logger.error(
                f"[ZhiHuClient.pong] Ping xhs failed: {e},current account: {self.account_info.account.account_name} and try to login again..."
            )
            ping_flag = False
        return ping_flag

    async def get_current_user_info(self) -> Dict:
        """
        获取当前登录用户信息
        Returns:

        """
        params = {"include": "email,is_active,is_bind_phone"}

        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.get(
                f"{zhihu_constant.ZHIHU_URL}/api/v4/me",
                params=params,
                headers=self.headers,
            )

        return response.json()

    async def get_note_by_keyword(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: SearchSort = SearchSort.DEFAULT,
        note_type: SearchType = SearchType.DEFAULT,
        search_time: SearchTime = SearchTime.DEFAULT,
    ) -> List[ZhihuContent]:
        """
        根据关键词搜索
        Args:
            keyword: 关键词
            page: 第几页
            page_size: 分页size
            sort: 排序
            note_type: 搜索结果类型
            search_time: 搜索多久时间的结果

        Returns:

        """
        uri = "/api/v4/search_v3"
        params = {
            "gk_version": "gz-gaokao",
            "t": "general",
            "q": keyword,
            "correction": 1,
            "offset": (page - 1) * page_size,
            "limit": page_size,
            "filter_fields": "",
            "lc_idx": (page - 1) * page_size,
            "show_all_topics": 0,
            "search_source": "Filter",
            "time_interval": search_time.value,
            "sort": sort.value,
            "vertical": note_type.value,
        }
        search_res = await self.get(uri, params)
        utils.logger.info(
            f"[ZhiHuClient.get_note_by_keyword] Search result: {search_res}"
        )
        return self._extractor.extract_contents_from_search(search_res)

    async def get_root_comments(
        self,
        content_id: str,
        content_type: str,
        offset: str = "",
        limit: int = 10,
        order_by: str = "score",
    ) -> Dict:
        """
        获取内容的一级评论
        Args:
            content_id: 内容ID
            content_type: 内容类型(answer, article, zvideo)
            offset:
            limit:
            order_by:

        Returns:

        """
        uri = f"/api/v4/comment_v5/{content_type}s/{content_id}/root_comment"
        params = {"order": order_by, "offset": offset, "limit": limit}
        return await self.get(uri, params)

    async def get_child_comments(
        self,
        root_comment_id: str,
        offset: str = "",
        limit: int = 10,
        order_by: str = "sort",
    ) -> Dict:
        """
        获取一级评论下的子评论
        Args:
            root_comment_id:
            offset:
            limit:
            order_by:

        Returns:

        """
        uri = f"/api/v4/comment_v5/comment/{root_comment_id}/child_comment"
        params = {"order": order_by, "offset": offset, "limit": limit}
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        content: ZhihuContent,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuComment]:
        """
        获取指定帖子下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            content: 内容详情对象(问题｜文章｜视频)
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        result: List[ZhihuComment] = []
        is_end: bool = False
        offset: str = ""
        limit: int = 10
        while not is_end:
            root_comment_res = await self.get_root_comments(
                content.content_id, content.content_type, offset, limit
            )
            if not root_comment_res:
                break
            paging_info = root_comment_res.get("paging", {})
            is_end = paging_info.get("is_end")
            offset = self._extractor.extract_offset(paging_info)
            comments = self._extractor.extract_comments(
                content, root_comment_res.get("data")
            )

            if not comments:
                break

            if callback:
                await callback(comments)

            result.extend(comments)
            await self.get_comments_all_sub_comments(
                content, comments, crawl_interval=crawl_interval, callback=callback
            )
            await asyncio.sleep(crawl_interval)
        return result

    async def get_comments_all_sub_comments(
        self,
        content: ZhihuContent,
        comments: List[ZhihuComment],
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuComment]:
        """
        获取指定评论下的所有子评论
        Args:
            content: 内容详情对象(问题｜文章｜视频)
            comments: 评论列表
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        all_sub_comments: List[ZhihuComment] = []
        for parment_comment in comments:
            if parment_comment.sub_comment_count == 0:
                continue

            is_end: bool = False
            offset: str = ""
            limit: int = 10
            while not is_end:
                child_comment_res = await self.get_child_comments(
                    parment_comment.comment_id, offset, limit
                )
                if not child_comment_res:
                    break
                paging_info = child_comment_res.get("paging", {})
                is_end = paging_info.get("is_end")
                offset = self._extractor.extract_offset(paging_info)
                sub_comments = self._extractor.extract_comments(
                    content, child_comment_res.get("data")
                )

                if not sub_comments:
                    break

                if callback:
                    await callback(sub_comments)

                all_sub_comments.extend(sub_comments)
                await asyncio.sleep(crawl_interval)
        return all_sub_comments

    async def get_answer_info(
        self, question_id: str, answer_id: str
    ) -> Optional[ZhihuContent]:
        """
        获取回答信息
        Args:
            question_id:
            answer_id:

        Returns:

        """
        uri = f"/question/{question_id}/answer/{answer_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_answer_content_from_html(response_html)

    async def get_article_info(self, article_id: str) -> Optional[ZhihuContent]:
        """
        获取文章信息
        Args:
            article_id:

        Returns:

        """
        uri = f"/p/{article_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_article_content_from_html(response_html)

    async def get_video_info(self, video_id: str) -> Optional[ZhihuContent]:
        """
        获取视频信息
        Args:
            video_id:

        Returns:

        """
        uri = f"/zvideo/{video_id}"
        response_html = await self.get(uri, return_response=True)
        return self._extractor.extract_zvideo_content_from_html(response_html)

    async def get_creator_info(self, url_token: str) -> Optional[ZhihuCreator]:
        """
        获取创作者信息
        Args:
            url_token:

        Returns:

        """
        uri = f"/people/{url_token}"
        html_content: str = await self.get(uri, return_response=True)
        return self._extractor.extract_creator(url_token, html_content)

    async def get_creator_answers(
        self, url_token: str, offset: int = 0, limit: int = 20
    ) -> Dict:
        """
        获取创作者的回答
        Args:
            url_token:
            offset:
            limit:

        Returns:


        """
        uri = f"/api/v4/members/{url_token}/answers"
        params = {
            "include": "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,excerpt,paid_info,reaction_instruction,is_labeled,label_info,relationship.is_authorized,voting,is_author,is_thanked,is_nothelp;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;data[*].question.has_publishing_draft,relationship",
            "offset": offset,
            "limit": limit,
            "order_by": "created",
        }
        return await self.get(uri, params)

    async def get_creator_articles(
        self, url_token: str, offset: int = 0, limit: int = 20
    ) -> Dict:
        """
        获取创作者的文章
        Args:
            url_token:
            offset:
            limit:

        Returns:

        """
        uri = f"/api/v4/members/{url_token}/articles"
        params = {
            "include": "data[*].comment_count,suggest_edit,is_normal,thumbnail_extra_info,thumbnail,can_comment,comment_permission,admin_closed_comment,content,voteup_count,created,updated,upvoted_followees,voting,review_info,reaction_instruction,is_labeled,label_info;data[*].vessay_info;data[*].author.badge[?(type=best_answerer)].topics;data[*].author.vip_info;",
            "offset": offset,
            "limit": limit,
            "order_by": "created",
        }
        return await self.get(uri, params)

    async def get_creator_videos(
        self, url_token: str, offset: int = 0, limit: int = 20
    ) -> Dict:
        """
        获取创作者的视频
        Args:
            url_token:
            offset:
            limit:

        Returns:

        """
        uri = f"/api/v4/members/{url_token}/zvideos"
        params = {
            "include": "similar_zvideo,creation_relationship,reaction_instruction",
            "offset": offset,
            "limit": limit,
            "similar_aggregation": "true",
        }
        return await self.get(uri, params)

    async def get_all_anwser_by_creator(
        self,
        creator: ZhihuCreator,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        获取创作者的所有回答
        Args:
            creator: 创作者信息
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_answers(creator.url_token, offset, limit)
            if not res:
                break
            utils.logger.info(
                f"[ZhiHuClient.get_all_anwser_by_creator] Get creator {creator.url_token} answers: {res}"
            )
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(
                res.get("data")
            )
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_all_articles_by_creator(
        self,
        creator: ZhihuCreator,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        获取创作者的所有文章
        Args:
            creator:
            crawl_interval:
            callback:

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_articles(creator.url_token, offset, limit)
            if not res:
                break
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(
                res.get("data")
            )
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_all_videos_by_creator(
        self,
        creator: ZhihuCreator,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        获取创作者的所有视频
        Args:
            creator:
            crawl_interval:
            callback:

        Returns:

        """
        all_contents: List[ZhihuContent] = []
        is_end: bool = False
        offset: int = 0
        limit: int = 20
        while not is_end:
            res = await self.get_creator_videos(creator.url_token, offset, limit)
            if not res:
                break
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end")
            contents = self._extractor.extract_content_list_from_creator(
                res.get("data")
            )
            if callback:
                await callback(contents)
            all_contents.extend(contents)
            offset += limit
            await asyncio.sleep(crawl_interval)
        return all_contents

    async def get_answers_by_question_id(
        self,
        question_id: str,
        cursor: str = "",
        session_id: str = "",
        limit: int = 5,
        offset: int = 0,
        order: str = "default",
    ) -> Dict:
        """
        获取问题下的所有回答
        Args:
            question_id: 问题ID
            cursor: 游标
            limit: 每页数量
            offset: 偏移量
            order: 排序方式(default | updated)
            session_id: 会话ID

        Returns:

        """
        uri = f"/api/v4/questions/{question_id}/feeds"
        params = {
            "cursor": cursor,
            "limit": limit,
            "offset": offset,
            "order": order,
            "session_id": session_id,
            "ws_qiangzhisafe": "1",
            "platform": "desktop",
            "include": "data[*].is_normal,admin_closed_comment,reward_info,is_collapsed,annotation_action,annotation_detail,collapse_reason,is_sticky,collapsed_by,suggest_edit,comment_count,can_comment,content,editable_content,attachment,voteup_count,reshipment_settings,comment_permission,created_time,updated_time,review_info,relevant_info,question,excerpt,is_labeled,paid_info,paid_info_content,reaction_instruction,relationship.is_authorized,is_author,voting,is_thanked,is_nothelp;data[*].author.follower_count,vip_info,kvip_info,badge[*].topics;data[*].settings.table_of_content.enabled",
        }
        return await self.get(uri, params)

    async def get_all_answers_by_question_id(
        self,
        question_id: str,
        crawl_interval: float = 1.0,
        max_answers: int = 0,
        order: str = "default",
        callback: Optional[Callable] = None,
    ) -> List[ZhihuContent]:
        """
        获取问题下的所有回答

        Args:
            question_id: 问题ID
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            max_answers: 0 表示不限制

        Returns:

        """
        is_end: bool = False
        req_params = {
            "cursor": "",
            "session_id": "",
            "offset": 0,
            "limit": 5,
            "order": order,
        }
        all_answers: List[ZhihuContent] = []
        while not is_end and (max_answers == 0 or len(all_answers) < max_answers):
            res = await self.get_answers_by_question_id(question_id, **req_params)
            if not res:
                break
            paging_info = res.get("paging", {})
            is_end = paging_info.get("is_end", True)
            contents = self._extractor.extract_anwser_list_from_questions_feeds(
                res.get("data", [])
            )
            all_answers.extend(contents)
            if callback:
                await callback(contents)
            await asyncio.sleep(crawl_interval)
            req_params = self._extractor.extract_next_req_params_from_url(
                paging_info, specific_params=req_params.keys()
            )
        utils.logger.info(
            f"[ZhiHuClient.get_all_answers_by_question_id] question id {question_id} get {len(all_answers)} answers"
        )
        return all_answers
