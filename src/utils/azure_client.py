import requests
from requests.auth import HTTPBasicAuth
import json
import logging
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureDevOpsClient:
    """Azure DevOps API client for pipeline analysis"""
    
    def __init__(self):
        # Get configuration from environment variables
        self.pat = os.getenv('AZURE_PAT', 'your-personal-access-token')
        self.organization = os.getenv('AZURE_ORGANIZATION', 'your-organization')
        self.project = os.getenv('AZURE_PROJECT', 'your-project')
        self.devops_server_url = os.getenv('AZURE_DEVOPS_SERVER_URL', 'https://dev.azure.com')
        self.api_version = os.getenv('AZURE_API_VERSION', '6.0')
        
        self.auth = HTTPBasicAuth('', self.pat)
        self.base_url = f'{self.devops_server_url}/{self.organization}/{self.project}'
    
    def get_pipeline_definition(self, definition_id: int) -> Optional[Dict[str, Any]]:
        """Get pipeline YAML definition"""
        url = f'{self.base_url}/_apis/build/definitions/{definition_id}?api-version={self.api_version}'
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Pipeline definition failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting pipeline definition: {e}")
            return None
    
    def get_latest_build(self, definition_id: int) -> Optional[Dict[str, Any]]:
        """Get latest build for pipeline"""
        url = f'{self.base_url}/_apis/build/builds?definitions={definition_id}&$top=1&api-version={self.api_version}'
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                builds = response.json().get('value', [])
                return builds[0] if builds else None
            else:
                logger.error(f"Get latest build failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting latest build: {e}")
            return None
    
    def get_build_timeline(self, build_id: int) -> Optional[Dict[str, Any]]:
        """Get build timeline"""
        url = f'{self.base_url}/_apis/build/builds/{build_id}/timeline?api-version={self.api_version}'
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get build timeline failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting build timeline: {e}")
            return None
    
    def get_log_content(self, build_id: int, log_id: int) -> Optional[str]:
        """Get log content"""
        url = f'{self.base_url}/_apis/build/builds/{build_id}/logs/{log_id}?api-version={self.api_version}'
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Get log content failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting log content: {e}")
            return None
    
    def get_build_details(self, build_id: int) -> Optional[Dict[str, Any]]:
        """Get build details"""
        url = f'{self.base_url}/_apis/build/builds/{build_id}?api-version={self.api_version}'
        
        try:
            response = requests.get(url, auth=self.auth)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Get build details failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting build details: {e}")
            return None 