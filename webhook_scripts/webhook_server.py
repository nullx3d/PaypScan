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
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
webhook_events = []
MAX_EVENTS = 50
MAX_EVENT_AGE = 3600  # 1 saat - eski event'leri sil

# Detailed logging
request_count = 0
last_request_time = time.time()
error_count = 0
last_error_time = None

def cleanup_old_events():
    """Clean up old events to prevent memory leak"""
    global webhook_events
    current_time = datetime.now()
    
    # Remove events older than 1 hour
    webhook_events = [
        event for event in webhook_events 
        if (current_time - datetime.fromisoformat(event['timestamp'])).total_seconds() < MAX_EVENT_AGE
    ]
    
    if len(webhook_events) > MAX_EVENTS:
        # Keep only the latest events
        webhook_events = webhook_events[-MAX_EVENTS:]
    
    logger.info(f"🧹 Memory cleanup: {len(webhook_events)} events remaining")

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handles Azure DevOps webhooks"""
    
    global request_count, last_request_time, error_count, last_error_time
    
    try:
        request_count += 1
        last_request_time = time.time()
        
        # Log request
        logger.info(f"📥 Webhook #{request_count} received: {request.method} {request.url}")
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"🕐 Request time: {datetime.now().isoformat()}")
        
        # Get JSON body
        data = request.get_json()
        if not data:
            logger.warning("❌ JSON body not found")
            error_count += 1
            last_error_time = time.time()
            return jsonify({"error": "No JSON data"}), 400
        
        # Get event type
        event_type = data.get('eventType', 'unknown')
        logger.info(f"📋 Event Type: {event_type}")
        
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
        
        # Cleanup old events periodically
        cleanup_old_events()  # ✅ Memory cleanup
        
        # Analyze Azure DevOps events
        analyze_azure_devops_event(data)
        
        logger.info(f"✅ Webhook #{request_count} processed successfully")
        return jsonify({"status": "success", "message": "Webhook received"}), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook #{request_count} processing error: {e}")
        error_count += 1
        last_error_time = time.time()
        return jsonify({"error": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_events():
    """Returns stored events"""
    response = jsonify({
        "total_events": len(webhook_events),
        "events": webhook_events
    })
    
    # Add headers to prevent connection issues
    response.headers['Connection'] = 'close'
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    
    return response

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

@app.route('/status', methods=['GET'])
def status_check():
    """Detailed status endpoint for monitoring"""
    global request_count, last_request_time, error_count, last_error_time
    
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "total_events": len(webhook_events),
        "server_uptime": "active",
        "last_event_time": webhook_events[-1]['timestamp'] if webhook_events else None,
        "memory_usage": len(webhook_events),
        "max_events": MAX_EVENTS,
        "request_count": request_count,
        "last_request_time": datetime.fromtimestamp(last_request_time).isoformat() if last_request_time else None,
        "error_count": error_count,
        "last_error_time": datetime.fromtimestamp(last_error_time).isoformat() if last_error_time else None,
        "success_rate": f"{((request_count - error_count) / request_count * 100):.1f}%" if request_count > 0 else "0%"
    })

@app.route('/connection-status', methods=['GET'])
def connection_status():
    """Detailed connection status for monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_events": len(webhook_events),
        "server_uptime": "active",
        "last_event_time": webhook_events[-1]['timestamp'] if webhook_events else None,
        "memory_usage": len(webhook_events),
        "max_events": MAX_EVENTS,
        "connection_test": "available"
    })

@app.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint for connection testing"""
    response = jsonify({"pong": datetime.now().isoformat()})
    
    # Add headers to prevent connection issues
    response.headers['Connection'] = 'close'
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    
    return response

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