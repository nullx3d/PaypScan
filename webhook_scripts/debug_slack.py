#!/usr/bin/env python3
"""
Debug Slack Notifications
Test Slack webhook functionality
"""

import requests
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get Slack webhook URL from environment
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

def test_slack_notification():
    """Test Slack notification"""
    if not SLACK_WEBHOOK_URL:
        logger.error("❌ SLACK_WEBHOOK_URL not configured")
        return False
    
    if SLACK_WEBHOOK_URL == "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK":
        logger.error("❌ SLACK_WEBHOOK_URL is still using placeholder value")
        return False
    
    try:
        message = {
            "text": "🧪 Test notification from Pipeline Security Scanner"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
    
    if response.status_code == 200:
            logger.info("✅ Slack test notification sent successfully")
            return True
    else:
            logger.error(f"❌ Slack notification failed: {response.status_code}")
            return False
        
except Exception as e:
        logger.error(f"❌ Slack notification error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Slack Notifications...")
    print("=" * 40)
    
    success = test_slack_notification()
    
    if success:
        print("✅ Slack test completed successfully")
    else:
        print("❌ Slack test failed") 