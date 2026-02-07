#!/bin/bash
#
# 🐋 Whale Watch - Stop All Services
#

echo "🛑 Stopping all services..."

# Kill processes on port 5000 and 8000
lsof -i :5000 -t | xargs kill -9 2>/dev/null || true
lsof -i :8000 -t | xargs kill -9 2>/dev/null || true

# Kill whale tracker
pkill -f "whale_tracker_integrated.py" 2>/dev/null || true

echo "✅ All services stopped"
