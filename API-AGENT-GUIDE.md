# 🐋 Whale Watch API - Agent Integration Guide

**For AI Agents: How to integrate whale tracking into your autonomous system**

---

## 🎯 Quick Start (For Agents)

### 1. **Get Latest Whale Data**
```bash
curl http://127.0.0.1:5000/api/whales
```

### 2. **Get Critical Alerts Only**
```bash
curl http://127.0.0.1:5000/api/alerts/critical
```

### 3. **Subscribe to Real-Time Updates**
```bash
curl -X POST http://127.0.0.1:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-agent.com/webhook",
    "severity": "critical",
    "agent_name": "my-trading-bot"
  }'
```

---

## 📡 Complete API Reference

### **Health Check**
```
GET /api/health
```
**Use this to:** Verify Whale Watch is running before executing trades
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0",
  "last_data_update": "2026-02-07T21:42:15.123456",
  "tracked_whales": {
    "eth": 5,
    "usdc": 3
  },
  "total_alerts": 8
}
```

---

### **Get Whales (Filterable)**
```
GET /api/whales?type=eth&min_eth=500&whale_type=private_whale&limit=20
```

**Query Parameters:**
| Parameter | Type | Example | Purpose |
|-----------|------|---------|---------|
| `type` | string | `eth`, `usdc`, or `all` | Filter by asset type |
| `min_eth` | float | `500` | Minimum ETH threshold |
| `min_usdc` | float | `500000` | Minimum USDC threshold |
| `whale_type` | string | `private_whale`, `exchange_cold`, `contract` | Filter by whale classification |
| `limit` | int | `50` | Max results (default: 100) |

**Example Request:**
```bash
# Get all private whales moving >100 ETH in last 50 results
curl "http://127.0.0.1:5000/api/whales?type=eth&min_eth=100&whale_type=private_whale&limit=50"
```

**Response:**
```json
{
  "whales": [
    {
      "hash": "0x661a863bc...",
      "from": "0xf8191d98...",
      "to": "0xeae7380d...",
      "value_eth": 956.0,
      "whale_profile": {
        "address": "0xf8191d98...",
        "whale_type": "private_whale",
        "confidence": 0.7,
        "description": "Private/institutional whale"
      },
      "timestamp": "2026-02-07T21:40:00.000Z"
    }
  ],
  "count": 1,
  "timestamp": "2026-02-07T21:42:15.123456"
}
```

---

### **Get Alerts (Filterable)**
```
GET /api/alerts?severity=critical&whale_type=private_whale&hours=12&limit=50
```

**Query Parameters:**
| Parameter | Type | Example | Purpose |
|-----------|------|---------|---------|
| `severity` | string | `critical`, `high`, `medium`, `low` | Alert severity level |
| `whale_type` | string | `private_whale`, `exchange_cold` | Filter by whale type |
| `hours` | int | `24` | Lookback period (default: 24) |
| `limit` | int | `100` | Max results |

**Example Request:**
```bash
# Get critical alerts from last 6 hours
curl "http://127.0.0.1:5000/api/alerts?severity=critical&hours=6"
```

**Response:**
```json
{
  "count": 2,
  "alerts": [
    {
      "id": "0x661a863b",
      "timestamp": "2026-02-07T21:40:15.000Z",
      "severity": "critical",
      "whale_type": "private_whale",
      "value_eth": 956.0,
      "value_usdc": 0,
      "message": "🐋 CRITICAL: 956.00 ETH whale (private_whale)",
      "tx_hash": "0x661a863bc0888f0ef..."
    }
  ],
  "filters": {
    "severity": "critical",
    "whale_type": null,
    "hours": 6
  },
  "timestamp": "2026-02-07T21:42:15.123456"
}
```

---

### **Get System Summary**
```
GET /api/summary
```
**Use this to:** Quick status check before making trading decisions
**Response:**
```json
{
  "system_status": "operational",
  "api_version": "1.0",
  "last_updated": "2026-02-07T21:42:15.123456",
  "summary": {
    "recent_eth_whales_count": 5,
    "recent_usdc_whales_count": 3,
    "total_tracked": 8,
    "total_alerts": 12,
    "critical_alerts": 2
  },
  "eth_whales_count": 5,
  "usdc_whales_count": 3,
  "total_alerts": 12,
  "critical_alerts": 2
}
```

---

### **Get Statistics**
```
GET /api/stats?hours=24
```
**Use this to:** Analyze whale activity patterns
**Response:**
```json
{
  "period_hours": 24,
  "eth_whales": {
    "count": 5,
    "total_eth": 2565.57,
    "total_usd": 6413925.0
  },
  "usdc_whales": {
    "count": 3,
    "total_usdc": 1500000.0
  },
  "whale_types": {
    "exchange_cold": 1,
    "private_whale": 4,
    "contract": 2
  }
}
```

---

## 🔔 Webhook Alerts (For Agent Subscribers)

### **Subscribe to Alerts**
```
POST /api/subscribe
Content-Type: application/json

{
  "webhook_url": "https://your-agent-server.com/webhook",
  "severity": "critical",
  "whale_type": "private_whale",
  "agent_name": "autonomous-trader-bot-v1"
}
```

**Response:**
```json
{
  "subscription_id": "sub_a7f8b2c9",
  "status": "active",
  "webhook_url": "https://your-agent-server.com/webhook"
}
```

### **What Your Agent Receives (Webhook Payload)**

When a whale meets your criteria, Whale Watch POSTs to your webhook:

```json
{
  "event": "whale_alert",
  "id": "0x661a863b",
  "type": "critical_movement",
  "severity": "critical",
  "timestamp": "2026-02-07T21:40:15.000Z",
  "whale": {
    "address": "0xf8191d98ae98d2f7abdfb63a9b0b812b93c873aa",
    "profile": {
      "address": "0xf8191d98ae98d2f7abdfb63a9b0b812b93c873aa",
      "whale_type": "private_whale",
      "confidence": 0.7
    }
  },
  "transaction": {
    "hash": "0x661a863bc0888f0ef3e5813ab3dc481fdadf960b87cd3e37d77663eb7a29081c",
    "value_eth": 956.0,
    "value_usd": 2390000.0,
    "direction": "outbound"
  },
  "market_impact": {
    "affected_pools": ["ETH-USDC"],
    "price_impact": null
  },
  "confidence": 0.7,
  "recommended_action": "MONITOR_CLOSELY | BE_READY_TO_SELL"
}
```

### **Unsubscribe from Alerts**
```
DELETE /api/subscriptions/{subscription_id}
```

---

## 💻 Code Examples

### **Python Agent (Async)**
```python
import aiohttp
import asyncio

class WhaleWatchAgent:
    def __init__(self):
        self.api_base = "http://127.0.0.1:5000/api"
    
    async def get_critical_alerts(self):
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_base}/alerts/critical?hours=6"
            async with session.get(url) as resp:
                alerts = await resp.json()
                return alerts.get('alerts', [])
    
    async def check_health(self):
        async with aiohttp.ClientSession() as session:
            url = f"{self.api_base}/health"
            async with session.get(url) as resp:
                health = await resp.json()
                return health['status'] == 'healthy'
    
    async def execute_trade_on_alert(self):
        # Check if API is healthy first
        if not await self.check_health():
            print("API unavailable, waiting...")
            return
        
        # Get critical alerts
        alerts = await self.get_critical_alerts()
        
        for alert in alerts:
            if alert['severity'] == 'critical':
                # Execute trading logic
                value = alert['value_eth'] if alert['value_eth'] > 0 else alert['value_usdc']
                print(f"ALERT: {value} whale detected - executing trade")
                # Add your trading logic here
                pass

# Usage
agent = WhaleWatchAgent()
asyncio.run(agent.execute_trade_on_alert())
```

### **JavaScript Agent**
```javascript
class WhaleWatchAgent {
  constructor() {
    this.apiBase = "http://127.0.0.1:5000/api";
  }

  async getWhales(minEth = 500) {
    const response = await fetch(
      `${this.apiBase}/whales?type=eth&min_eth=${minEth}`
    );
    return await response.json();
  }

  async subscribeToAlerts(webhookUrl, severity = "critical") {
    const response = await fetch(`${this.apiBase}/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        webhook_url: webhookUrl,
        severity: severity,
        agent_name: "js-agent-v1"
      })
    });
    return await response.json();
  }

  async onWhaleAlert(alertData) {
    // Handle incoming alert from webhook
    console.log("WHALE ALERT:", alertData);
    // Execute your trading logic
  }
}

// Usage
const agent = new WhaleWatchAgent();
await agent.subscribeToAlerts("https://my-agent.com/webhook");
```

---

## 🔐 Best Practices for Agents

1. **Check Health First**
   ```bash
   curl http://127.0.0.1:5000/api/health
   ```
   Always verify Whale Watch is running before trading.

2. **Use Confidence Scores**
   - Only trade on whale_profile.confidence > 0.7
   - This filters out uncertain classifications

3. **Monitor Different Whale Types**
   - `exchange_cold`: Institutional moves, likely volatility
   - `private_whale`: Unpredictable, high impact
   - `contract`: Often liquidity-related, moderate impact

4. **Batch Requests**
   - Get all data once per scan cycle
   - Don't hammer the API with individual requests

5. **Implement Retry Logic**
   - Whale Watch updates every 12 seconds
   - Retry alerts that fail delivery
   - Use exponential backoff

---

## 📊 API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | System health check |
| GET | `/api/whales` | Get all whales (filterable) |
| GET | `/api/whales/eth` | Get ETH whales only |
| GET | `/api/whales/usdc` | Get USDC whales only |
| GET | `/api/alerts` | Get alerts (filterable) |
| GET | `/api/alerts/critical` | Get critical alerts only |
| GET | `/api/summary` | Quick system overview |
| GET | `/api/stats` | Whale activity statistics |
| POST | `/api/subscribe` | Subscribe to webhook alerts |
| GET | `/api/subscriptions` | List active subscriptions |
| DELETE | `/api/subscriptions/{id}` | Unsubscribe |
| GET | `/api/download` | Download whale_data.json |
| GET | `/api/docs` | API documentation |

---

## 🚀 Ready to Integrate?

The Whale Watch API is **designed for AI agents**. It provides:
- ✅ Real-time whale data (updated every 12 seconds)
- ✅ Intelligent filtering (by severity, type, value)
- ✅ Webhook subscriptions (for autonomous reactions)
- ✅ Minimal latency (JSON over HTTP)
- ✅ No authentication needed (agent-friendly)

**Your agent can now make autonomous trading decisions based on real-time whale movements.** 🐋⚡

---

**Questions?** Check `/api/docs` for live documentation.

