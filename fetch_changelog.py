"""A script to fetch GitHub changelog updates and post them to Slack."""

import sys
import logging
from datetime import datetime, timedelta
import io
import zipfile
import feedparser
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

from config import (
    SLACK_TOKEN,
    CHANNEL_ID,
    RSS_FEED_URL,
    TIMESTAMP_FILE,
    REQUEST_TIMEOUT,
    get_github_config,
)


client = WebClient(token=SLACK_TOKEN)


def get_latest_workflow_run_id(github_config):
    """Get the ID of the most recent workflow run."""
    url = f"https://api.github.com/repos/{github_config['REPO_OWNER']}/{github_config['REPO_NAME']}/actions/workflows/{github_config['WORKFLOW_NAME']}/runs"
    headers = {"Authorization": f"Bearer {github_config['GITHUB_TOKEN']}"}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    latest_run = response.json()["workflow_runs"][0]
    return latest_run["id"]


def get_artifact_id(run_id, github_config):
    """Get the artifact ID for a given workflow run."""
    url = f"https://api.github.com/repos/{github_config['REPO_OWNER']}/{github_config['REPO_NAME']}/actions/runs/{run_id}/artifacts"
    headers = {"Authorization": f"Bearer {github_config['GITHUB_TOKEN']}"}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    # Get the first artifact ID (you can adjust if you expect multiple artifacts)
    artifacts = response.json()["artifacts"]
    if artifacts:
        return artifacts[0]["id"]
    else:
        logger.info("No artifacts found for this workflow run. Proceeding with initial setup.")
        return None


def download_and_read_artifact(artifact_id, github_config):
    """Download and read the contents of a GitHub artifact."""
    url = f"https://api.github.com/repos/{github_config['REPO_OWNER']}/{github_config['REPO_NAME']}/actions/artifacts/{artifact_id}/zip"
    headers = {"Authorization": f"Bearer {github_config['GITHUB_TOKEN']}"}

    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    # Load the zip file into memory
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        for file_name in zip_file.namelist():
            logger.debug(f"Reading file: {file_name}")
            with zip_file.open(file_name) as file:
                content = file.read()
                logger.debug(content.decode())
                # Decode if it's a text file
                return content.decode()


def write_artifact(file_path, data):
    """Write data to the artifact file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(data.isoformat())
    logger.info(f"New timestamp written data to artifact: {data}")


def fetch_latest_posts(last_timestamp):
    """Fetches new entries from the RSS feed."""
    feed = feedparser.parse(RSS_FEED_URL)
    new_posts = []

    # Loop through feed entries to find new ones
    for entry in reversed(feed.entries):
        entry_date = datetime(*entry.published_parsed[:6])
        if entry_date > last_timestamp:
            new_posts.append(entry)
            latest_timestamp = entry_date
        else:
            latest_timestamp = last_timestamp

    return new_posts, latest_timestamp


def post_to_slack(new_posts):
    """Posts new updates to Slack."""
    try:
        message = "New GitHub Changelog Updates:\n"

        for post in new_posts:
            message += f"- { ' '.join(post.published.split()[:3]) }: *<{post.link}|{post.title}>*\n"

        client.chat_postMessage(
            channel=CHANNEL_ID,
            icon_emoji=":chart_with_upwards_trend:",
            unfurl_media=False,
            text=message,
        )
        return True

    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e.response['error']}")
        return False


def read_local_timestamp():
    """Read the timestamp from a local file."""
    try:
        with open(TIMESTAMP_FILE, 'r', encoding='utf-8') as file:
            return datetime.fromisoformat(file.read().strip())
    except FileNotFoundError:
        return datetime.now() - timedelta(days=7)


def main(local_mode=False):
    """Main function to orchestrate the changelog fetching and posting process."""
    try:
        github_config = get_github_config(local_mode)

        if local_mode:
            # In local mode, just read from local file
            last_timestamp = read_local_timestamp()
            logger.info(f"Using local timestamp: {last_timestamp}")
        else:
            latest_run_id = get_latest_workflow_run_id(github_config)
            artifact_id = get_artifact_id(latest_run_id, github_config)

            if artifact_id:
                last_timestamp = download_and_read_artifact(
                    artifact_id, github_config)
            else:
                # No artifact exists yet; set last_timestamp to 7 days ago
                last_timestamp = datetime.now() - timedelta(days=7)
                logger.info("No existing artifact found. Using timestamp from 7 days ago as initial value.")
                logger.info(f"Initial timestamp set to: {last_timestamp}")

    except (requests.HTTPError, requests.RequestException) as e:
        logger.error("An error occurred while reading the artifact file:", exc_info=True)
        sys.exit(1)

    try:
        new_posts, latest_timestamp = fetch_latest_posts(last_timestamp)
        if new_posts:
            logger.info(f"Found {len(new_posts)} new posts to share.")
            if post_to_slack(new_posts):
                write_artifact(TIMESTAMP_FILE, latest_timestamp)
                logger.info("Successfully posted updates to Slack and saved new timestamp.")
            else:
                logger.warning("Skipped writing to artifact due to Slack posting failure.")
                sys.exit(1)
        else:
            logger.info("No new posts found since last check.")
            write_artifact(TIMESTAMP_FILE, last_timestamp)
    except (feedparser.CharacterEncodingOverride, ValueError) as e:
        logger.error("An error occurred during post processing:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
