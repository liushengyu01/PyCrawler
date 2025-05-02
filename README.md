# PyCrawler

一个强大的多平台数据采集工具，支持抖音、快手、哔哩哔哩、小红书、百度贴吧、微博等平台的数据采集。本项目包含两个主要组件：

1. `MediaDownloader`: 主爬虫程序
2. `SignService`: 请求签名服务

## 免责声明

本仓库的所有内容仅供学习使用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。

我们提供的爬虫仅能获取各平台上**公开的信息**。我们强烈反对任何形式的隐私侵犯行为。如果你使用本项目进行了侵犯他人隐私的行为，我们将与你保持距离，并支持受害者通过法律手段维护自己的权益。

对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。

## 功能特点

### MediaDownloader（主爬虫程序）
- 支持多个主流平台的数据采集
- 支持账号池管理
- 支持 IP 代理配置
- 支持多种数据存储方式（MySQL、CSV、JSON）
- 内置重试机制，提高爬取稳定性
- 模块化设计，易于扩展

### SignService（签名服务）
- 独立的请求签名服务
- 支持多平台的签名生成
- 支持 Docker 部署
- 易于集成和扩展

## 系统要求

- Python 3.9.6（推荐）
- Node.js >= 16
- MySQL
- Redis
- 操作系统：支持 Windows、Linux、MacOS

## 安装部署

### 1. 克隆仓库
```bash
git clone https://github.com/liushengyu01/PyCrawler.git
cd PyCrawler
```

### 2. 安装签名服务
```bash
cd SignService

# 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/MacOS
pip install -r requirements.txt

# 启动签名服务
python app.py
```

### 3. 安装主爬虫程序
```bash
cd MediaDownloader

# 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/MacOS
pip install -r requirements.txt
```

### 4. 配置
1. 配置账号池和 IP 代理信息（参考 `MediaDownloader/config/README.md`）
2. 配置数据存储方式（推荐使用 MySQL）
3. 在 `config/base_config.py` 中配置搜索关键词等信息

## 使用方法

### 启动爬虫
```bash
python main.py --platform [platform] --type [type]
```

参数说明：
- platform: 平台名称（xhs/douyin/bilibili/kuaishou/weibo/tieba）
- type: 爬取类型（search/user/等）

例如：
```bash
python main.py --platform xhs --type search  # 小红书搜索采集
python main.py --platform douyin --type user  # 抖音用户采集
```

### Docker 部署
项目同时支持 Docker 部署，详细步骤：

1. 构建签名服务
```bash
cd SignService
docker build -t mediacrawler_signsrv .
```

2. 构建并启动整个项目
```bash
cd MediaDownloader
docker-compose up --build
```

## 项目结构
- `MediaDownloader/`: 主爬虫程序
  - `config/`: 配置文件
  - `media_platform/`: 各平台爬虫实现
  - `pkg/`: 工具包
  - `repo/`: 数据存储实现
  - `schema/`: 数据库架构
  
- `SignService/`: 签名服务
  - `apis/`: API 实现
  - `logic/`: 业务逻辑
  - `pkg/`: 工具包

## 注意事项
1. 推荐使用 Python 3.9.6 版本，其他版本可能存在依赖安装问题
2. 使用数据库存储可以避免数据重复
3. 建议配置代理 IP 和账号池以提高爬取稳定性
4. 遵守目标平台的使用条款和规范

## 贡献
欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证
本项目基于 MIT 许可证开源。 