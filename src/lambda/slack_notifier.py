import requests
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger()


class SlackNotifier:
    """Send notifications to Slack via Webhook."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_patent_notification(
        self,
        search_results: Dict[str, List[Dict]],
        total_patents: int
    ) -> bool:
        """Send patent search results to Slack."""
        try:
            if total_patents == 0:
                message = self._build_no_results_message()
            else:
                message = self._build_results_message(
                    search_results,
                    total_patents
                )

            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()

            logger.info(f"Successfully sent notification to Slack")
            return True

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send Slack notification: {str(e)}"
            logger.error(error_msg)
            return False

    def _build_results_message(
        self,
        search_results: Dict[str, List[Dict]],
        total_patents: int
    ) -> Dict:
        """Build Slack message with patent results."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "特許情報取得レポート",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*実行日時*: {timestamp}\n*合計件数*: {total_patents}件"
                }
            },
            {
                "type": "divider"
            }
        ]

        for keyword, patents in search_results.items():
            if patents:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*キーワード: {keyword}*\n件数: {len(patents)}件"
                    }
                })

                for idx, patent in enumerate(patents[:5]):
                    patent_text = self._format_patent(patent)
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": patent_text
                        }
                    })

                if len(patents) > 5:
                    blocks.append({
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"... 他 {len(patents) - 5} 件"
                            }
                        ]
                    })

                blocks.append({
                    "type": "divider"
                })

        return {
            "blocks": blocks
        }

    def _build_no_results_message(self) -> Dict:
        """Build Slack message when no patents are found."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "特許情報取得レポート",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*実行日時*: {timestamp}\n\n本日検索キーワードに該当する特許情報は見つかりませんでした。"
                    }
                }
            ]
        }

    def _format_patent(self, patent: Dict) -> str:
        """Format patent information for Slack message."""
        title = patent.get('title', 'N/A')
        patent_number = patent.get('patentNumber', 'N/A')
        publication_date = patent.get('publicationDate', 'N/A')
        applicant = patent.get('applicant', 'N/A')

        return (
            f"• *{title}*\n"
            f"  特許番号: {patent_number}\n"
            f"  出願人: {applicant}\n"
            f"  公開日: {publication_date}"
        )
