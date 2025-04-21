"""Configuration settings for the GitHub changelog Slack bot."""

import os
from typing import Final
from dotenv import load_dotenv


load_dotenv()

# Slack Configuration (always required)
SLACK_TOKEN: Final[str] = os.getenv("SLACK_TOKEN")
if not SLACK_TOKEN:
    raise ValueError("SLACK_TOKEN environment variable is not set")
CHANNEL_ID: Final[str] = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is not set")

# GitHub Configuration (required for GitHub Actions)
def get_github_config(local_mode: bool = False):
    """Get GitHub configuration, making it optional in local mode."""
    if local_mode:
        return {
            "REPO_OWNER": os.getenv("REPO_OWNER", ""),
            "REPO_NAME": os.getenv("REPO_NAME", ""),
            "WORKFLOW_NAME": os.getenv("WORKFLOW_NAME", ""),
            "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "")
        }
    else:
        REPO_OWNER = os.getenv("REPO_OWNER")
        REPO_NAME = os.getenv("REPO_NAME")
        WORKFLOW_NAME = os.getenv("WORKFLOW_NAME")
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

        if not all([REPO_OWNER, REPO_NAME, WORKFLOW_NAME, GITHUB_TOKEN]):
            raise ValueError(
                "GitHub configuration environment variables are not set")

        return {
            "REPO_OWNER": REPO_OWNER,
            "REPO_NAME": REPO_NAME,
            "WORKFLOW_NAME": WORKFLOW_NAME,
            "GITHUB_TOKEN": GITHUB_TOKEN
        }


# RSS Feed Configuration
RSS_FEED_URL: Final[str] = "https://github.blog/changelog/feed/"
TIMESTAMP_FILE: Final[str] = 'artifact-file.txt'

# API Configuration
REQUEST_TIMEOUT: Final[int] = 30  # seconds
