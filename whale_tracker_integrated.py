#!/usr/bin/env python3
"""
Whale Watch - Integrated Version
Combines core tracker + whale profiler + alert system
Displays enriched data in whale_data.json for dashboard
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
BASE_URL = "https://api.etherscan.io/v2/api?"
CHAIN_ID = "1"
USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b06830e3606e948a6837273b988c8d9168cf7d3c9f6e"

DATA_FILE = "whale_data.json"

# Known exchange addresses (simplified)
KNOWN_EXCHANGES = {
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch",
    "0x68b3465833fb72b5a828cefedaf081fcf87985d86": "Uniswap",
    "0x881d40237659c3889fa846dc609271767e1e4361": "Lido",
    "0x8ba1f109551bd432803012645ac136ddd64dba72": "Curve",
    "0xdafea492d9c6733e3b819972800123369113cbb7": "OpenSea",
}

class WhaleTracker:
    def __init__(self):
        self.session = None
        self.analytics_data = {
            "last_updated": None,
            "eth_whales": [],
            "usdc_whales": [],
            "whale_profiles": {},  # NEW: whale enrichment
            "alerts": [],  # NEW: alert history
            "summary": {}
        }
        self.profile_cache = {}  # Cache whale profiles

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_api_key(self) -> str:
        """Load API key from environment."""
        key = os.getenv("ETHERSCAN_API_KEY", "").strip()
        if not key:
            print("❌ CRITICAL ERROR: Missing ETHERSCAN_API_KEY")
            print("📝 Set it in .env file: ETHERSCAN_API_KEY=your_key_here")
            sys.exit(1)
        return key

    async def _get(self, url: str) -> Optional[Dict]:
        """Generic GET request."""
        api_key = self._get_api_key()
        full_url = f"{url}&chainid={CHAIN_ID}&apikey={api_key}"
        
        try:
            async with self.session.get(full_url) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                
                if 'jsonrpc' in data:
                    return data.get('result')
                elif data.get('status') == '1':
                    return data.get('result')
                else:
                    return None
        except Exception as e:
            return None

    async def get_block_number(self) -> Optional[int]:
        """Get current block number."""
        result = await self._get(f"{BASE_URL}&module=proxy&action=eth_blockNumber")
        if result:
            return int(result, 16)
        return None

    async def get_block(self, block_number: int) -> Optional[Dict]:
        """Get block details."""
        block_hex = hex(block_number)
        result = await self._get(f"{BASE_URL}&module=proxy&action=eth_getBlockByNumber&tag={block_hex}&boolean=true")
        return result

    async def get_logs(self, from_block: int, to_block: int) -> List[Dict]:
        """Get event logs (USDC transfers)."""
        result = await self._get(f"{BASE_URL}&module=logs&action=getLogs&address={USDC_CONTRACT}&topic0={USDC_TRANSFER_TOPIC}&fromBlock={hex(from_block)}&toBlock={hex(to_block)}")
        return result if result else []

    async def get_wallet_balance(self, address: str) -> Optional[float]:
        """Get wallet balance in ETH (for profiling)."""
        result = await self._get(f"{BASE_URL}&module=account&action=balance&address={address}")
        if result:
            return int(result) / 10**18
        return None

    def is_whale_eth(self, value_wei: int) -> bool:
        return value_wei > 10**20  # >100 ETH

    def is_whale_usdc(self, value_wei: int) -> bool:
        return value_wei > (100_000 * 10**6)  # >$100k USDC

    def _profile_whale(self, address: str, outbound_value: float = 0) -> Dict[str, Any]:
        """Identify whale type based on address."""
        
        # Check cache
        if address in self.profile_cache:
            return self.profile_cache[address]
        
        profile = {
            "address": address,
            "whale_type": "unknown",
            "confidence": 0.5,
            "description": ""
        }
        
        # Check if it's a known exchange
        lower_addr = address.lower()
        for exchange_addr, exchange_name in KNOWN_EXCHANGES.items():
            if lower_addr == exchange_addr.lower():
                profile["whale_type"] = "exchange_cold"
                profile["confidence"] = 0.95
                profile["description"] = f"Identified as {exchange_name} address"
                break
        
        # Check address characteristics
        if lower_addr.startswith("0x0"):
            profile["whale_type"] = "contract"
            profile["confidence"] = 0.8
            profile["description"] = "Smart contract address"
        elif lower_addr.endswith("000") or lower_addr.endswith("111"):
            profile["whale_type"] = "suspicious"
            profile["confidence"] = 0.6
            profile["description"] = "Unusual address pattern"
        else:
            # Default to private whale
            if profile["whale_type"] == "unknown":
                profile["whale_type"] = "private_whale"
                profile["confidence"] = 0.7
                profile["description"] = "Private/institutional whale"
        
        self.profile_cache[address] = profile
        return profile

    def _generate_alert(self, whale_addr: str, value_eth: float, value_usdc: float, 
                       tx_hash: str, whale_profile: Dict) -> Optional[Dict]:
        """Generate alert if thresholds met."""
        
        # Alert thresholds
        CRITICAL_ETH = 500
        CRITICAL_USDC = 500_000
        
        if value_eth < CRITICAL_ETH and value_usdc < CRITICAL_USDC:
            return None  # Not critical
        
        severity = "critical" if (value_eth >= CRITICAL_ETH or value_usdc >= CRITICAL_USDC) else "high"
        
        alert = {
            "id": tx_hash[:16],
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "whale_type": whale_profile.get("whale_type", "unknown"),
            "value_eth": value_eth,
            "value_usdc": value_usdc,
            "address": whale_addr,
            "tx_hash": tx_hash,
            "message": f"🐋 {severity.upper()}: {value_eth:.2f} ETH whale ({whale_profile.get('whale_type')})"
        }
        
        return alert

    async def scan_block_eth(self, block: Dict) -> List[Dict]:
        """Scan block for ETH whales with profiling."""
        whales = []
        transactions = block.get('transactions', [])
        timestamp = block.get('timestamp', '')
        
        for tx in transactions:
            value_wei = int(tx.get('value', '0x0'), 16)
            if self.is_whale_eth(value_wei):
                from_addr = tx.get('from', '')
                to_addr = tx.get('to', '')
                
                # Profile the whale
                profile = self._profile_whale(from_addr, value_wei / 10**18)
                
                whale_data = {
                    "hash": tx.get('hash', ''),
                    "from": from_addr,
                    "to": to_addr,
                    "value_eth": value_wei / 10**18,
                    "value_usdc": 0,
                    "timestamp": timestamp,
                    "whale_profile": profile
                }
                
                whales.append(whale_data)
                
                # Generate alert if critical
                alert = self._generate_alert(from_addr, whale_data["value_eth"], 0, 
                                           whale_data["hash"], profile)
                if alert:
                    self.analytics_data["alerts"].append(alert)
        
        return whales

    async def scan_block_usdc(self, logs: List[Dict], block_timestamp: str) -> List[Dict]:
        """Scan logs for USDC whales with profiling."""
        whales = []
        for log in logs:
            try:
                data_field = log.get('data', '0x')
                topics = log.get('topics', [])
                
                if len(topics) >= 3:
                    to_address = "0x" + topics[2][-40:]
                    value_wei = int(data_field, 16)
                    
                    if self.is_whale_usdc(value_wei):
                        from_address = "0x" + topics[1][-40:]
                        
                        # Profile the whale
                        profile = self._profile_whale(to_address, value_usdc=value_wei / 10**6)
                        
                        whale_data = {
                            "to": to_address,
                            "from": from_address,
                            "hash": log.get('transactionHash', '0x...'),
                            "value_wei": value_wei,
                            "value_usdc": value_wei / 10**6,
                            "timestamp": block_timestamp,
                            "whale_profile": profile
                        }
                        
                        whales.append(whale_data)
                        
                        # Generate alert if critical
                        alert = self._generate_alert(to_address, 0, whale_data["value_usdc"],
                                                   whale_data["hash"], profile)
                        if alert:
                            self.analytics_data["alerts"].append(alert)
            except:
                pass
        
        return whales

    def update_dashboard_data(self, eth_whales: List, usdc_whales: List):
        """Update data file with whale + profile + alert info."""
        now = datetime.now().isoformat()
        
        current_eth = self.analytics_data.get('eth_whales', [])
        current_usdc = self.analytics_data.get('usdc_whales', [])
        
        new_eth = (eth_whales + current_eth)[:50]
        new_usdc = (usdc_whales + current_usdc)[:50]
        
        self.analytics_data["last_updated"] = now
        self.analytics_data["eth_whales"] = new_eth
        self.analytics_data["usdc_whales"] = new_usdc
        
        # Keep only recent alerts
        self.analytics_data["alerts"] = self.analytics_data["alerts"][-100:]
        
        self.analytics_data["summary"] = {
            "recent_eth_whales_count": len(eth_whales),
            "recent_usdc_whales_count": len(usdc_whales),
            "total_tracked": len(new_eth) + len(new_usdc),
            "total_alerts": len(self.analytics_data["alerts"]),
            "critical_alerts": len([a for a in self.analytics_data["alerts"] if a.get("severity") == "critical"])
        }

        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.analytics_data, f, indent=2, default=str)
            print(f"✅ Dashboard updated at {now}")
            if eth_whales or usdc_whales:
                print(f"   ETH: {len(eth_whales)}, USDC: {len(usdc_whales)}, Alerts: {len(self.analytics_data['alerts'])}")
        except Exception as e:
            print(f"❌ Failed to update dashboard: {e}")

    async def run_scan_loop(self, blocks_per_scan: int = 5):
        """Main scanning loop."""
        print("🐋 Starting Whale Watch - INTEGRATED VERSION")
        print(f"📊 Features: Tracker + Profiler + Alerts")
        print(f"🔍 Scanning every 12 seconds...\n")
        
        async with self:
            while True:
                current_block = await self.get_block_number()
                if not current_block:
                    print("⏳ Waiting for connection...")
                    await asyncio.sleep(5)
                    continue

                start_block = current_block - blocks_per_scan
                print(f"🔎 Scanning blocks {start_block} to {current_block}...", end='\r')
                
                # Fetch in parallel
                block_task = self.get_block(current_block)
                logs_task = self.get_logs(start_block, current_block)
                
                block_data, logs = await asyncio.gather(block_task, logs_task, return_exceptions=True)
                
                block_data = block_data if not isinstance(block_data, Exception) else None
                logs = logs if not isinstance(logs, Exception) else []
                
                eth_whales = []
                usdc_whales = []
                
                if block_data:
                    ts_hex = block_data.get('timestamp', '0x0')
                    try:
                        ts_int = int(ts_hex, 16)
                        timestamp_iso = datetime.fromtimestamp(ts_int).isoformat()
                    except:
                        timestamp_iso = datetime.now().isoformat()
                    
                    eth_whales = await self.scan_block_eth(block_data)
                    usdc_whales = await self.scan_block_usdc(logs, timestamp_iso)
                
                # ALWAYS update to show system is alive (even if no whales)
                self.update_dashboard_data(eth_whales, usdc_whales)
                
                if eth_whales or usdc_whales:
                    print(f"\n🐋 Found {len(eth_whales)} ETH and {len(usdc_whales)} USDC whale(s)!")
                    
                    for w in eth_whales[:2]:
                        profile = w.get('whale_profile', {})
                        print(f"  🐋 {w['value_eth']:.2f} ETH ({profile.get('whale_type', 'unknown')})")
                    
                    for w in usdc_whales[:2]:
                        profile = w.get('whale_profile', {})
                        print(f"  💵 ${w['value_usdc']:,.0f} USDC ({profile.get('whale_type', 'unknown')})")
                else:
                    print(f"\r  ✅ Scan complete. No whales this round.", end='')
                
                await asyncio.sleep(12)

if __name__ == "__main__":
    tracker = WhaleTracker()
    try:
        asyncio.run(tracker.run_scan_loop(blocks_per_scan=5))
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping tracker...")
        print("✅ Data saved to whale_data.json")
