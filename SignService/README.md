## 免责声明

本仓库的所有内容仅供学习使用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。

我们提供的爬虫仅能获取抖音、快手、哔哩哔哩、小红书、百度贴吧、微博平台上**公开的信息**，

我们强烈反对任何形式的隐私侵犯行为。如果你使用本项目进行了侵犯他人隐私的行为，我们将与你保持距离，并支持受害者通过法律手段维护自己的权益。<br>

对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件<br>

## MediaCrawlerSignSrv 平台请求签名服务
将请求签名的功能从MediaCrawler中独立出来，作为一个独立的服务，方便调用。
另外，这个服务也可以作为一个独立的服务，供其他项目调用。

## 项目部署安装

### 本地安装
> python推荐版本：3.9.6， requirements.txt中的依赖包是基于这个版本的，其他版本可能会有依赖装不上问题。
> 
> 本地安装签名服务时，需要nodejs环境，版本大于等于16以上

#### 1、新建Pro版本目录
```shell
# 新建目录MediaCrawlerPro并进入
mkdir MediaCrawlerPro
cd MediaCrawlerPro
```

##### 2、克隆签名服务仓库并安装依赖
```shell
# 先克隆签名服务仓库并安装依赖
git clone https://github.com/MediaCrawlerPro/MediaCrawlerPro-SignSrv
cd MediaCrawlerPro-SignSrv

# 创建虚拟环境并安装签名服务的依赖，
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

##### 3、启动签名服务
> 本地安装签名服务时，需要nodejs环境，版本大于等于16以上
```shell
python app.py 
```

### Docker安装
```shell
docker build -t mediacrawler_signsrv .
docker run -p 8989:8989 -e LOGGER_LEVEL=ERROR mediacrawler_signsrv
```

## 项目目录结构说明
[MediaCrawlerPro-SignSrv 目录结构说明](./project_tree.md)