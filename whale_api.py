#!/usr/bin/env python3
"""
Whale Watch REST API
Agent-to-agent interface for whale tracking data
Allows other AI agents to subscribe to whale movements and alerts
"""

from flask import Flask, jsonify, request, send_file
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
import aiohttp
from functools import wraps
import hashlib

app = Flask(__name__)

# Configuration
DATA_FILE = "whale_data.json"
ALERTS_FILE = "whale_alerts.jsonl"
MAX_RESULTS = 100
API_VERSION = "1.0"

# Webhook subscriptions (in-memory, persists during runtime)
webhook_subscriptions = []


class WhaleAPI:
    """API handler for whale tracker data."""
    
    @staticmethod
    def load_whale_data() -> Dict[str, Any]:
        """Load latest whale data from file."""
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading whale data: {e}")
        
        return {
            "last_updated": datetime.utcnow().isoformat(),
            "eth_whales": [],
            "usdc_whales": [],
            "alerts": [],
            "summary": {}
        }
    
    @staticmethod
    def load_alerts() -> List[Dict]:
        """Load alerts from JSONL file."""
        alerts = []
        try:
            if os.path.exists(ALERTS_FILE):
                with open(ALERTS_FILE, 'r') as f:
                    for line in f:
                        if line.strip():
                            alerts.append(json.loads(line))
        except Exception as e:
            print(f"⚠️ Error loading alerts: {e}")
        
        return alerts
    
    @staticmethod
    def filter_whales(whales: List[Dict], min_eth: float = 0, 
                     min_usdc: float = 0, whale_type: Optional[str] = None,
                     limit: int = MAX_RESULTS) -> List[Dict]:
        """Filter whales by criteria."""
        filtered = whales
        
        if min_eth > 0:
            filtered = [w for w in filtered if w.get('value_eth', 0) >= min_eth]
        
        if min_usdc > 0:
            filtered = [w for w in filtered if w.get('value_usdc', 0) >= min_usdc]
        
        if whale_type:
            filtered = [w for w in filtered 
                       if w.get('whale_profile', {}).get('whale_type') == whale_type]
        
        return filtered[:limit]
    
    @staticmethod
    def filter_alerts(alerts: List[Dict], severity: Optional[str] = None,
                     whale_type: Optional[str] = None, hours: int = 24,
                     limit: int = MAX_RESULTS) -> List[Dict]:
        """Filter alerts by criteria."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        filtered = []
        
        for alert in alerts:
            try:
                alert_time = datetime.fromisoformat(alert.get('timestamp', ''))
                if alert_time < cutoff:
                    continue
                
                if severity and alert.get('severity') != severity:
                    continue
                
                if whale_type and alert.get('whale_type') != whale_type:
                    continue
                
                filtered.append(alert)
            except:
                pass
        
        return sorted(filtered, key=lambda a: a.get('timestamp', ''), 
                     reverse=True)[:limit]


# API Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for agent monitoring."""
    data = WhaleAPI.load_whale_data()
    return jsonify({
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "last_data_update": data.get('last_updated'),
        "tracked_whales": {
            "eth": len(data.get('eth_whales', [])),
            "usdc": len(data.get('usdc_whales', []))
        },
        "total_alerts": data.get('summary', {}).get('total_alerts', 0)
    })


@app.route('/api/whales', methods=['GET'])
def get_whales():
    """Get whale movements with optional filtering.
    
    Query parameters:
    - type: 'eth' or 'usdc' (default: both)
    - min_eth: minimum ETH threshold
    - min_usdc: minimum USDC threshold
    - whale_type: 'exchange_cold', 'private_whale', etc.
    - limit: max results (default: 100)
    
    Example:
    /api/whales?type=eth&min_eth=500&whale_type=private_whale&limit=20
    """
    data = WhaleAPI.load_whale_data()
    whale_type_filter = request.args.get('whale_type', None)
    min_eth = float(request.args.get('min_eth', 0))
    min_usdc = float(request.args.get('min_usdc', 0))
    limit = int(request.args.get('limit', MAX_RESULTS))
    whale_data_type = request.args.get('type', 'all')
    
    result = {"whales": []}
    
    if whale_data_type in ['eth', 'all']:
        eth_whales = WhaleAPI.filter_whales(
            data.get('eth_whales', []),
            min_eth=min_eth,
            whale_type=whale_type_filter,
            limit=limit
        )
        result['whales'].extend(eth_whales)
    
    if whale_data_type in ['usdc', 'all']:
        usdc_whales = WhaleAPI.filter_whales(
            data.get('usdc_whales', []),
            min_usdc=min_usdc,
            whale_type=whale_type_filter,
            limit=limit
        )
        result['whales'].extend(usdc_whales)
    
    # Sort by timestamp
    result['whales'] = sorted(
        result['whales'],
        key=lambda w: w.get('timestamp', ''),
        reverse=True
    )[:limit]
    
    result['count'] = len(result['whales'])
    result['timestamp'] = datetime.utcnow().isoformat()
    
    return jsonify(result)


@app.route('/api/whales/<whale_type>', methods=['GET'])
def get_whales_by_type(whale_type: str):
    """Get whales of specific type (eth or usdc).
    
    Example:
    /api/whales/eth?min_value=500
    """
    data = WhaleAPI.load_whale_data()
    
    if whale_type == 'eth':
        whales = data.get('eth_whales', [])
        min_value = float(request.args.get('min_value', 0))
        filtered = [w for w in whales if w.get('value_eth', 0) >= min_value]
    elif whale_type == 'usdc':
        whales = data.get('usdc_whales', [])
        min_value = float(request.args.get('min_value', 0))
        filtered = [w for w in whales if w.get('value_usdc', 0) >= min_value]
    else:
        return jsonify({"error": "Invalid whale type. Use 'eth' or 'usdc'"}), 400
    
    limit = int(request.args.get('limit', MAX_RESULTS))
    
    return jsonify({
        "type": whale_type,
        "count": len(filtered[:limit]),
        "whales": filtered[:limit],
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get alerts with optional filtering.
    
    Query parameters:
    - severity: 'critical', 'high', 'medium', 'low'
    - whale_type: filter by whale type
    - hours: lookback period (default: 24)
    - limit: max results (default: 100)
    
    Example:
    /api/alerts?severity=critical&hours=12&limit=50
    """
    data = WhaleAPI.load_whale_data()
    alerts = data.get('alerts', [])
    
    severity = request.args.get('severity', None)
    whale_type = request.args.get('whale_type', None)
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', MAX_RESULTS))
    
    filtered = WhaleAPI.filter_alerts(
        alerts,
        severity=severity,
        whale_type=whale_type,
        hours=hours,
        limit=limit
    )
    
    return jsonify({
        "count": len(filtered),
        "alerts": filtered,
        "filters": {
            "severity": severity,
            "whale_type": whale_type,
            "hours": hours
        },
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/alerts/critical', methods=['GET'])
def get_critical_alerts():
    """Get only critical-severity alerts (shortcut endpoint).
    
    Example:
    /api/alerts/critical?hours=6
    """
    data = WhaleAPI.load_whale_data()
    alerts = data.get('alerts', [])
    
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', MAX_RESULTS))
    
    critical = WhaleAPI.filter_alerts(
        alerts,
        severity='critical',
        hours=hours,
        limit=limit
    )
    
    return jsonify({
        "count": len(critical),
        "critical_alerts": critical,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Get system summary (quick overview for agents).
    
    Example:
    /api/summary
    """
    data = WhaleAPI.load_whale_data()
    
    return jsonify({
        "system_status": "operational",
        "api_version": API_VERSION,
        "last_updated": data.get('last_updated'),
        "summary": data.get('summary', {}),
        "eth_whales_count": len(data.get('eth_whales', [])),
        "usdc_whales_count": len(data.get('usdc_whales', [])),
        "total_alerts": data.get('summary', {}).get('total_alerts', 0),
        "critical_alerts": data.get('summary', {}).get('critical_alerts', 0),
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/subscribe', methods=['POST'])
def subscribe_webhook():
    """Subscribe to webhook alerts.
    
    Request body:
    {
        "webhook_url": "https://agent.example.com/webhook",
        "severity": "critical",  # optional
        "whale_type": "private_whale",  # optional
        "agent_name": "my-trading-bot"  # optional
    }
    
    Response:
    {
        "subscription_id": "sub_xxxxx",
        "status": "active"
    }
    """
    payload = request.get_json()
    
    if not payload or 'webhook_url' not in payload:
        return jsonify({"error": "webhook_url required"}), 400
    
    subscription = {
        "id": hashlib.md5(
            f"{payload['webhook_url']}{datetime.utcnow()}".encode()
        ).hexdigest()[:12],
        "webhook_url": payload['webhook_url'],
        "severity": payload.get('severity', 'all'),
        "whale_type": payload.get('whale_type', 'all'),
        "agent_name": payload.get('agent_name', 'unknown'),
        "created_at": datetime.utcnow().isoformat(),
        "active": True
    }
    
    webhook_subscriptions.append(subscription)
    
    return jsonify({
        "subscription_id": subscription['id'],
        "status": "active",
        "webhook_url": subscription['webhook_url'],
        "timestamp": datetime.utcnow().isoformat()
    }), 201


@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    """Get all active webhook subscriptions."""
    return jsonify({
        "count": len(webhook_subscriptions),
        "subscriptions": webhook_subscriptions,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/subscriptions/<subscription_id>', methods=['DELETE'])
def unsubscribe(subscription_id: str):
    """Unsubscribe from webhook alerts."""
    global webhook_subscriptions
    
    webhook_subscriptions = [s for s in webhook_subscriptions 
                            if s['id'] != subscription_id]
    
    return jsonify({
        "status": "unsubscribed",
        "subscription_id": subscription_id,
        "remaining_subscriptions": len(webhook_subscriptions)
    })


@app.route('/api/download', methods=['GET'])
def download_data():
    """Download complete whale_data.json file.
    
    Example:
    /api/download
    """
    if os.path.exists(DATA_FILE):
        return send_file(DATA_FILE, as_attachment=True)
    return jsonify({"error": "Data file not found"}), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about whale activity.
    
    Example:
    /api/stats?hours=24
    """
    data = WhaleAPI.load_whale_data()
    hours = int(request.args.get('hours', 24))
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    eth_whales = data.get('eth_whales', [])
    usdc_whales = data.get('usdc_whales', [])
    
    return jsonify({
        "period_hours": hours,
        "eth_whales": {
            "count": len(eth_whales),
            "total_eth": sum(w.get('value_eth', 0) for w in eth_whales),
            "total_usd": sum(w.get('value_eth', 0) * 2500 for w in eth_whales)
        },
        "usdc_whales": {
            "count": len(usdc_whales),
            "total_usdc": sum(w.get('value_usdc', 0) for w in usdc_whales)
        },
        "whale_types": {
            "exchange_cold": len([w for w in eth_whales + usdc_whales 
                                 if w.get('whale_profile', {}).get('whale_type') == 'exchange_cold']),
            "private_whale": len([w for w in eth_whales + usdc_whales 
                                if w.get('whale_profile', {}).get('whale_type') == 'private_whale']),
            "contract": len([w for w in eth_whales + usdc_whales 
                           if w.get('whale_profile', {}).get('whale_type') == 'contract'])
        },
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/docs', methods=['GET'])
def get_docs():
    """Get API documentation."""
    return jsonify({
        "title": "Whale Watch API",
        "version": API_VERSION,
        "description": "Agent-native interface for on-chain whale tracking",
        "endpoints": {
            "GET /api/health": "System health check",
            "GET /api/whales": "Get whale movements (filterable)",
            "GET /api/whales/eth": "Get ETH whales only",
            "GET /api/whales/usdc": "Get USDC whales only",
            "GET /api/alerts": "Get alerts (filterable)",
            "GET /api/alerts/critical": "Get critical alerts only",
            "GET /api/summary": "Get system summary",
            "GET /api/stats": "Get whale activity statistics",
            "POST /api/subscribe": "Subscribe to webhook alerts",
            "GET /api/subscriptions": "List active subscriptions",
            "DELETE /api/subscriptions/<id>": "Unsubscribe from alerts",
            "GET /api/download": "Download complete whale_data.json",
            "GET /api/docs": "API documentation"
        },
        "base_url": "http://127.0.0.1:8000",
        "authentication": "None (open API)",
        "rate_limit": "None (for agents)",
        "response_format": "JSON"
    })


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    print("🐋 Whale Watch API - Starting")
    print("📡 Available at: http://127.0.0.1:5000/api/")
    print("📖 Documentation: http://127.0.0.1:5000/api/docs")
    print("💚 Agent-native interface ready\n")
    app.run(host='127.0.0.1', port=5000, debug=False)
