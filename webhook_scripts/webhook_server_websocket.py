#!/usr/bin/env python3
"""
Azure DevOps WebSocket Webhook Server
WebSocket-based webhook server to eliminate connection timeout issues
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import logging
from datetime import datetime
import os
import time
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'payscan_websocket_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables
webhook_events = []
MAX_EVENTS = 50
MAX_EVENT_AGE = 3600  # 1 saat

# Connection tracking
connected_clients = set()
client_heartbeats = {}
last_webhook_time = None

# Detailed logging
request_count = 0
last_request_time = time.time()
error_count = 0
last_error_time = None

def cleanup_old_events():
    """Clean up old events to prevent memory leak"""
    global webhook_events
    current_time = datetime.now()
    
    webhook_events = [
        event for event in webhook_events 
        if (current_time - datetime.fromisoformat(event['timestamp'])).total_seconds() < MAX_EVENT_AGE
    ]
    
    if len(webhook_events) > MAX_EVENTS:
        webhook_events = webhook_events[-MAX_EVENTS:]
    
    logger.info(f"🧹 Memory cleanup: {len(webhook_events)} events remaining")

def broadcast_event(event_data):
    """Broadcast event to all connected WebSocket clients"""
    try:
        socketio.emit('webhook_event', event_data, namespace='/')
        logger.info(f"📡 Event broadcasted to {len(connected_clients)} connected clients")
    except Exception as e:
        logger.error(f"❌ Failed to broadcast event: {e}")

def start_heartbeat_monitor():
    """Monitor client heartbeats and clean up inactive connections"""
    def monitor():
        while True:
            try:
                current_time = time.time()
                inactive_clients = []
                
                for client_id, last_heartbeat in client_heartbeats.items():
                    if current_time - last_heartbeat > 30:  # 30 saniye timeout
                        inactive_clients.append(client_id)
                
                for client_id in inactive_clients:
                    del client_heartbeats[client_id]
                    connected_clients.discard(client_id)
                    logger.info(f"🔌 Inactive client removed: {client_id}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
                time.sleep(10)
    
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    logger.info("💓 Heartbeat monitor started")

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection"""
    client_id = request.sid
    connected_clients.add(client_id)
    client_heartbeats[client_id] = time.time()
    
    logger.info(f"🔌 Client connected: {client_id} (Total: {len(connected_clients)})")
    
    # Send current status
    emit('connection_status', {
        'status': 'connected',
        'client_id': client_id,
        'connected_clients': len(connected_clients),
        'total_events': len(webhook_events),
        'last_webhook': last_webhook_time
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    client_id = request.sid
    connected_clients.discard(client_id)
    if client_id in client_heartbeats:
        del client_heartbeats[client_id]
    
    logger.info(f"🔌 Client disconnected: {client_id} (Total: {len(connected_clients)})")

@socketio.on('heartbeat')
def handle_heartbeat():
    """Handle client heartbeat"""
    client_id = request.sid
    client_heartbeats[client_id] = time.time()
    
    # Send heartbeat response
    emit('heartbeat_response', {
        'timestamp': datetime.now().isoformat(),
        'client_id': client_id
    })

@socketio.on('request_events')
def handle_request_events():
    """Handle client request for events"""
    client_id = request.sid
    
    # Send all events to client
    emit('events_data', {
        'events': webhook_events,
        'total_events': len(webhook_events),
        'timestamp': datetime.now().isoformat()
    })
    
    logger.info(f"📤 Events sent to client: {client_id}")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle client joining a room"""
    room = data.get('room', 'default')
    join_room(room)
    logger.info(f"🏠 Client {request.sid} joined room: {room}")

# HTTP Routes
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handles Azure DevOps webhooks"""
    
    global request_count, last_request_time, error_count, last_error_time, last_webhook_time
    
    try:
        request_count += 1
        last_request_time = time.time()
        last_webhook_time = datetime.now().isoformat()
        
        # Log request
        logger.info(f"📥 Webhook #{request_count} received: {request.method} {request.url}")
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"🕐 Request time: {last_webhook_time}")
        
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
            'headers': dict(request.headers),
            'request_id': request_count
        }
        webhook_events.append(event_record)
        
        # Clean old events
        if len(webhook_events) > MAX_EVENTS:
            webhook_events = webhook_events[-MAX_EVENTS:]
            logger.info(f"🔄 Old events cleaned. Remaining events: {len(webhook_events)}")
        
        # Cleanup old events periodically
        cleanup_old_events()
        
        # Analyze Azure DevOps events
        analyze_azure_devops_event(data)
        
        # Broadcast to WebSocket clients
        broadcast_event({
            'event_type': event_type,
            'timestamp': event_record['timestamp'],
            'request_id': request_count,
            'connected_clients': len(connected_clients)
        })
        
        logger.info(f"✅ Webhook #{request_count} processed successfully")
        return jsonify({
            "status": "success", 
            "message": "Webhook received",
            "broadcasted_to": len(connected_clients),
            "request_id": request_count
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook #{request_count} processing error: {e}")
        error_count += 1
        last_error_time = time.time()
        return jsonify({"error": str(e)}), 500

@app.route('/events', methods=['GET'])
def get_events():
    """Get all stored events (HTTP fallback)"""
    response = jsonify({
        "total_events": len(webhook_events),
        "events": webhook_events,
        "connected_clients": len(connected_clients),
        "last_webhook": last_webhook_time
    })
    response.headers['Connection'] = 'close'
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/ping', methods=['GET'])
def ping():
    """Health check endpoint"""
    response = jsonify({
        "pong": datetime.now().isoformat(),
        "connected_clients": len(connected_clients),
        "total_events": len(webhook_events),
        "last_webhook": last_webhook_time
    })
    response.headers['Connection'] = 'close'
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/status', methods=['GET'])
def status_check():
    """Detailed status endpoint"""
    global request_count, last_request_time, error_count, last_error_time
    
    return jsonify({
        "server_status": "running",
        "webhook_events_count": len(webhook_events),
        "connected_clients": len(connected_clients),
        "request_count": request_count,
        "last_request_time": datetime.fromtimestamp(last_request_time).isoformat() if last_request_time else None,
        "error_count": error_count,
        "last_error_time": datetime.fromtimestamp(last_error_time).isoformat() if last_error_time else None,
        "success_rate": f"{((request_count - error_count) / request_count * 100):.1f}%" if request_count > 0 else "0%",
        "last_webhook": last_webhook_time,
        "memory_usage": f"{len(webhook_events)}/{MAX_EVENTS} events",
        "uptime": "running"
    })

@app.route('/websocket-info', methods=['GET'])
def websocket_info():
    """WebSocket connection information"""
    return jsonify({
        "websocket_enabled": True,
        "connected_clients": list(connected_clients),
        "client_count": len(connected_clients),
        "heartbeat_clients": list(client_heartbeats.keys()),
        "server_url": f"ws://localhost:{port}"
    })

def analyze_azure_devops_event(data):
    """Analyze Azure DevOps event and log details"""
    event_type = data.get('eventType', 'unknown')
    
    if event_type == 'build.complete':
        build_info = data.get('resource', {})
        build_id = build_info.get('id', 'unknown')
        build_number = build_info.get('buildNumber', 'unknown')
        definition_name = build_info.get('definition', {}).get('name', 'unknown')
        
        logger.info(f"🏗️ Build completed: {definition_name} #{build_number} (ID: {build_id})")
        
    elif event_type == 'build.started':
        build_info = data.get('resource', {})
        build_id = build_info.get('id', 'unknown')
        build_number = build_info.get('buildNumber', 'unknown')
        definition_name = build_info.get('definition', {}).get('name', 'unknown')
        
        logger.info(f"🚀 Build started: {definition_name} #{build_number} (ID: {build_id})")
        
    else:
        logger.info(f"📋 Event type: {event_type}")

if __name__ == '__main__':
    # Start heartbeat monitor
    start_heartbeat_monitor()
    
    # Start WebSocket server
    logger.info("🚀 Starting WebSocket Webhook Server...")
    logger.info("💓 Heartbeat monitor: Active")
    
    port = int(os.environ.get('PORT', 8001))
    logger.info(f"Starting WebSocket webhook server... Port: {port}")
    logger.info(f"Webhook URL: http://localhost:{port}/webhook")
    logger.info(f"WebSocket URL: ws://localhost:{port}")
    logger.info(f"Health Check: http://localhost:{port}/health")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True) 