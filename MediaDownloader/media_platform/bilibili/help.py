import json
import re
import urllib.parse
from typing import Dict, Optional

from model.m_bilibili import CreatorQueryResponse


class BiliExtractor:

    def extract_creator_info(
        self, up_info: Dict, relation_state: Dict, space_navnum: Dict
    ) -> Optional[CreatorQueryResponse]:
        """
        提取B站主页信息

        Args:
            up_info (Dict): B站用户信息
            relation_state (Dict): B站用户关系状态
            space_navnum (Dict): B站用户空间导航栏数据

        Returns:
            CreatorQueryResponse: 创作者信息
        """
        if not up_info or not relation_state or not space_navnum:
            return None

        res_creator = CreatorQueryResponse(
            nickname=up_info.get("name", ""),
            avatar=up_info.get("face", ""),
            description=up_info.get("sign", ""),
            user_id=str(up_info.get("mid", "")),
            follower_count=str(relation_state.get("follower", "0")),
            following_count=str(relation_state.get("following", "0")),
            content_count=str(space_navnum.get("video", "0")),
        )
        return res_creator

    def extract_w_webid(self, html: str) -> str:
        """
        提取w_webid

        Args:
            html (str): B站主页HTML

        Returns:
            str: w_webid
        """
        __RENDER_DATA__ = re.search(
            r"<script id=\"__RENDER_DATA__\" type=\"application/json\">(.*?)</script>",
            html,
            re.S,
        ).group(1)
        w_webid = json.loads(urllib.parse.unquote(__RENDER_DATA__))["access_id"]
        return w_webid
