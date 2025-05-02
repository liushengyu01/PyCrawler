# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import random
import time

from model.m_xiaohongshu import NoteUrlInfo, CreatorUrlInfo
from pkg.tools.crawler_util import extract_url_params_to_dict


def base36encode(number, alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError("number must be an integer")

    base36 = ""
    sign = ""

    if number < 0:
        sign = "-"
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def base36decode(number):
    return int(number, 36)


def get_search_id():
    e = int(time.time() * 1000) << 64
    t = int(random.uniform(0, 2147483646))
    return base36encode((e + t))


img_cdns = [
    "https://sns-img-qc.xhscdn.com",
    "https://sns-img-hw.xhscdn.com",
    "https://sns-img-bd.xhscdn.com",
    "https://sns-img-qn.xhscdn.com",
]


def get_img_url_by_trace_id(trace_id: str, format_type: str = "png"):
    return f"{random.choice(img_cdns)}/{trace_id}?imageView2/format/{format_type}"


def get_img_urls_by_trace_id(trace_id: str, format_type: str = "png"):
    return [f"{cdn}/{trace_id}?imageView2/format/{format_type}" for cdn in img_cdns]


def get_trace_id(img_url: str):
    # 浏览器端上传的图片多了 /spectrum/ 这个路径
    return (
        f"spectrum/{img_url.split('/')[-1]}"
        if img_url.find("spectrum") != -1
        else img_url.split("/")[-1]
    )


def parse_note_info_from_note_url(url: str) -> NoteUrlInfo:
    """
    从小红书笔记url中解析出笔记信息
    Args:
        url: "https://www.xiaohongshu.com/explore/66fad51c000000001b0224b8?xsec_token=AB3rO-QopW5sgrJ41GwN01WCXh6yWPxjSoFI9D5JIMgKw=&xsec_source=pc_search"
    Returns:

    """
    note_id = url.split("/")[-1].split("?")[0]
    params = extract_url_params_to_dict(url)
    xsec_token = params.get("xsec_token", "")
    xsec_source = params.get("xsec_source", "")
    return NoteUrlInfo(note_id=note_id, xsec_token=xsec_token, xsec_source=xsec_source)


def parse_creator_info_from_creator_url(url: str) -> CreatorUrlInfo:
    """
    从小红书创作者主页url中解析出创作者信息

    Args:
        url (str): 创作者主页url

    Returns:
        CreatorUrlInfo: 创作者信息
    """
    creator_id = url.split("/")[-1].split("?")[0]
    params = extract_url_params_to_dict(url)
    xsec_token = params.get("xsec_token", "")
    xsec_source = params.get("xsec_source", "")
    return CreatorUrlInfo(
        creator_id=creator_id, xsec_token=xsec_token, xsec_source=xsec_source
    )


if __name__ == "__main__":
    _img_url = "https://sns-img-bd.xhscdn.com/7a3abfaf-90c1-a828-5de7-022c80b92aa3"
    # 获取一个图片地址在多个cdn下的url地址
    # final_img_urls = get_img_urls_by_trace_id(get_trace_id(_img_url))
    final_img_url = get_img_url_by_trace_id(get_trace_id(_img_url))
    print(final_img_url)
