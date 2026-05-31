import logging
import os
from typing import List, Set

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_env_var(key: str, default: str = None) -> str:
    """Get environment variable with optional default value."""
    value = os.getenv(key, default)
    if not value:
        raise ValueError(f"Required environment variable '{key}' not found")
    return value


def load_keywords_from_csv(csv_path: str) -> List[str]:
    """Load keywords from CSV file."""
    keywords = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:
                if line.strip():
                    keyword = line.split(',')[0].strip()
                    keywords.append(keyword)
        logger.info(f"Loaded {len(keywords)} keywords from {csv_path}")
        return keywords
    except Exception as e:
        logger.error(f"Error loading keywords from {csv_path}: {str(e)}")
        raise


def deduplicate_patents(patents: List[dict]) -> List[dict]:
    """Remove duplicate patents by patent ID."""
    seen_ids: Set[str] = set()
    deduplicated = []
    for patent in patents:
        patent_id = patent.get('patentNumber', '')
        if patent_id not in seen_ids:
            seen_ids.add(patent_id)
            deduplicated.append(patent)
    logger.info(f"Deduplicated patents: {len(patents)} -> {len(deduplicated)}")
    return deduplicated


def log_error(error_message: str) -> None:
    """Log error message."""
    logger.error(error_message)
