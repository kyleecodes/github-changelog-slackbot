"""Script to run the GitHub changelog Slack bot locally."""

import os
import sys
from dotenv import load_dotenv
from fetch_changelog import main as fetch_changelog_main


def main():
    """Load environment variables and run the changelog fetch script."""
    load_dotenv()

    # Check if .env file exists
    if not os.path.exists('.env'):
        print("Error: .env file not found!")
        print(
            "Please create a .env file based on .env.example and fill in your credentials.")
        sys.exit(1)

    # Run the main script in local mode
    fetch_changelog_main(local_mode=True)


if __name__ == "__main__":
    main()
