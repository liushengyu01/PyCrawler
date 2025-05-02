# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


from contextvars import ContextVar

from pkg.playwright.bilibili_manager import BilibiliPlaywrightManager
from pkg.playwright.douyin_manager import DouYinPlaywrightManager
from pkg.playwright.xhs_manager import XhsPlaywrightManager

request_id_var: ContextVar = ContextVar("request_id")
xhs_manager_ctx_var: ContextVar[XhsPlaywrightManager] = ContextVar("xhs_manager_ctx_var")
dy_manager_ctx_var: ContextVar[DouYinPlaywrightManager] = ContextVar("dy_manager_ctx_var")
bilibili_manager_ctx_var: ContextVar[BilibiliPlaywrightManager] = ContextVar("bilibili_manager_ctx_var")