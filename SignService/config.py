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
import os

from tornado.options import define

from pkg.utils import custom_getenv

IS_DEBUG = custom_getenv("IS_DEBUG", True)
user_cookie_name = 'mediacrawler_sgn_srv'
cookie_secret = "k1tFJHDQTL+8zmFf5Pd4W82ObesAhUlooxC/HLdyZqw='"
# xsrf_cookies设置成True就以为这所有的post（非get请求）都必须加上 _xsrf 参数
xsrf_cookies = False
# cookie 过期时间, 设置为 24 小时
EXPIRE_DURATION = 60 * 60 * 24
# logging level
logger_level = os.getenv("LOGGER_LEVEL", logging.INFO)

app_port = custom_getenv("APP_PORT", 8989)
app_address = custom_getenv("APP_ADDRESS", "0.0.0.0")
define(name="port", default=app_port, type=int, help="app http listen port")
define(name="address", default=app_address, type=str, help="app http listen address")

# 设置为True不会打开浏览器（无头浏览器）
# 设置False会打开一个浏览器
playwright_headless = custom_getenv("playwright_headless", False)

# 签名类型，js版本（可选playwright，但是不建议使用）
sign_type = custom_getenv("SIGN_TYPE", "javascript")

# playwright版本的配置cookies配置，不建议使用，只是为了合理抽象一个sign服务，有不同的签名实现
# 抖音和XHS已经过滑块的cookie，xhs需要登录态的cookies
xhs_fixed_cookie = "xsecappid=xhs-pc-web;acw_tc=197dbac640990d15505bfb4922a3830d9c4789806a91f1b7015cb01ee5c5647c;websectiga=16f444b9ff5e3d7e258b5f7674489196303a0b160e16647c6c2b4dcb609f4134;webBuild=4.28.5;sec_poison_id=c74bb98d-3811-452d-91f3-57912cfbfeda;web_session=040069b5e1e37c6e09cf82ca83344b20e9127f;gid=yjyqYddY2fqjyjyqYddWY7EKWJ1WuIYWDSTjuTEIkk0yWxq8UiVfhV888JqWJ228y8y0fSYj;a1=19138ee7872l7zn87bck9ngga17pfjdv3uzhjw6kw30000237255;abRequestId=604534c9-554c-5929-a7d3-2cc94c6dee7b;unread={%22ub%22:%2266b5b1d9000000001e01c2aa%22%2C%22ue%22:%226694d6b9000000000d00dce7%22%2C%22uc%22:25};webId=f4cb6698411a26950da80b8c92344ee2"
dy_fixed_cookie = "__ac_nonce=066b4ee10004f0469e70a; __ac_signature=_02B4Z6wo00f01lnMNZgAAIDDuQf-Sp1nZbZZ.DEAAPDWf2; ttwid=1%7CrmqTgfdiWXHBM5K5hRoA3cZVU2Q5Olqy_9Vwaq5VKjg%7C1723133456%7C336feef995fdf33daeb6b1d964f56d95e5adb357e55dd2d2b3caa2f135690324; UIFID_TEMP=dea138cbdc2046bf3e7655429b003b549d1072cfdebbb5c0810783ab5e8f96eaff77044b04d0c8c4cba45f04e40fbb0d4d219741e5fb852f4e970908e8dea7dd7643d86519b808f48b6c10fe189e4a00; douyin.com; device_web_cpu_core=4; device_web_memory_size=8; architecture=amd64; dy_swidth=1920; dy_sheight=1080; s_v_web_id=verify_lzlh65dq_UKLp3RIJ_q2Dl_4bFw_BDPi_hn4mJOx3SbQ1; csrf_session_id=6852b05bda5a6ce15749cb12835aa7f5; fpk1=U2FsdGVkX19kcR6VnlaNST8rJ9ViDXhGDyscJ0N2FfAxJEGCTrxf+Fii55MR1Aqnj0Ph3yjl6qosgYWe2DMD7Q==; fpk2=19cc53d247c0d02221855ee25c52c3e1; strategyABtestKey=%221723133460.552%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; passport_csrf_token=3b4fda274d54025c321754dd66dce1ba; passport_csrf_token_default=3b4fda274d54025c321754dd66dce1ba; bd_ticket_guard_client_web_domain=2; UIFID=dea138cbdc2046bf3e7655429b003b549d1072cfdebbb5c0810783ab5e8f96eaff77044b04d0c8c4cba45f04e40fbb0d7b0a01eb822e46dc179720a5a138bdcd3749053c54b9ec5426a54b6aab0c351f9ef2104b89dc8488e77e1f7fd99b8086f2f0d217853fbdfeb07c1a2fe59e3de99ac25efa5b870e65d34d5e6e00a5a4ee667169f797b56eab8bd6bc4eaaf3c4f17ed899bdeb989eb8e014522ee1409817; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1920%2C%5C%22screen_height%5C%22%3A1080%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A4%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A100%7D%22; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A0%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A1%7D%22; home_can_add_dy_2_desktop=%221%22; biz_trace_id=5d461173; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCQ1RFUnJ1Q3JuLzRad1ZiMUQwYi9WZ1dHVWhkb0hIeHozOWRWL2EzZzVkSm1reXArczJXdkwyanlWNTNGUE9VL3BJcFFUY0EwdE9Qd0dxUDM5SVJSSFk9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoxfQ%3D%3D; IsDouyinActive=true"
bilibili_fixed_cookie = "b_lsid=E693ED2D_19152DB2244;home_feed_column=5;buvid4=65E9F6D6-920A-9DE5-7759-59C871D5FF5397346-024081420-bhxxTN9MAnMLZBpqlqjICQ%3D%3D;CURRENT_FNVAL=4048;header_theme_version=CLOSE;buvid3=FB8124D9-A1DF-D1F9-A8D9-FC9066FAC05A96823infoc;b_nut=1723667896;_uuid=2D3BB9E3-9AA3-27D9-42C4-2C514F7DAD10D97127infoc;bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MjM5MjcxOTksImlhdCI6MTcyMzY2NzkzOSwicGx0IjotMX0.MCCpMZR9jr5Ec7W9xl-i3o9O3WpbW-dsho4ch9Y8P4A;bili_ticket_expires=1723927139;bmg_af_switch=1;bmg_src_def_domain=i2.hdslb.com;browser_resolution=2079-1173;buvid_fp=d4daeb9dce7fc1b95459fb10a46cd9e8;enable_web_push=DISABLE"
