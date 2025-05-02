import asyncio
import hashlib
import os
from typing import List, Optional, Dict, Union

import aiohttp
import config
from pkg.tools import utils
import ssl


class MediaDownloader:
    def __init__(self):
        self.download_path = config.DOWNLOAD_PATH
        self.timeout = config.DOWNLOAD_TIMEOUT
        self.retry = config.DOWNLOAD_RETRY
        self.chunk_size = config.DOWNLOAD_CHUNK_SIZE
        self.bilibili_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Origin": "https://www.bilibili.com"
        }
        # SSL配置
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def _get_platform_from_url(self, url: str) -> str:
        """
        Get platform name from URL
        Args:
            url: Content URL

        Returns:
            str: Platform name (xhs, douyin, etc.)
        """
        if 'douyin.com' in url or 'douyinvod.com' in url:
            return 'douyin'
        elif 'xiaohongshu.com' in url or 'xhscdn.com' in url:
            return 'xhs'
        elif 'kuaishou.com' in url or 'ksapisrv.com' in url or 'kwaicdn.com' in url:
            return 'kuaishou'
        elif 'bilibili.com' in url or 'hdslb.com' in url:
            return 'bilibili'
        elif 'zhihu.com' in url:
            return 'zhihu'
        else:
            # Try to determine platform from the current crawler
            if hasattr(config, 'PLATFORM') and config.PLATFORM:
                platform_map = {
                    'bili': 'bilibili',
                    'dy': 'douyin',
                    'xhs': 'xhs',
                    'ks': 'kuaishou',
                    'zhihu': 'zhihu'
                }
                return platform_map.get(config.PLATFORM, config.PLATFORM)
            return 'unknown'

    def _get_file_extension(self, content_type: str, url: str) -> str:
        """
        Get file extension based on content type and URL
        Args:
            content_type: Content type (video/image)
            url: Content URL

        Returns:
            str: File extension
        """
        # Try to get extension from URL first
        url_ext = os.path.splitext(url)[1].lower()
        if url_ext and url_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi']:
            return url_ext

        # If no valid extension in URL, use content type
        if content_type == "image":
            return ".jpg"  # Default to jpg for images
        elif content_type == "video":
            return ".mp4"  # Default to mp4 for videos
        return ".jpg"  # Default fallback

    def _generate_filename(self, url: str, content_type: str) -> str:
        """
        Generate unique filename using MD5 hash of URL
        Args:
            url: Content URL
            content_type: Content type (video/image)

        Returns:
            str: Generated filename with extension
        """
        # Create MD5 hash of URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Get appropriate file extension
        ext = self._get_file_extension(content_type, url)
        
        return f"{url_hash}{ext}"

    async def download_content(
        self, content_url: str, content_type: str = None, cookies: Union[Dict, str] = None
    ) -> Optional[str]:
        """
        Download a single media content
        Args:
            content_url: Content URL
            content_type: Content type (video/image)
            cookies: Cookies for authentication (dict or string)

        Returns:
            Optional[str]: Filepath if download successful, None otherwise
        """
        if not content_url:
            utils.logger.error("[MediaDownloader.download_content] Empty content URL")
            return None

        # Get platform from URL
        platform = self._get_platform_from_url(content_url)

        # Generate filename and create download directory
        filename = self._generate_filename(content_url, content_type)
        download_dir = os.path.join(self.download_path, platform, content_type or "unknown")
        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

        # Skip if file already exists
        if os.path.exists(filepath):
            utils.logger.info(f"[MediaDownloader.download_content] File already exists: {filepath}")
            return filepath

        # Download with retries
        for attempt in range(self.retry):
            try:
                # 创建自定义的TCP连接器
                conn = aiohttp.TCPConnector(
                    ssl=self.ssl_context,
                    force_close=True,
                    enable_cleanup_closed=True,
                    limit=10
                )
                
                async with aiohttp.ClientSession(connector=conn) as session:
                    headers = self.bilibili_headers if platform == 'bilibili' else {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    
                    # Handle cookies
                    if cookies:
                        if isinstance(cookies, dict):
                            headers["Cookie"] = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                        else:
                            headers["Cookie"] = cookies

                    # For Bilibili videos, we need to handle the video stream
                    if platform == 'bilibili' and content_type == 'video':
                        # First get the video stream info
                        async with session.get(content_url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                            if response.status == 200:
                                video_info = await response.json()
                                if video_info.get('code') == 0:
                                    # Get all video segments
                                    segments = video_info['data']['durl']
                                    with open(filepath, "wb") as f:
                                        for segment in segments:
                                            segment_url = segment['url']
                                            # Add range header for segment download
                                            headers['Range'] = f"bytes={segment.get('offset', 0)}-{segment.get('offset', 0) + segment.get('size', 0) - 1}"
                                            
                                            # Download segment with retry
                                            for segment_attempt in range(self.retry):
                                                try:
                                                    async with session.get(
                                                        segment_url, 
                                                        headers=headers, 
                                                        timeout=aiohttp.ClientTimeout(total=300),
                                                        ssl=self.ssl_context
                                                    ) as segment_response:
                                                        if segment_response.status in (200, 206):
                                                            async for chunk in segment_response.content.iter_chunked(self.chunk_size):
                                                                f.write(chunk)
                                                            break
                                                        else:
                                                            utils.logger.error(f"[MediaDownloader.download_content] Failed to download segment {segment_url}, status: {segment_response.status}")
                                                except Exception as e:
                                                    if segment_attempt < self.retry - 1:
                                                        await asyncio.sleep(1)
                                                        continue
                                                    raise e
                                    
                                    utils.logger.info(f"[MediaDownloader.download_content] Successfully downloaded: {filepath}")
                                    return filepath
                    else:
                        # Normal download for other platforms or images
                        async with session.get(
                            content_url, 
                            headers=headers, 
                            timeout=aiohttp.ClientTimeout(total=60),
                            ssl=self.ssl_context
                        ) as response:
                            if response.status in (200, 206):  # 接受206状态码
                                with open(filepath, "wb") as f:
                                    async for chunk in response.content.iter_chunked(self.chunk_size):
                                        f.write(chunk)
                                utils.logger.info(f"[MediaDownloader.download_content] Successfully downloaded: {filepath}")
                                return filepath
                            else:
                                utils.logger.error(f"[MediaDownloader.download_content] Failed to download {content_url}, status: {response.status}")
            except Exception as e:
                utils.logger.error(f"[MediaDownloader.download_content] Error downloading {content_url}: {str(e)}")
                if attempt < self.retry - 1:
                    await asyncio.sleep(1)  # Wait before retry
                continue

        return None

    async def download_batch(self, urls: List[str], content_type: str, cookies: Union[Dict, str] = None) -> List[str]:
        """
        Download multiple media contents in batch
        Args:
            urls: List of content URLs
            content_type: Content type (video/image)
            cookies: Cookies for authentication (dict or string)

        Returns:
            List[str]: List of successfully downloaded filepaths
        """
        tasks = [self.download_content(url, content_type, cookies) for url in urls]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r]  # Filter out None results 