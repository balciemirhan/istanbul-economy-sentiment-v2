import logging
import requests

logger = logging.getLogger(__name__)

class XAPIClient:
    BASE_URL = "https://api.x.com/2"

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        self.total_requests = 0

    def _make_request(self, url: str, params: dict = None) -> dict:
        self.total_requests += 1
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            logger.error(f"API Hatası: {response.status_code} - {response.text}")
            raise Exception(f"API Error: {response.status_code}")

        data = response.json()
        
        # Rate limit header'larını al ve logla
        remaining = response.headers.get('x-ratelimit-remaining', 'N/A')
        limit = response.headers.get('x-ratelimit-limit', 'N/A')
        logger.info(f"📊 Rate limit: {remaining}/{limit} kaldı")
        
        return data

    def get_recent_tweets(self, query: str, start_time: str = None, end_time: str = None,
                          max_results: int = 100, next_token: str = None) -> dict:
        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,lang,author_id,id,text",
            "expansions": "author_id",
            "user.fields": "username,name,public_metrics"
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if next_token:
            params["next_token"] = next_token

        return self._make_request(f"{self.BASE_URL}/tweets/search/recent", params)
