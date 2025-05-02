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
from typing import Dict, List

from db import AsyncMysqlDB
from pkg.account_pool import AccountInfoModel, AccountStatusEnum
from var import media_crawler_db_var


async def query_platform_accounts_cookies(platform_name: str, cookie_status: int = 0) -> List[Dict]:
    """
    根据指定平台名称查询账号cookies列表
    Args:
        platform_name: xhs | dy | ks | wb | bili | tieba | zhihu
        cookie_status: 0: 正常状态 -1: 异常状态

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    sql: str = f"select * from crawler_cookies_account where platform_name = '{platform_name}' and status = {cookie_status} order by update_time asc"
    return await async_db_conn.query(sql)


async def update_account_status_by_id(account_id: int , account: AccountInfoModel) -> int:
    """
    更新账号状态
    Args:
        account_id:
        account:

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    update_value = {
        "status": account.status.value,
    }
    if account.status == AccountStatusEnum.INVALID:
        update_value["invalid_timestamp"] = account.invalid_timestamp

    return await async_db_conn.update_table("crawler_cookies_account", update_value, "id", account_id)
