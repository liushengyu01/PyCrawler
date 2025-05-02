# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pkg.tools.downloader import MediaDownloader


class AbstractCrawler(ABC):
    def __init__(self):
        self.downloader = MediaDownloader()

    @abstractmethod
    async def async_initialize(self):
        """
        Asynchronous Initialization
        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def start(self):
        """
        Start the crawler
        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def search(self):
        """
        Search the content
        Returns:

        """
        raise NotImplementedError

    async def download_media_content(self, content_url: str, content_type: str = None) -> Optional[str]:
        """
        Download media content using MediaCrawlerPro-Downloader service
        
        Args:
            content_url: Content URL
            content_type: Content type (video/image)
            
        Returns:
            Path to downloaded file or None if download failed
        """
        return await self.downloader.download_content(content_url, content_type)

    async def download_media_batch(self, content_urls: List[str], content_type: str = None) -> Dict[str, str]:
        """
        Download multiple media contents using MediaCrawlerPro-Downloader service
        
        Args:
            content_urls: List of content URLs
            content_type: Content type (video/image)
            
        Returns:
            Dictionary mapping URLs to downloaded file paths
        """
        return await self.downloader.download_batch(content_urls, content_type)


class AbstractStore(ABC):
    @abstractmethod
    async def store_content(self, content_item: Dict):
        """
        Store the content
        Args:
            content_item:

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def store_comment(self, comment_item: Dict):
        """
        Store the comment
        Args:
            comment_item:

        Returns:

        """
        raise NotImplementedError

    @abstractmethod
    async def store_creator(self, creator: Dict):
        """
        Store the creator
        Args:
            creator:

        Returns:

        """
        raise NotImplementedError


class AbstractApiClient(ABC):
    @abstractmethod
    async def request(self, method, url, **kwargs):
        """
        Send a request
        Args:
            method:
            url:
            **kwargs:

        Returns:

        """
        raise NotImplementedError
