#!/usr/bin/env python3
"""
Azure DevOps Webhook Server
Flask webhook server to be exposed with ngrok
"""

from flask import Flask, request, jsonify
import json
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
webhook_events = []
MAX_EVENTS = 50

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handles Azure DevOps webhooks"""
    
    try:
        # Log request
        logger.info(f"Webhook received: {request.method} {request.url}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Get JSON body
        data = request.get_json()
        if not data:
            logger.warning("JSON body not found")
            return jsonify({"error": "No JSON data"}), 400
        
        # Get event type
        event_type = data.get('eventType', 'unknown')
        logger.info(f"Event Type: {event_type}")
        
        # Store event
        global webhook_events
        event_record = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data,
            'headers': dict(request.headers)
        }
        webhook_events.append(event_record)
        
        # Clean old events (prevent memory leak)
        if len(webhook_events) > MAX_EVENTS:
            webhook_events = webhook_events[-MAX_EVENTS:]
            logger.info(f"🔄 Old events cleaned. Remaining events: {len(webhook_events)}")
        
        # Analyze Azure DevOps events
        analyze_azure_devops_event(data)
        
        return jsonify({"status": "success", "message": "Webhook received"}), 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_events():
    """Returns stored events"""
    return jsonify({
        "total_events": len(webhook_events),
        "events": webhook_events
    })

@app.route('/events/latest', methods=['GET'])
def get_latest_event():
    """Returns the latest event"""
    if webhook_events:
        return jsonify(webhook_events[-1])
    return jsonify({"error": "No events found"}), 404

@app.route('/events/builds', methods=['GET'])
def get_build_events():
    """Filters build events"""
    build_events = [
        event for event in webhook_events 
        if event.get('event_type') in ['build.completed', 'build.started', 'build.failed']
    ]
    return jsonify({
        "total_build_events": len(build_events),
        "build_events": build_events
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_events": len(webhook_events)
    })

def analyze_azure_devops_event(data):
    """Analyzes Azure DevOps events"""
    
    event_type = data.get('eventType')
    
    if event_type == 'build.completed':
        # Build completed event
        resource = data.get('resource', {})
        build_id = resource.get('id')
        build_number = resource.get('buildNumber')
        result = resource.get('result')
        
        logger.info(f"Build completed: {build_number} (ID: {build_id}) - Result: {result}")
        
        # Perform security analysis
        if result == 'succeeded':
            logger.info("✅ Build successful - Security analysis can be performed")
        else:
            logger.warning(f"⚠️ Build failed: {result}")
    
    elif event_type == 'build.started':
        # Build started event
        resource = data.get('resource', {})
        build_id = resource.get('id')
        build_number = resource.get('buildNumber')
        
        logger.info(f"Build started: {build_number} (ID: {build_id})")
    
    elif event_type == 'build.failed':
        # Build failed event
        resource = data.get('resource', {})
        build_id = resource.get('id')
        build_number = resource.get('buildNumber')
        
        logger.warning(f"Build failed: {build_number} (ID: {build_id})")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting webhook server... Port: {port}")
    logger.info(f"Webhook URL: http://localhost:{port}/webhook")
    logger.info(f"Events URL: http://localhost:{port}/events")
    logger.info(f"Health Check: http://localhost:{port}/health")
    
    app.run(host='0.0.0.0', port=port, debug=True) 