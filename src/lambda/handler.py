import os
import logging
import json
from typing import Any, Dict

from patent_api import PatentAPIClient
from slack_notifier import SlackNotifier
from utils import (
    get_env_var,
    load_keywords_from_csv,
    deduplicate_patents,
    log_error
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for patent information retrieval and Slack notification.
    Triggered daily by EventBridge at 20:00.
    """
    try:
        logger.info("Starting patent information retrieval")

        jpo_api_id = get_env_var('JPO_API_ID')
        jpo_api_password = get_env_var('JPO_API_PASSWORD')
        jpo_token_url = get_env_var('JPO_TOKEN_URL')
        slack_webhook_url = get_env_var('SLACK_WEBHOOK_URL')

        keywords_csv_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'config',
            'keywords.csv'
        )

        keywords = load_keywords_from_csv(keywords_csv_path)

        if not keywords:
            log_error("No keywords loaded from CSV")
            return {
                'statusCode': 400,
                'body': json.dumps('No keywords available')
            }

        api_client = PatentAPIClient(
            api_id=jpo_api_id,
            api_password=jpo_api_password,
            token_url=jpo_token_url
        )

        search_results = api_client.search_multiple_keywords(keywords)

        all_patents = []
        for patents in search_results.values():
            all_patents.extend(patents)

        deduplicated_patents = deduplicate_patents(all_patents)
        total_count = len(deduplicated_patents)

        logger.info(f"Total patents found: {total_count}")

        notifier = SlackNotifier(webhook_url=slack_webhook_url)

        success = notifier.send_patent_notification(
            search_results,
            total_count
        )

        if success:
            logger.info("Patent information successfully sent to Slack")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully retrieved and sent patent information',
                    'patents_found': total_count
                })
            }
        else:
            logger.error("Failed to send notification to Slack")
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to send Slack notification')
            }

    except ValueError as e:
        log_error(f"Configuration error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps(f'Configuration error: {str(e)}')
        }
    except Exception as e:
        log_error(f"Unexpected error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Unexpected error: {str(e)}')
        }
