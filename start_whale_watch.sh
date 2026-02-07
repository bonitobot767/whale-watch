#!/bin/bash

# 🐋 Whale Watch - Complete Startup Script
# Starts tracker, HTTP server, and opens dashboard

PROJECT_DIR="/home/mourad/clawd/bonito-projects/onchain-intelligence-agent"
cd "$PROJECT_DIR"

echo "🐋 Starting Whale Watch System..."
echo "=================================="

# Kill any existing processes (cleanup)
pkill -f "whale_tracker.py" 2>/dev/null || true
pkill -f "http.server" 2>/dev/null || true
sleep 1

# Start the whale tracker in the background
echo "✅ Starting tracker (INTEGRATED)..."
python3 whale_tracker_integrated.py > /tmp/whale_tracker.log 2>&1 &
TRACKER_PID=$!
echo "   PID: $TRACKER_PID"

# Start the Whale Watch API in the background
echo "✅ Starting REST API (Agent Interface)..."
python3 whale_api.py > /tmp/whale_api.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

# Start the HTTP server in the background (for dashboard)
echo "✅ Starting dashboard server..."
python3 -m http.server 8000 > /tmp/http_server.log 2>&1 &
SERVER_PID=$!
echo "   PID: $SERVER_PID"

# Wait for server to start
sleep 2

# Open the dashboard in the default browser
echo "✅ Opening dashboard..."
# Try multiple methods to open browser
if command -v chromium &> /dev/null; then
    chromium http://127.0.0.1:8000/dashboard-simple.html &
elif command -v firefox &> /dev/null; then
    firefox http://127.0.0.1:8000/dashboard-simple.html &
elif command -v x-www-browser &> /dev/null; then
    x-www-browser http://127.0.0.1:8000/dashboard-simple.html &
else
    echo "   Manual: Open http://127.0.0.1:8000/dashboard-simple.html in your browser"
fi

echo ""
echo "=================================="
echo "✅ Whale Watch is RUNNING!"
echo ""
echo "📊 Dashboard: http://127.0.0.1:8000/dashboard-simple.html"
echo "🔌 REST API: http://127.0.0.1:5000/api/"
echo "📖 API Docs: http://127.0.0.1:5000/api/docs"
echo ""
echo "🛑 To stop:"
echo "   Kill the terminal or run: pkill -f whale_tracker.py && pkill -f whale_api.py && pkill -f http.server"
echo ""
echo "📝 Logs:"
echo "   Tracker: tail -f /tmp/whale_tracker.log"
echo "   API:     tail -f /tmp/whale_api.log"
echo "   Server:  tail -f /tmp/http_server.log"
echo "=================================="

# Keep this script running so the processes don't get killed
wait
