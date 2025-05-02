### MediaCrawlerPro-Python目录结构如下所示：
```tree
.
├── base                                                # 基础类目录
│   └── base_crawler.py                                 # 抽象类定义
├── cmd_arg                                             # 命令行参数目录
│   └── arg.py                                          # 命令行参数解析
├── config                                              # 配置文件目录
│   ├── README.md                                       # 配置文件说明
│   ├── accounts_cookies.xlsx                           # excel账号池模板
│   ├── base_config.py                                  # 基础配置
│   ├── db_config.py                                    # 数据库配置
│   ├── proxy_config.py                                 # 代理配置
│   └── sign_srv_config.py                              # 签名服务配置
├── constant                                            # 常量目录
│   ├── baidu_tieba.py                                  # 百度贴吧常量
│   ├── base_constant.py                                # 基础常量
│   ├── bilibili.py                                     # B站常量
│   ├── douyin.py                                       # 抖音常量
│   ├── kuaishou.py                                     # 快手常量
│   ├── weibo.py                                        # 微博常量
│   ├── xiaohongshu.py                                  # 小红书常量
│   └── zhihu.py                                        # 知乎常量
├── data                                                # 数据目录
├── docs                                                # 文档目录
├── media_platform                                      # 平台爬虫实现目录
│   ├── bilibili                                        # B站爬虫实现
│   │   ├── client.py                                   # B站客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── exception.py                                # 异常定义处理
│   │   ├── field.py                                    # 字段定义
│   │   └── help.py                                     # 辅助函数
│   ├── douyin                                          # 抖音爬虫实现
│   │   ├── client.py                                   # 抖音客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── exception.py                                # 异常定义处理
│   │   ├── field.py                                    # 字段定义
│   │   └── help.py                                     # 辅助函数
│   ├── kuaishou                                        # 快手爬虫实现
│   │   ├── graphql                                     # GraphQL查询目录
│   │   │   ├── comment_list.graphql                    # 评论列表查询
│   │   │   ├── search_query.graphql                    # 搜索查询
│   │   │   ├── video_detail.graphql                    # 视频详情查询
│   │   │   ├── vision_profile.graphql                  # 用户主页查询
│   │   │   ├── vision_profile_photo_list.graphql       # 图片列表查询
│   │   │   ├── vision_profile_user_list.graphql        # 用户列表查询
│   │   │   └── vision_sub_comment_list.graphql         # 子评论列表查询
│   │   ├── client.py                                   # 快手客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── exception.py                                # 异常定义处理
│   │   └── graphql.py                                  # GraphQL处理
│   ├── tieba                                           # 百度贴吧爬虫实现
│   │   ├── client.py                                   # 贴吧客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── field.py                                    # 字段定义
│   │   └── help.py                                     # 辅助函数
│   ├── weibo                                           # 微博爬虫实现
│   │   ├── client.py                                   # 微博客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── exception.py                                # 异常定义处理
│   │   ├── field.py                                    # 字段定义
│   │   └── help.py                                     # 辅助函数
│   ├── xhs                                             # 小红书爬虫实现
│   │   ├── client.py                                   # 小红书客户端API
│   │   ├── core.py                                     # 主流程逻辑
│   │   ├── exception.py                                # 异常定义处理
│   │   ├── extractor.py                                # 数据提取器
│   │   ├── field.py                                    # 字段定义
│   │   └── help.py                                     # 辅助函数
│   └── zhihu                                           # 知乎爬虫实现
│       ├── client.py                                   # 知乎客户端API
│       ├── core.py                                     # 主流程逻辑
│       ├── exception.py                                # 异常定义处理
│       ├── field.py                                    # 字段定义
│       └── help.py                                     # 辅助函数
├── model                                               # 数据模型目录
│   ├── m_baidu_tieba.py                                # 百度贴吧数据模型
│   ├── m_bilibili.py                                   # B站数据模型
│   ├── m_weibo.py                                      # 微博数据模型
│   ├── m_xiaohongshu.py                                # 小红书数据模型
│   └── m_zhihu.py                                      # 知乎数据模型
├── pkg                                                 # 项目包目录
│   ├── account_pool                                    # 账号池目录
│   │   ├── field.py                                    # 字段定义
│   │   └── pool.py                                     # 账号池实现
│   ├── cache                                           # 缓存目录
│   │   ├── abs_cache.py                                # 缓存抽象类
│   │   ├── cache_factory.py                            # 缓存工厂
│   │   ├── local_cache.py                              # 本地缓存
│   │   └── redis_cache.py                              # redis缓存
│   ├── proxy                                           # IP代理目录
│   │   ├── providers                                   # IP代理提供商目录
│   │   │   └── kuaidl_proxy.py                         # 快代理实现
│   │   ├── base_proxy.py                               # IP代理抽象类
│   │   ├── proxy_ip_pool.py                            # IP代理池实现
│   │   └── types.py                                    # IP代理类型定义
│   ├── rpc                                             # RPC目录
│   │   └── sign_srv_client                             # 签名服务客户端
│   │       ├── sign_client.py                          # 签名客户端实现
│   │       └── sign_model.py                           # 签名模型定义
│   ├── tools                                           # 工具目录
│   │   ├── crawler_util.py                             # 爬虫工具函数
│   │   ├── time_util.py                                # 时间工具函数
│   │   └── utils.py                                    # 通用工具函数
│   └── async_http_client.py                            # 异步HTTP客户端
├── repo                                                # 数据存储目录
│   ├── accounts_cookies                                # 账号池相关的存储
│   │   └── cookies_manage_sql.py                       # mysql账号池管理
│   └── platform_save_data                              # 平台数据存储
│       ├── bilibili                                    # B站数据存储
│       │   ├── bilibili_store_impl.py                  # B站存储实现
│       │   └── bilibili_store_sql.py                   # B站SQL定义
│       ├── douyin                                      # 抖音数据存储
│       │   ├── douyin_store_impl.py                    # 抖音存储实现
│       │   └── douyin_store_sql.py                     # 抖音SQL定义
│       ├── kuaishou                                    # 快手数据存储
│       │   ├── kuaishou_store_impl.py                  # 快手存储实现
│       │   └── kuaishou_store_sql.py                   # 快手SQL定义
│       ├── tieba                                       # 贴吧数据存储
│       │   ├── tieba_store_impl.py                     # 贴吧存储实现
│       │   └── tieba_store_sql.py                      # 贴吧SQL定义
│       ├── weibo                                       # 微博数据存储
│       │   ├── weibo_store_impl.py                     # 微博存储实现
│       │   └── weibo_store_sql.py                      # 微博SQL定义
│       ├── xhs                                         # 小红书数据存储
│       │   ├── xhs_store_impl.py                       # 小红书存储实现
│       │   └── xhs_store_sql.py                        # 小红书SQL定义
│       └── zhihu                                       # 知乎数据存储
│           ├── zhihu_store_impl.py                     # 知乎存储实现
│           └── zhihu_store_sql.py                      # 知乎SQL定义
├── schema                                              # 数据库表结构目录
│   ├── 2024082301_ddl.sql                              # 数据库变更脚本
│   ├── 2024082302_ddl.sql                              # 数据库变更脚本
│   ├── 2024082401_ddl.sql                              # 数据库变更脚本
│   ├── 2024091301_ddl.sql                              # 数据库变更脚本
│   ├── 2024101001_ddl.sql                              # 数据库变更脚本
│   ├── 2024112901_ddl.sql                              # 数据库变更脚本
│   └── tables.sql                                      # 基础表结构
├── static                                              # 静态文件目录
│   ├── img.png                                         # 图片资源
│   ├── img3.png                                        # 图片资源
│   ├── img4.png                                        # 图片资源
│   ├── img5.png                                        # 图片资源
│   ├── img6.png                                        # 图片资源
│   ├── img_1.png                                       # 图片资源
│   └── img_2.png                                       # 图片资源
├── test                                                # 单元测试目录
│   ├── test_expiring_local_cache.py                    # 本地缓存测试
│   ├── test_proxy_ip_pool.py                           # IP代理池测试
│   ├── test_redis_cache.py                             # redis缓存测试
│   └── test_utils.py                                   # 工具函数测试
├── Dockerfile                                          # Docker构建文件
├── LICENSE                                             # 开源协议
├── README.md                                           # 项目说明
├── async_db.py                                         # 异步数据库
├── db.py                                               # 数据库初始化
├── docker-compose.yaml                                 # docker-compose配置
├── main.py                                             # 程序入口
├── mypy.ini                                            # mypy配置
├── raw_directory_tree.txt                              # 目录结构文件
├── requirements.txt                                    # 项目依赖
└── var.py                                              # 上下文变量定义
```
