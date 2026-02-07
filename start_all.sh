#!/bin/bash
#
# 🐋 Whale Watch - Start Everything
# Runs whale tracker + API + dashboard in one command
#

set -e

echo "🐋 Whale Watch - Starting All Services"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "whale_tracker_integrated.py" ]; then
    echo "❌ Error: Run this script from the whale-watch directory"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 not found. Install Python 3.9+"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
python3 -c "import aiohttp" 2>/dev/null || {
    echo "⚠️  Installing dependencies..."
    pip install -r requirements.txt
}

# Create logs directory
mkdir -p logs

# Start services in background
echo ""
echo "🚀 Starting services..."

# 1. Whale Tracker
echo "  1️⃣  Starting whale tracker..."
python3 whale_tracker_integrated.py > logs/whale_tracker.log 2>&1 &
TRACKER_PID=$!
echo "     PID: $TRACKER_PID"

# Wait for whale_data.json to be created
sleep 3
if [ ! -f "whale_data.json" ]; then
    echo "⚠️  Waiting for whale data..."
    sleep 3
fi

# 2. Enhanced API
echo "  2️⃣  Starting API server..."
python3 whale_api_enhanced.py > logs/api.log 2>&1 &
API_PID=$!
echo "     PID: $API_PID"

# 3. HTTP Server (Dashboard)
echo "  3️⃣  Starting web server (port 8000)..."
python3 -m http.server 8000 --directory . > logs/http.log 2>&1 &
HTTP_PID=$!
echo "     PID: $HTTP_PID"

# Wait for services to start
sleep 2

# Check if services are running
if ! kill -0 $TRACKER_PID 2>/dev/null; then
    echo "❌ Whale tracker failed to start"
    exit 1
fi

if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ API server failed to start"
    exit 1
fi

if ! kill -0 $HTTP_PID 2>/dev/null; then
    echo "❌ HTTP server failed to start"
    exit 1
fi

# Success!
echo ""
echo "✅ All services running!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Dashboard:  http://127.0.0.1:8000/dashboard-enhanced.html"
echo "🔌 API:        http://127.0.0.1:5000/api"
echo ""
echo "📝 Logs:"
echo "   Tracker: tail -f logs/whale_tracker.log"
echo "   API:     tail -f logs/api.log"
echo "   HTTP:    tail -f logs/http.log"
echo ""
echo "🛑 To stop all services:"
echo "   kill $TRACKER_PID $API_PID $HTTP_PID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save PIDs to file
echo "$TRACKER_PID" > .pids/tracker.pid
echo "$API_PID" > .pids/api.pid
echo "$HTTP_PID" > .pids/http.pid

mkdir -p .pids 2>/dev/null || true
echo "$TRACKER_PID $API_PID $HTTP_PID" > .pids/all.pids

# Keep script running
wait
