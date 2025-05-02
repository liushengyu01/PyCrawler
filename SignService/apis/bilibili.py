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
import logging

from tenacity import RetryError

from apis.base_handler import TornadoBaseReqHandler
from constant import BILIBILI_DEFAULT_SIGN_SERVER
from constant.error_code import ApiCode
from logic.bilibili.bilibili_logic import BilibiliSignLogic
from params.bilibili_sign import BilibliSignRequest, BilibliSignResponse

logger = logging.getLogger(__name__)
bilibili_sign_logic = BilibiliSignLogic(BILIBILI_DEFAULT_SIGN_SERVER)


class BilibiliSignHandler(TornadoBaseReqHandler):
    request_model = BilibliSignRequest

    async def post(self):
        """
        处理bilibili签名请求
        :return:
        """
        try:
            req: BilibliSignRequest = self.parse_params()
            if not req:
                return

            response: BilibliSignResponse = await bilibili_sign_logic.sign(req)
            self.return_ok(data=response, msg="success")

        except RetryError as e:
            logger.error("bilibli sign error, error: %s", e.last_attempt.exception())
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="douyin sign error",
                                          extra={"error": repr(e.last_attempt.exception())})

        except Exception as e:
            logger.error("bilibli sign unkown error, error: %s", e)
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="douyin sign error", extra={"error": repr(e)})
