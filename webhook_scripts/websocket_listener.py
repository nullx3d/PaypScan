#!/usr/bin/env python3
"""
WebSocket-based Webhook Listener
Real-time event processing using WebSocket connection
"""

import socketio
import time
import json
import logging
import sys
import os
from datetime import datetime
import threading
import gc
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load .env file with explicit path and override
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

from src.utils.azure_client import AzureDevOpsClient
from src.utils.security_analyzer import SecurityAnalyzer
from src.utils.log_manager import LogManager
from src.database.database import DatabaseManager

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
WEBHOOK_SERVER_URL = os.getenv('WEBHOOK_SERVER_URL', 'http://localhost:8001')
print(f"🔧 Debug: WEBHOOK_SERVER_URL = {WEBHOOK_SERVER_URL}")

class WebSocketListener:
    def __init__(self):
        # WebSocket client
        self.sio = socketio.Client()
        self.websocket_url = WEBHOOK_SERVER_URL
        
        # Core components
        self.azure_client = AzureDevOpsClient()
        self.security_analyzer = SecurityAnalyzer()
        self.log_manager = LogManager()
        self.db_manager = DatabaseManager()
        
        # Azure DevOps config from environment variables (for simple method)
        self.organization = organization
        self.project = project
        self.pat = pat
        self.devops_server_url = devops_server_url
        
        # Debug: Print environment variables
        print(f"🔧 Debug: AZURE_ORGANIZATION = {self.organization}")
        print(f"🔧 Debug: AZURE_PROJECT = {self.project}")
        print(f"🔧 Debug: AZURE_PAT = {self.pat[:10]}..." if self.pat else "🔧 Debug: AZURE_PAT = None")
        print(f"🔧 Debug: SLACK_WEBHOOK_URL = {SLACK_WEBHOOK_URL}")
        
        # Connection tracking
        self.connected = False
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.last_event_time = time.time()
        self.last_heartbeat_time = time.time()
        
        # Event processing
        self.processed_events = set()
        self.event_count = 0
        
        # Memory management
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 300  # 5 dakika
        
        # Setup WebSocket events
        self.setup_websocket_events()
        
        logger.info("🔌 WebSocket Listener initialized")
        logger.info(f"📡 WebSocket URL: {self.websocket_url}")

    def setup_websocket_events(self):
        """Setup WebSocket event handlers"""
        
        @self.sio.event
        def connect():
            """Handle WebSocket connection"""
            self.connected = True
            self.connection_attempts += 1
            self.successful_connections += 1
            self.last_heartbeat_time = time.time()
            
            logger.info(f"🔌 WebSocket connected! (Attempt #{self.connection_attempts})")
            logger.info(f"📡 Server: {self.websocket_url}")
            
            # Request current events
            self.sio.emit('request_events')
            
            # Start heartbeat
            self.start_heartbeat()

        @self.sio.event
        def disconnect():
            """Handle WebSocket disconnection"""
            self.connected = False
            self.failed_connections += 1
            
            logger.warning("🔌 WebSocket disconnected!")
            
            # Try to reconnect
            self.reconnect()

        @self.sio.on('connection_status')
        def handle_connection_status(data):
            """Handle connection status update"""
            logger.info(f"📊 Connection Status: {data}")
            
        @self.sio.on('heartbeat_response')
        def handle_heartbeat_response(data):
            """Handle heartbeat response"""
            self.last_heartbeat_time = time.time()
            logger.debug(f"💓 Heartbeat response: {data}")

        @self.sio.on('events_data')
        def handle_events_data(data):
            """Handle events data from server"""
            events = data.get('events', [])
            total_events = data.get('total_events', 0)
            
            logger.info(f"📥 Received {len(events)} events from server (Total: {total_events})")
            
            # Process new events
            for event in events:
                self.process_event(event)

        @self.sio.on('webhook_event')
        def handle_webhook_event(data):
            """Handle real-time webhook event"""
            event_type = data.get('event_type', 'unknown')
            request_id = data.get('request_id', 0)
            timestamp = data.get('timestamp', '')
            
            logger.info(f"🚨 REAL-TIME EVENT: {event_type} (ID: {request_id}) at {timestamp}")
            
            # Process the event
            self.process_realtime_event(data)

    def start_heartbeat(self):
        """Start heartbeat to keep connection alive"""
        def heartbeat_loop():
            while self.connected:
                try:
                    self.sio.emit('heartbeat')
                    time.sleep(10)  # Send heartbeat every 10 seconds
                except Exception as e:
                    logger.error(f"💓 Heartbeat error: {e}")
                    break
        
        thread = threading.Thread(target=heartbeat_loop, daemon=True)
        thread.start()
        logger.info("💓 Heartbeat started")

    def reconnect(self):
        """Attempt to reconnect to WebSocket server"""
        max_retries = 5
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Reconnection attempt {attempt + 1}/{max_retries}")
                self.sio.connect(self.websocket_url)
                return  # Success
            except Exception as e:
                logger.error(f"❌ Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        logger.error("❌ All reconnection attempts failed!")

    def process_event(self, event):
        """Process a single event"""
        try:
            event_id = event.get('request_id', 0)
            
            # Skip if already processed
            if event_id in self.processed_events:
                return
            
            self.processed_events.add(event_id)
            self.event_count += 1
            self.last_event_time = time.time()
            
            # Extract event data
            event_data = event.get('data', {})
            event_type = event.get('event_type', 'unknown')
            
            logger.info(f"🔍 Processing event #{event_id}: {event_type}")
            
            # Process based on event type
            if event_type == 'build.complete':
                self.process_build_complete_event(event_data, event_id)
            elif event_type == 'build.started':
                self.process_build_started_event(event_data, event_id)
            else:
                logger.info(f"📋 Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"❌ Error processing event: {e}")

    def process_realtime_event(self, event_data):
        """Process real-time webhook event"""
        try:
            event_type = event_data.get('event_type', 'unknown')
            request_id = event_data.get('request_id', 0)
            
            logger.info(f"⚡ Processing real-time event: {event_type} (ID: {request_id})")
            
            # Get full event data from server
            self.sio.emit('request_events')
            
        except Exception as e:
            logger.error(f"❌ Error processing real-time event: {e}")

    def process_build_complete_event(self, event_data, event_id):
        """Process build complete event using simple_webhook_listener logic"""
        try:
            build_info = event_data.get('resource', {})
            build_id = build_info.get('id')
            build_number = build_info.get('buildNumber')
            definition = build_info.get('definition', {})
            definition_id = definition.get('id')
            definition_name = definition.get('name')
            
            logger.info(f"🔔 New Build Event: {build_number} (ID: {build_id})")
            logger.info(f"   Definition: {definition_name} (ID: {definition_id})")
            
            # Log webhook event
            self.log_manager.log_webhook('INFO', 'New build event received',
                                      build_id=build_id, build_number=build_number,
                                      definition_name=definition_name, definition_id=definition_id)
            
            # Save event to database (with duplicate check)
            event_data_for_db = {
                'event_type': 'build.complete',
                'build_id': build_id,
                'build_number': build_number,
                'definition_id': definition_id,
                'definition_name': definition_name,
                'raw_data': build_info
            }
            
            # Duplicate event check
            if self.db_manager.event_exists(build_id, build_number):
                logger.info(f"⏭️ Duplicate event skipped: Build {build_number}")
                return False
            
            webhook_event_id = self.db_manager.save_webhook_event(event_data_for_db)
            logger.info(f"💾 Event saved to database: ID {webhook_event_id}")
            
            # Log database operation
            self.log_manager.log_audit('Webhook event saved',
                                       event_id=webhook_event_id, build_number=build_number,
                                       definition_name=definition_name)
            
            # Get YAML content using simple_webhook_listener method
            yaml_content, yaml_filename = self.get_yaml_content_simple(definition_id)
            if yaml_content:
                logger.info(f"✅ YAML content received ({len(yaml_content)} characters)")
                
                # Perform security analysis
                security_findings = self.security_analyzer.analyze_yaml_content(yaml_content)
                
                if security_findings:
                    logger.warning("🚨 SECURITY ALERT! Dangerous patterns detected:")
                    
                    # Log security alert
                    self.log_manager.log_security('WARNING', 'Dangerous patterns detected',
                                               build_id=build_id, build_number=build_number,
                                               definition_name=definition_name,
                                               total_patterns=len(security_findings))
                    
                    for finding in security_findings:
                        logger.warning(f"   🔴 {finding['pattern'].upper()}: {finding['count']} instances found")
                        
                        # Log each pattern in detail
                        self.log_manager.log_security('WARNING', f"Pattern detected: {finding['pattern']}",
                                                   pattern=finding['pattern'], count=finding['count'],
                                                   build_id=build_id, build_number=build_number)
                        
                        for match in finding['matches'][:3]:  # Show first 3 matches
                            logger.warning(f"      Example: {match[:100]}...")
                    
                    # Save security findings to database
                    self.db_manager.save_security_findings(webhook_event_id, security_findings)
                    
                    # Send Slack notification
                    build_info_for_slack = {
                        'build_id': build_id,
                        'build_number': build_number,
                        'definition_name': definition_name,
                        'definition_id': definition_id
                    }
                    self.send_slack_notification_simple(build_info_for_slack, security_findings)
                    
                    # Log Slack notification
                    self.log_manager.log_audit('Slack notification sent',
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
            
        except Exception as e:
            logger.error(f"❌ Error processing build complete event: {e}")
            
            # Log error
            self.log_manager.log_error('Event analysis error',
                                 error=str(e), build_id=build_id if 'build_id' in locals() else None,
                                 build_number=build_number if 'build_number' in locals() else None)
            return False

    def process_build_started_event(self, event_data, event_id):
        """Process build started event"""
        try:
            build_info = event_data.get('resource', {})
            build_id = build_info.get('id', 0)
            build_number = build_info.get('buildNumber', 'unknown')
            definition_name = build_info.get('definition', {}).get('name', 'unknown')
            
            logger.info(f"🚀 Build started: {definition_name} #{build_number} (ID: {build_id})")
            
            # Log webhook event
            self.log_manager.log_webhook(
                'INFO',
                f"Build started: {build_number}",
                event_type='build.started',
                build_id=build_id,
                build_number=build_number,
                definition_name=definition_name
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing build started event: {e}")

    def get_yaml_content_simple(self, definition_id):
        """Get YAML content using simple_webhook_listener method"""
        try:
            # First get pipeline definition
            definition_url = f'{self.devops_server_url}/{self.organization}/{self.project}/_apis/build/definitions/{definition_id}?api-version=6.0'
            definition_response = requests.get(definition_url, auth=HTTPBasicAuth('', self.pat))
            
            if definition_response.status_code != 200:
                logger.error(f"Failed to get pipeline definition: {definition_response.status_code}")
                return None, None
            
            definition_data = definition_response.json()
            process = definition_data.get('process', {})
            yaml_filename = process.get('yamlFilename', 'azure-pipelines.yml')
            
            logger.info(f"📋 YAML file for Pipeline {definition_id}: {yaml_filename}")
            
            # Get YAML file
            url = f'{self.devops_server_url}/{self.organization}/{self.project}/_apis/git/repositories/cc0db49e-774d-4dc7-b789-6fbda107c4c7/items?path=/{yaml_filename}&api-version=6.0'
            response = requests.get(url, auth=HTTPBasicAuth('', self.pat))
            
            if response.status_code == 200:
                return response.text, yaml_filename
            else:
                logger.error(f"Failed to get YAML file: {response.status_code} - {yaml_filename}")
                return None, None
        except Exception as e:
            logger.error(f"YAML retrieval error: {e}")
            return None, None

    def get_yaml_content(self, definition_id):
        """Get YAML content from Azure DevOps"""
        try:
            # Get pipeline definition
            definition = self.azure_client.get_pipeline_definition(definition_id)
            if not definition:
                logger.warning(f"❌ Could not get pipeline definition: {definition_id}")
                return None, None
            
            # Debug: Check definition type
            logger.info(f"🔍 Definition type: {type(definition)}")
            logger.info(f"🔍 Definition content: {definition}")
            
            # Check if definition is a dictionary
            if not isinstance(definition, dict):
                logger.error(f"❌ Definition is not a dictionary: {type(definition)}")
                return None, None
            
            yaml_filename = definition.get('process', {}).get('yamlFilename', 'azure-pipelines.yml')
            
            # Get YAML content
            yaml_content = self.azure_client.get_yaml_content(definition_id, yaml_filename)
            if not yaml_content:
                logger.warning(f"❌ Could not get YAML content: {yaml_filename}")
                return None, None
            
            logger.info(f"📄 YAML content retrieved: {yaml_filename}")
            return yaml_content, yaml_filename
            
        except Exception as e:
            logger.error(f"❌ Error getting YAML content: {e}")
            return None, None

    def send_slack_notification_simple(self, build_info, findings):
        """Send Slack notification using simple_webhook_listener method"""
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
            if SLACK_WEBHOOK_URL:
                import requests
                response = requests.post(SLACK_WEBHOOK_URL, json=message)
                if response.status_code == 200:
                    logger.info("✅ Slack notification sent")
                else:
                    logger.error(f"❌ Failed to send Slack notification: {response.status_code}")
            else:
                logger.warning("⚠️ Slack webhook URL not configured")
                
        except Exception as e:
            logger.error(f"Slack notification error: {e}")

    def send_slack_notification(self, build_info, findings, total_patterns, total_risk_score):
        """Send Slack notification"""
        try:
            build_number = build_info.get('buildNumber', 'unknown')
            definition_name = build_info.get('definition', {}).get('name', 'unknown')
            
            # Create Slack message
            message = {
                "text": f"🚨 Security Alert: {total_patterns} issues found in {definition_name} #{build_number}",
                "attachments": [
                    {
                        "color": "danger" if total_risk_score > 20 else "warning",
                        "fields": [
                            {
                                "title": "Pipeline",
                                "value": definition_name,
                                "short": True
                            },
                            {
                                "title": "Build",
                                "value": build_number,
                                "short": True
                            },
                            {
                                "title": "Issues Found",
                                "value": total_patterns,
                                "short": True
                            },
                            {
                                "title": "Risk Score",
                                "value": total_risk_score,
                                "short": True
                            }
                        ]
                    }
                ]
            }
            
            # Send to Slack
            if SLACK_WEBHOOK_URL:
                import requests
                response = requests.post(SLACK_WEBHOOK_URL, json=message)
                if response.status_code == 200:
                    logger.info("✅ Slack notification sent")
                else:
                    logger.error(f"❌ Slack notification failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"❌ Error sending Slack notification: {e}")

    def cleanup_memory(self):
        """Clean up memory"""
        try:
            current_time = time.time()
            
            # Clean up old processed events (keep last 100)
            if len(self.processed_events) > 100:
                # Keep only recent events (this is simplified)
                self.processed_events = set(list(self.processed_events)[-100:])
            
            # Force garbage collection
            gc.collect()
            
            self.last_cleanup_time = current_time
            logger.info("🧹 Memory cleanup performed")
            
        except Exception as e:
            logger.error(f"❌ Memory cleanup error: {e}")

    def show_status(self):
        """Show current status"""
        logger.info("📊 WEBSOCKET LISTENER STATUS:")
        logger.info(f"   🔗 Connected: {self.connected}")
        logger.info(f"   📡 Server: {self.websocket_url}")
        logger.info(f"   📥 Events processed: {self.event_count}")
        logger.info(f"   🕐 Last event: {time.strftime('%H:%M:%S', time.localtime(self.last_event_time))}")
        logger.info(f"   💓 Last heartbeat: {time.strftime('%H:%M:%S', time.localtime(self.last_heartbeat_time))}")
        logger.info(f"   🧹 Last cleanup: {time.strftime('%H:%M:%S', time.localtime(self.last_cleanup_time))}")

    def run(self):
        """Main run loop"""
        try:
            logger.info("🚀 Starting WebSocket Listener...")
            
            # Connect to WebSocket server
            self.sio.connect(self.websocket_url)
            
            # Main loop
            last_status_time = time.time()
            
            while True:
                try:
                    # Show status every 5 minutes
                    if time.time() - last_status_time > 300:
                        self.show_status()
                        last_status_time = time.time()
                    
                    # Memory cleanup every 5 minutes
                    if time.time() - self.last_cleanup_time > self.cleanup_interval:
                        self.cleanup_memory()
                    
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Shutting down WebSocket Listener...")
                    break
                except Exception as e:
                    logger.error(f"❌ Main loop error: {e}")
                    time.sleep(5)
            
            # Disconnect
            if self.connected:
                self.sio.disconnect()
            
        except Exception as e:
            logger.error(f"❌ WebSocket Listener error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    listener = WebSocketListener()
    listener.run() 