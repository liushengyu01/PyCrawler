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
from constant import XHS_DEFAULT_SIGN_SERVER
from constant.error_code import ApiCode
from context_vars import xhs_manager_ctx_var
from logic.xhs import XhsSignLogic
from params.xiaohongshu_sign import (XhsSignRequest, XhsSignResponse,
                                     XhsUpdateCookiesRequest)
from pkg.custom_exceptions import BusinessLogicError

logger = logging.getLogger(__name__)
xhs_sign_logic = XhsSignLogic(XHS_DEFAULT_SIGN_SERVER)


class XhsSignHandler(TornadoBaseReqHandler):
    request_model = XhsSignRequest

    async def post(self):
        """
        处理xhs签名请求
        :return:
        """
        try:
            req: XhsSignRequest = self.parse_params()
            if not req:
                return

            response: XhsSignResponse = await xhs_sign_logic.sign(req)
            self.return_ok(data=response, msg="success")

        except RetryError as e:
            logger.error("xhs sign error, error: %s", e.last_attempt.exception())
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="xhs sign error",
                                          extra={"error": repr(e.last_attempt.exception())})

        except Exception as e:
            logger.error("xhs sign unkown error, error: %s", e)
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="xhs sign error", extra={"error": repr(e)})


class XhsUpdateSignBrowserCookies(TornadoBaseReqHandler):
    request_model = XhsUpdateCookiesRequest

    async def post(self):
        """
        更新xhs浏览器cookies,会调用xhs_browser_manager中的一系列方法来完成cookies更新
        :return:
        """
        req: XhsUpdateCookiesRequest = self.parse_params()
        if not req:
            return

        xhs_browser_manager = xhs_manager_ctx_var.get()
        if not xhs_browser_manager:
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="xhs browser manager object not found...")
        try:
            await xhs_browser_manager.update_fixed_cookies(req.cookies)
            self.return_ok(msg="update xhs sign server browser cookies success")
        except BusinessLogicError as e:
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="update xhs browser cookies logic error",
                                          extra={"error": repr(e)})
        except Exception as e:
            return self.return_error_info(ApiCode.EXCEPTION, errmsg="update xhs browser cookies unkown error",
                                          extra={"error": repr(e)})