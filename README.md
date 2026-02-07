# 🐋 Whale Watch - Real-Time On-Chain Intelligence Agent

An autonomous AI agent that detects large cryptocurrency transfers (whale movements) on Ethereum in real-time and feeds actionable signals to other trading systems.

**Perfect for:** Trading bots, market researchers, autonomous agents, DeFi protocols

---

## 🎯 What Does This Do?

Whale Watch scans the Ethereum blockchain every 12 seconds and identifies:

✅ **Large ETH transfers** (>100 ETH, ~$300K+)  
✅ **Large USDC transfers** (>$100K)  
✅ **Wallet patterns** (institutional, exchange, private)  
✅ **Real-time alerts** via JSON API  
✅ **Integration-ready** for other autonomous systems  

**Why it matters:** Whale movements often precede major price moves. This system detects them in seconds, not hours.

---

## 📋 Quick Start (5 Minutes)

### 1. Get an API Key (FREE)

Visit: https://etherscan.io/apis

- Click "Sign Up"
- Create free account
- Generate API key
- Copy it somewhere safe

### 2. Clone & Install

```bash
git clone https://github.com/bonitobot767/whale-watch
cd whale-watch
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and paste your API key:

```
ETHERSCAN_API_KEY=your_api_key_here
```

### 4. Run

```bash
./start_whale_watch.sh
```

### 5. View Dashboard

Open in browser: http://127.0.0.1:8000/dashboard-simple.html

---

## 🔧 What You Get

### The Dashboard

```
http://127.0.0.1:8000/dashboard-simple.html
```

- Real-time whale transaction table
- 24-hour volume summaries
- Live system status
- Sortable, clickable (links to Etherscan)

### The REST API

```
http://127.0.0.1:5000/api
```

Designed for other systems (bots, agents) to query:

```bash
# Get whale summary
curl http://127.0.0.1:5000/api/summary

# Get all whales from last 6 hours
curl http://127.0.0.1:5000/api/whales?hours=6

# Get critical alerts
curl http://127.0.0.1:5000/api/alerts/critical
```

### The JSON Feed

Auto-generated file: `whale_data.json`

Other systems can read this directly for real-time whale data.

---

## 🤖 How to Use (For Autonomous Systems)

### Example 1: Python Bot Subscribing to Alerts

```python
import aiohttp
import asyncio

async def subscribe_to_whale_alerts():
    async with aiohttp.ClientSession() as session:
        # Subscribe to critical whales
        payload = {
            "webhook_url": "https://my-bot.com/webhook/whales",
            "severity": "critical",
            "agent_name": "my-trading-bot"
        }
        
        async with session.post(
            "http://127.0.0.1:5000/api/subscribe",
            json=payload
        ) as resp:
            result = await resp.json()
            print(f"Subscribed: {result['subscription_id']}")

asyncio.run(subscribe_to_whale_alerts())
```

Now your bot receives real-time webhook POST requests whenever a whale moves.

### Example 2: Query Whale Data

```python
import aiohttp

async def get_recent_whales():
    async with aiohttp.ClientSession() as session:
        # Get whales from last 12 hours
        async with session.get(
            "http://127.0.0.1:5000/api/whales?hours=12&limit=10"
        ) as resp:
            data = await resp.json()
            
            for whale in data['eth_whales']:
                print(f"🐋 {whale['value_eth']} ETH moved")
                print(f"   From: {whale['from']}")
                print(f"   To: {whale['to']}")
```

---

## 📊 API Endpoints

### GET /api/summary

**Returns:** System status + whale count

```bash
curl http://127.0.0.1:5000/api/summary
```

```json
{
  "recent_eth_whales_count": 5,
  "recent_usdc_whales_count": 2,
  "total_eth_volume": 1250.45,
  "total_usdc_volume": 450000,
  "last_update": "2026-02-07T19:30:15.243871",
  "system_status": "online"
}
```

---

### GET /api/whales

**Returns:** List of detected whale movements

```bash
curl http://127.0.0.1:5000/api/whales?hours=24&limit=50
```

**Query parameters:**
- `hours` — Last N hours (default: 24)
- `limit` — Max results (default: 50)
- `type` — `eth` or `usdc` (optional)

```json
{
  "eth_whales": [
    {
      "hash": "0xfccc611f...",
      "from": "0x129ab3a...",
      "to": "0xc36442b...",
      "value_eth": 600.31,
      "value_usd": 1800000,
      "timestamp": "2026-02-07T19:30:10.000Z"
    }
  ]
}
```

---

### GET /api/alerts/critical

**Returns:** Critical-severity alerts only

```bash
curl http://127.0.0.1:5000/api/alerts/critical?hours=6
```

```json
{
  "alerts": [
    {
      "alert_id": "uuid_here",
      "severity": "critical",
      "type": "eth_whale",
      "amount": 600.31,
      "recommended_action": "INVESTIGATE",
      "timestamp": "2026-02-07T19:30:10.000Z"
    }
  ]
}
```

---

### POST /api/subscribe

**Subscribe to webhook alerts**

```bash
curl -X POST http://127.0.0.1:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://my-bot.com/webhook/whales",
    "severity": "critical",
    "agent_name": "my-agent"
  }'
```

Your webhook receives POST requests like:

```json
{
  "alert_id": "uuid",
  "severity": "critical",
  "type": "eth_whale",
  "amount": 600.31,
  "from": "0x129ab3a...",
  "to": "0xc36442b...",
  "hash": "0xfccc611f...",
  "timestamp": "2026-02-07T19:30:10.000Z",
  "action": "INVESTIGATE"
}
```

---

### GET /api/health

**System status check**

```bash
curl http://127.0.0.1:5000/api/health
```

```json
{
  "status": "ok",
  "whales_tracked": 42,
  "last_update": "2026-02-07T19:30:15.243871",
  "uptime_seconds": 3600
}
```

---

## ⚙️ Configuration

Edit `.env` to adjust behavior:

```
# How sensitive whale detection is
WHALE_ETH_THRESHOLD=100        # Default: 100 ETH
WHALE_USDC_THRESHOLD=100000    # Default: $100K USDC

# Scanning speed
SCAN_INTERVAL_SECONDS=12       # Check every N seconds
BLOCKS_PER_SCAN=5              # Scan N blocks per check
```

**Trade-offs:**
- **Lower threshold** = More whales detected, more noise
- **Higher threshold** = Fewer whales, higher confidence
- **Faster scanning** = More responsive, higher API usage
- **Slower scanning** = Less responsive, lower API usage

---

## 🚀 Deployment

### Local Development

```bash
./start_whale_watch.sh
```

This starts:
- Whale tracker (backend)
- REST API (port 5000)
- Dashboard (port 8000)

### Production (Linux/Mac)

```bash
# Run in background
nohup python3 whale_tracker_integrated.py > whale_watch.log 2>&1 &
nohup python3 whale_api.py > api.log 2>&1 &

# Or use systemd/supervisor for persistent service
```

### Docker (Optional)

```bash
docker build -t whale-watch .
docker run -p 5000:5000 -p 8000:8000 whale-watch
```

---

## 🔍 How It Works (Technical)

```
Ethereum Blockchain
        ↓
   Etherscan API (free tier, 5 calls/sec)
        ↓
whale_tracker.py (async Python)
    - Fetch latest block
    - Scan for ETH transfers >100 ETH
    - Parse USDC token transfers >$100K
    - Profile wallet types
    - Generate alerts
        ↓
whale_data.json (atomic JSON write)
        ↓
    ├─→ Dashboard (HTML reads JSON)
    ├─→ REST API (agents query endpoints)
    └─→ Webhooks (real-time alerts)
```

### Architecture

- **whale_tracker_integrated.py** — Main scanning engine
- **whale_api.py** — FastAPI REST server
- **whale_profiler.py** — Whale type identification
- **alert_system.py** — Alert generation + webhooks
- **dashboard-simple.html** — Web UI (single file)

---

## 🐛 Troubleshooting

### "API Key not found"

```bash
# Make sure .env exists
ls -la .env

# Make sure it has your key
cat .env | grep ETHERSCAN_API_KEY
```

Should show: `ETHERSCAN_API_KEY=your_actual_key`

---

### "No whales detected"

Possible causes:
1. **Threshold too high** — Lower it in `.env`
2. **Network is quiet** — Try again in 1-2 minutes
3. **System just started** — Give it 2-3 minutes to find data

```bash
# Temporarily lower threshold
WHALE_ETH_THRESHOLD=50
```

---

### "Dashboard shows no data"

1. Check Python script is running:
   ```bash
   ps aux | grep whale_tracker
   ```

2. Check if `whale_data.json` exists:
   ```bash
   ls -la whale_data.json
   ```

3. Refresh browser (Ctrl+F5 to clear cache)

4. Check browser console (F12) for errors

---

### "Port already in use"

```bash
# Find process on port 5000
lsof -i :5000
kill -9 <PID>

# Find process on port 8000
lsof -i :8000
kill -9 <PID>

# Restart
./start_whale_watch.sh
```

---

### "Rate limit exceeded"

Etherscan free tier: 5 calls/sec max

Solution: Increase scan interval or reduce blocks per scan

```
SCAN_INTERVAL_SECONDS=20  # Instead of 12
```

---

## 📈 Performance

- **CPU:** <5% at idle, <15% during scans
- **Memory:** ~50MB
- **Storage:** ~10MB for code
- **Network:** 1-2 Mbps
- **Uptime:** 99%+ with proper error handling

---

## 🔐 Security Notes

⚠️ **Never:**
- Commit `.env` to Git (use `.env.example` instead)
- Share your Etherscan API key
- Use mainnet wallets/keys
- Trust third-party webhook URLs

✅ **Do:**
- Keep `.env` local and private
- Rotate API keys periodically
- Use HTTPS for webhook URLs
- Validate webhook signatures

---

## 📝 Requirements

- Python 3.9+
- 50MB disk space
- 1-2 Mbps internet
- Free Etherscan API key

**Dependencies:**
- `aiohttp` — Async HTTP
- `fastapi` — REST API
- `uvicorn` — ASGI server
- `python-dotenv` — Environment config

---

## 💡 Use Cases

1. **Trading Bot Input** — Feed whale signals into your trading logic
2. **Market Research** — Analyze whale behavior patterns
3. **DeFi Protocol** — Monitor large transfers for risk management
4. **Autonomous Agent** — Let agents react to whale movements
5. **Alert System** — Webhook notifications to Slack, Discord, etc.

---

## 📚 More Info

- **Etherscan API Docs:** https://docs.etherscan.io
- **Ethereum RPC Guide:** https://www.alchemy.com/sdk/eth
- **FastAPI Docs:** https://fastapi.tiangolo.com

---

## 📄 License

MIT - Use freely, modify, distribute

---

## ❓ Questions?

- Check Troubleshooting section above
- Review API examples
- Open an issue on GitHub

---

**Built for autonomous systems and traders who want real-time whale intelligence.**

Last updated: February 2026
