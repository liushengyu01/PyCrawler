# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import argparse

import config
import constant
from pkg.tools.utils import str2bool


def parse_cmd():
    # 读取command arg
    parser = argparse.ArgumentParser(description="Media crawler program.")
    parser.add_argument(
        "--platform",
        type=str,
        help="Media platform select (xhs | dy | ks | bili | wb | tieba | zhihu)",
        choices=[
            constant.XHS_PLATFORM_NAME,
            constant.DOUYIN_PLATFORM_NAME,
            constant.KUAISHOU_PLATFORM_NAME,
            constant.WEIBO_PLATFORM_NAME,
            constant.BILIBILI_PLATFORM_NAME,
            constant.TIEBA_PLATFORM_NAME,
            constant.ZHIHU_PLATFORM_NAME,
        ],
        default=config.PLATFORM,
    )
    parser.add_argument(
        "--type",
        type=str,
        help="crawler type (search | detail | creator)",
        choices=["search", "detail", "creator"],
        default=config.CRAWLER_TYPE,
    )
    parser.add_argument(
        "--keywords", type=str, help="please input keywords", default=config.KEYWORDS
    )
    parser.add_argument(
        "--start", type=int, help="number of start page", default=config.START_PAGE
    )
    parser.add_argument(
        "--save_data_option",
        type=str,
        help="where to save the data (csv or db or json)",
        choices=["csv", "db", "json"],
        default=config.SAVE_DATA_OPTION,
    )
    parser.add_argument(
        "--download",
        type=str2bool,
        help="whether to download media content (yes/no)",
        default=config.DOWNLOAD_MEDIA,
    )

    args = parser.parse_args()

    # override config
    config.PLATFORM = args.platform
    config.CRAWLER_TYPE = args.type
    config.START_PAGE = args.start
    config.KEYWORDS = args.keywords
    config.SAVE_DATA_OPTION = args.save_data_option
    config.DOWNLOAD_MEDIA = args.download
