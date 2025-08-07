#!/usr/bin/env python3
"""
Simple Real-Time Webhook Listener
Webhook geldiğinde YAML içeriğini okur ve güvenlik analizi yapar
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import time
import logging
import re
from datetime import datetime
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load .env file with explicit path and override
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

from src.database.database import DatabaseManager
from src.utils.log_manager import log_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Azure DevOps config from environment variables
organization = os.getenv('AZURE_ORGANIZATION', 'your-organization')
project = os.getenv('AZURE_PROJECT', 'your-project')
pat = os.getenv('AZURE_PAT', 'your-personal-access-token')
devops_server_url = os.getenv('AZURE_DEVOPS_SERVER_URL', 'https://dev.azure.com')

# Notifications config from environment variables
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')

# Webhook config from environment
WEBHOOK_SERVER_URL = os.getenv('WEBHOOK_SERVER_URL', 'https://your-ngrok-url.ngrok-free.app')

class SlackNotifier:
    """Slack notification sender"""
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_security_alert(self, build_info, findings):
        """Sends security alert to Slack"""
        try:
            # Simple Slack message
            message = {
                "text": f"🚨 SECURITY ALERT - Build: {build_info['build_number']} - Pipeline: {build_info['definition_name']}"
            }
            
            # Add patterns
            if findings:
                pattern_list = []
                
                # List all patterns
                for finding in findings:
                    pattern_name = finding['pattern']
                    count = finding['count']
                    pattern_list.append(f"• {pattern_name}: {count} instances")
                
                # Add patterns
                message["text"] += f"\n\n🔴 Detected Patterns:\n" + "\n".join(pattern_list)
                
                # Add total count
                total_patterns = len(findings)
                message["text"] += f"\n\n📊 Summary: {total_patterns} patterns detected"
            
            # Send to Slack
            response = requests.post(self.webhook_url, json=message)
            if response.status_code == 200:
                logger.info("✅ Slack notification sent")
            else:
                logger.error(f"❌ Failed to send Slack notification: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
    
    def _format_findings(self, findings):
        """Formats detected patterns"""
        formatted = []
        for finding in findings:
            pattern_name = finding['pattern'].upper()
            count = finding['count']
            examples = finding['matches'][:2]  # First 2 examples
            
            formatted.append(f"• *{pattern_name}*: {count} instances")
            for example in examples:
                formatted.append(f"  `{example[:50]}...`")
        
        return "\n".join(formatted)

class SecurityAnalyzer:
    """Advanced security analyzer"""
    
    def __init__(self):
        # Use the existing security analyzer from src.utils
        pass
    
    def analyze_yaml_content(self, yaml_content):
        """Analyzes YAML content for security issues"""
        # Use the method from src.utils.security_analyzer directly
        from src.utils.security_analyzer import SecurityAnalyzer as BaseSecurityAnalyzer
        findings = BaseSecurityAnalyzer.analyze_yaml_content(yaml_content)
        
        # Debug: Check custom patterns
        custom_count = len([f for f in findings if f.get('is_custom', False)])
        logger.info(f"🔍 Security analysis: {len(findings)} findings ({custom_count} custom)")
        
        # Debug: List all findings
        for finding in findings:
            logger.info(f"   - {finding['pattern']}: {finding['count']} (is_custom: {finding.get('is_custom', False)})")
        
        return findings

class SimpleWebhookListener:
    """Simple webhook listener"""
    
    def __init__(self):
        self.webhook_url = WEBHOOK_SERVER_URL
        self.security_analyzer = SecurityAnalyzer()
        self.slack_notifier = SlackNotifier(SLACK_WEBHOOK_URL)
        self.db_manager = DatabaseManager()
        
        # Debug: Print Slack webhook URL
        print(f"🔧 Debug: Slack Webhook URL = {SLACK_WEBHOOK_URL}")
        
        # Use Slack URL from environment
        print(f"🔧 Debug: Using Slack URL from environment: {SLACK_WEBHOOK_URL}")
        
        # Set event counter to current events in webhook server
        current_events = self.get_webhook_events()
        if current_events and 'events' in current_events:
            self.last_event_count = len(current_events['events'])
            print(f"🔄 Event counter set: {self.last_event_count} current events")
        else:
            self.last_event_count = 0
            print("🔄 Event counter reset - waiting for new events")
        
    def get_webhook_events(self):
        """Gets webhook events"""
        try:
            response = requests.get(f"{self.webhook_url}/events")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get webhook events: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Webhook connection error: {e}")
            return None
    
    def get_yaml_content(self, definition_id):
        """Gets pipeline YAML content"""
        try:
            # First get pipeline definition
            definition_url = f'{devops_server_url}/{organization}/{project}/_apis/build/definitions/{definition_id}?api-version=6.0'
            definition_response = requests.get(definition_url, auth=HTTPBasicAuth('', pat))
            
            if definition_response.status_code != 200:
                logger.error(f"Failed to get pipeline definition: {definition_response.status_code}")
                return None, None
            
            definition_data = definition_response.json()
            process = definition_data.get('process', {})
            yaml_filename = process.get('yamlFilename', 'azure-pipelines.yml')
            
            logger.info(f"📋 YAML file for Pipeline {definition_id}: {yaml_filename}")
            
            # Get YAML file
            url = f'{devops_server_url}/{organization}/{project}/_apis/git/repositories/cc0db49e-774d-4dc7-b789-6fbda107c4c7/items?path=/{yaml_filename}&api-version=6.0'
            response = requests.get(url, auth=HTTPBasicAuth('', pat))
            
            if response.status_code == 200:
                return response.text, yaml_filename
            else:
                logger.error(f"Failed to get YAML file: {response.status_code} - {yaml_filename}")
                return None, None
        except Exception as e:
            logger.error(f"YAML retrieval error: {e}")
            return None, None
    
    def analyze_webhook_event(self, event):
        """Analyzes webhook event"""
        try:
            data = event.get('data', {})
            event_type = data.get('eventType')
            resource = data.get('resource', {})
            
            if event_type == 'build.complete':
                build_id = resource.get('id')
                build_number = resource.get('buildNumber')
                definition = resource.get('definition', {})
                definition_id = definition.get('id')
                definition_name = definition.get('name')
                
                logger.info(f"🔔 New Build Event: {build_number} (ID: {build_id})")
                logger.info(f"   Definition: {definition_name} (ID: {definition_id})")
                
                # Log webhook event
                log_manager.log_webhook('INFO', 'New build event received',
                                      build_id=build_id, build_number=build_number,
                                      definition_name=definition_name, definition_id=definition_id)
                
                # Save event to database (with duplicate check)
                event_data = {
                    'event_type': event_type,
                    'build_id': build_id,
                    'build_number': build_number,
                    'definition_id': definition_id,
                    'definition_name': definition_name,
                    'raw_data': resource
                }
                
                # Duplicate event check
                if self.db_manager.event_exists(build_id, build_number):
                    logger.info(f"⏭️ Duplicate event skipped: Build {build_number}")
                    return False
                
                webhook_event_id = self.db_manager.save_webhook_event(event_data)
                logger.info(f"💾 Event saved to database: ID {webhook_event_id}")
                
                # Log database operation
                log_manager.log_database('INFO', 'Webhook event saved',
                                       event_id=webhook_event_id, build_number=build_number,
                                       definition_name=definition_name)
                
                # Get YAML content
                yaml_content, yaml_filename = self.get_yaml_content(definition_id)
                if yaml_content:
                    logger.info(f"✅ YAML content received ({len(yaml_content)} characters)")
                    
                    # Perform security analysis
                    security_findings = self.security_analyzer.analyze_yaml_content(yaml_content)
                    
                    if security_findings:
                        logger.warning("🚨 SECURITY ALERT! Dangerous patterns detected:")
                        
                        # Log security alert
                        log_manager.log_security('WARNING', 'Dangerous patterns detected',
                                               build_id=build_id, build_number=build_number,
                                               definition_name=definition_name,
                                               total_patterns=len(security_findings))
                        
                        for finding in security_findings:
                            logger.warning(f"   🔴 {finding['pattern'].upper()}: {finding['count']} instances found")
                            
                            # Log each pattern in detail
                            log_manager.log_security('WARNING', f"Pattern detected: {finding['pattern']}",
                                                   pattern=finding['pattern'], count=finding['count'],
                                                   build_id=build_id, build_number=build_number)
                            
                            for match in finding['matches'][:3]:  # Show first 3 matches
                                logger.warning(f"      Example: {match[:100]}...")
                        
                        # Save security findings to database
                        self.db_manager.save_security_findings(webhook_event_id, security_findings)
                        
                        # Send Slack notification
                        build_info = {
                            'build_id': build_id,
                            'build_number': build_number,
                            'definition_name': definition_name,
                            'definition_id': definition_id
                        }
                        self.slack_notifier.send_security_alert(build_info, security_findings)
                        
                        # Log Slack notification
                        log_manager.log_audit('Slack notification sent',
                                            action='slack_notification', build_id=build_id,
                                            build_number=build_number, definition_name=definition_name,
                                            total_patterns=len(security_findings))
                        
                    else:
                        logger.info("✅ Security analysis: No dangerous patterns detected")
                    
                    # Save pipeline analysis to database
                    total_patterns = len(security_findings) if security_findings else 0
                    total_risk_score = sum(finding.get('risk_score', 0) for finding in security_findings) if security_findings else 0
                    
                    self.db_manager.save_pipeline_analysis(
                        webhook_event_id, 
                        yaml_content, 
                        yaml_filename, 
                        total_patterns, 
                        total_risk_score
                    )
                    
                    # Mark event as processed
                    self.db_manager.update_webhook_event_processed(webhook_event_id)
                    
                    # Save YAML to logs folder (for backup)
                    import os
                    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
                    os.makedirs(logs_dir, exist_ok=True)
                    filename = os.path.join(logs_dir, f"yaml_build_{build_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml")
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(yaml_content)
                    
                    logger.info(f"💾 YAML file saved: {filename}")
                    
                    # Show first 5 lines
                    lines = yaml_content.split('\n')[:5]
                    logger.info("📄 YAML Content (first 5 lines):")
                    for line in lines:
                        logger.info(f"   {line}")
                    
                else:
                    logger.warning("❌ Failed to get YAML content")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Event analysis error: {e}")
            
            # Log error
            log_manager.log_error('Event analysis error',
                                 error=str(e), build_id=build_id if 'build_id' in locals() else None,
                                 build_number=build_number if 'build_number' in locals() else None)
            return False
    
    def run(self):
        """Main listening loop"""
        logger.info("🚀 Simple Webhook Listener started")
        logger.info(f"📡 Webhook URL: {self.webhook_url}")
        logger.info("🔍 Security analysis active")
        if SLACK_WEBHOOK_URL != "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK":
            logger.info("📱 Slack notifications active")
        else:
            logger.warning("⚠️ Slack webhook URL not configured - notifications will not be sent")
        logger.info("⏳ Listening for events... (Press Ctrl+C to stop)")
        
        try:
            while True:
                # Get webhook events
                events_data = self.get_webhook_events()
                
                if events_data:
                    events = events_data.get('events', [])
                    current_count = len(events)
                    
                    # Check for new events
                    if current_count > self.last_event_count:
                        new_events = events[self.last_event_count:]
                        logger.info(f"🆕 {len(new_events)} new events found")
                        
                        for event in new_events:
                            self.analyze_webhook_event(event)
                        
                        self.last_event_count = current_count
                
                # Wait 5 seconds
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("🛑 Listener stopped")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    listener = SimpleWebhookListener()
    listener.run() 