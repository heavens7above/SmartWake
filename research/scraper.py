"""
Polite Web Scraper Module for SmartWake Research.
Includes exponential backoff, caching in research/data/raw/cache/, and audit logging.
"""

import os
import sys
import time
import hashlib
import json
import logging
from typing import Optional, Dict, Any
import requests

DEFAULT_SCRAPER_ENDPOINT = "http://api.scraperapi.com"
DEFAULT_SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "5ca589e3263cbb98efebfebe80d7fd35")


class Scraper:
    def __init__(
        self,
        api_key: str = DEFAULT_SCRAPER_API_KEY,
        endpoint: str = DEFAULT_SCRAPER_ENDPOINT,
        cache_dir: Optional[str] = None,
        log_file: Optional[str] = None,
        delay_seconds: float = 1.0,
        max_retries: int = 4,
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.timeout = timeout

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache_dir = cache_dir or os.path.join(base_dir, "data", "raw", "cache")
        self.log_file = log_file or os.path.join(base_dir, "logs", "scraper.log")

        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        self.logger = logging.getLogger("SmartWakeResearchScraper")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            fh = logging.FileHandler(self.log_file, encoding="utf-8")
            fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(fmt)
            self.logger.addHandler(ch)

    def _get_cache_path(self, url: str) -> str:
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, use_proxy: bool = False) -> Optional[requests.Response]:
        time.sleep(self.delay_seconds)
        cache_file = self._get_cache_path(url)

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                self.logger.info(f"CACHE HIT: {url} -> status {cached_data.get('status_code', 200)}")
                resp = requests.Response()
                resp.status_code = cached_data.get("status_code", 200)
                resp._content = cached_data.get("content", "").encode("utf-8")
                resp.url = url
                return resp
            except Exception as e:
                self.logger.warning(f"Cache read error for {url}: {e}")

        for attempt in range(self.max_retries):
            try:
                headers = {"User-Agent": "SmartWakeAcademicResearchBot/1.0 (+http://smartwake-research.edu)"}
                if use_proxy and self.api_key:
                    proxy_params = {"api_key": self.api_key, "url": url}
                    if params:
                        proxy_params.update(params)
                    resp = requests.get(self.endpoint, params=proxy_params, timeout=self.timeout)
                else:
                    resp = requests.get(url, params=params, headers=headers, timeout=self.timeout)

                self.logger.info(f"FETCH [{resp.status_code}] URL: {url} (Attempt {attempt+1})")

                if resp.status_code == 200:
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(
                                {
                                    "url": url,
                                    "status_code": resp.status_code,
                                    "timestamp": time.time(),
                                    "content": resp.text,
                                },
                                f,
                                indent=2,
                            )
                    except Exception as cache_err:
                        self.logger.warning(f"Cache write error for {url}: {cache_err}")
                    return resp
                elif resp.status_code in [429, 500, 502, 503, 504]:
                    sleep_time = (2 ** attempt) * 1.5
                    self.logger.warning(f"HTTP {resp.status_code} for {url}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    self.logger.error(f"HTTP {resp.status_code} for {url}. Not retrying.")
                    return resp
            except Exception as exc:
                sleep_time = (2 ** attempt) * 1.5
                self.logger.warning(f"Exception fetching {url}: {exc}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        self.logger.error(f"Failed to fetch {url} after {self.max_retries} attempts.")
        return None
