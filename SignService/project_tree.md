### MediaCrawlerPro-SignSrv 目录结构说明
```tree
.
├── apis                         # API接口目录
│   ├── base_handler.py          # Tornado Handler的基础类
│   ├── bilibili.py              # B站签名API接口
│   ├── douyin.py                # 抖音签名API接口
│   ├── xiaohongshu.py           # 小红书签名API接口
│   └── zhihu.py                 # 知乎签名API接口
├── constant                     # 常量定义目录
│   ├── base_constant.py         # 基础常量定义
│   └── error_code.py            # 错误代码定义
├── logic                        # 业务签名逻辑目录
│   ├── bilibili                 # B站签名业务逻辑
│   │   ├── bilibili_logic.py    # B站签名业务逻辑实现
│   │   └── help.py              # B站辅助函数
│   ├── douyin                   # 抖音签名业务逻辑
│   │   └── douyin_logic.py      # 抖音签名业务逻辑实现
│   ├── xhs                      # 小红书签名业务逻辑
│   │   ├── help.py              # 小红书辅助函数
│   │   └── xhs_logic.py         # 小红书签名业务逻辑实现
│   └── zhihu                    # 知乎签名业务逻辑
│       └── zhihu_logic.py       # 知乎签名业务逻辑实现
├── params                       # 参数定义目录
│   ├── base_model.py            # 基础参数模型
│   ├── bilibili_sign.py         # B站签名相关参数
│   ├── douyin_sign.py           # 抖音签名相关参数
│   ├── xiaohongshu_sign.py      # 小红书签名相关参数
│   └── zhihu_sign.py            # 知乎签名相关参数
├── pkg                          # 项目包目录
│   ├── cache                    # 缓存相关目录
│   │   ├── abs_cache.py         # 抽象缓存类
│   │   ├── cache_factory.py     # 缓存工厂类
│   │   └── local_cache.py       # 本地缓存实现
│   ├── custom_exceptions        # 自定义异常目录
│   │   └── base_exceptions.py   # 基础异常类
│   ├── js                       # JavaScript目录
│   │   ├── douyin.js            # 抖音相关JS文件
│   │   ├── stealth.min.js       # 去除浏览器自动化特征的JS
│   │   ├── xhs.js               # 小红书相关JS文件
│   │   └── zhihu.js             # 知乎相关JS文件
│   ├── playwright               # Playwright目录
│   │   ├── bilibili_manager.py  # B站Playwright管理器
│   │   ├── douyin_manager.py    # 抖音Playwright管理器
│   │   ├── manager.py           # 通用Playwright管理器
│   │   └── xhs_manager.py       # 小红书Playwright管理器
│   ├── utils                    # 工具函数目录
│   │   ├── base_utils.py        # 基础工具函数
│   │   └── crawler_util.py      # 爬虫工具函数
│   └── async_http_client.py     # 异步HTTP客户端
├── test                         # 测试目录
│   └── test_custom_getenv.py    # 自定义环境变量测试
├── Dockerfile                   # Docker配置文件
├── LICENSE                      # 开源协议
├── README.md                    # 项目说明文档
├── app.py                       # 应用程序入口
├── config.py                    # 配置文件
├── context_vars.py              # 上下文变量定义
├── img.png                      # 项目截图
├── project_tree.md              # 项目目录结构说明
├── requirements.txt             # 依赖项说明文件
└── urls.py                      # URL路由配置
```