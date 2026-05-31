import requests
import json
import logging
from typing import List, Optional, Dict
from datetime import datetime

logger = logging.getLogger()


class PatentAPIClient:
    """Client for Japanese Patent Office (JPO) API."""

    def __init__(self, api_id: str, api_password: str, token_url: str):
        self.api_id = api_id
        self.api_password = api_password
        self.token_url = token_url
        self.access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """Get access token from JPO API."""
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "grant_type": "password",
                "username": self.api_id,
                "password": self.api_password
            }

            response = requests.post(
                self.token_url,
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get('access_token')

            if not self.access_token:
                raise ValueError("No access token in response")

            token_suffix = self.access_token[-2:] if len(self.access_token) >= 2 else "**"
            logger.info(f"Successfully obtained access token from JPO API (token ends with: ...{token_suffix})")
            return self.access_token

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to obtain access token: {str(e)}"
            logger.error(error_msg)
            raise

    def search_patents(self, keyword: str, max_results: int = 50) -> List[Dict]:
        """Search patents by keyword."""
        if not self.access_token:
            self.get_access_token()

        try:
            search_url = "https://ip-data.jpo.go.jp/api/1/search"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "term": keyword,
                "start": 1,
                "rows": max_results
            }

            response = requests.post(
                search_url,
                json=payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()
            patents = data.get('results', [])

            logger.info(
                f"Found {len(patents)} patents for keyword '{keyword}'"
            )
            return patents

        except requests.exceptions.RequestException as e:
            error_msg = f"Patent search failed for '{keyword}': {str(e)}"
            logger.error(error_msg)
            return []
        except Exception as e:
            error_msg = f"Error parsing patent search response: {str(e)}"
            logger.error(error_msg)
            return []

    def search_multiple_keywords(
        self,
        keywords: List[str],
        max_results: int = 50
    ) -> Dict[str, List[Dict]]:
        """Search patents for multiple keywords."""
        results = {}

        for keyword in keywords:
            logger.info(f"Searching patents for keyword: {keyword}")
            patents = self.search_patents(keyword, max_results)
            results[keyword] = patents

        return results
