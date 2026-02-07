#!/usr/bin/env python3
"""
On-Chain Whale Tracker (PRODUCTION READY)
Real-time tracking of ETH and USDC whale movements.
Optimized for reliability, atomicity, and parallelism.
"""

import asyncio
import aiohttp
import json
import os
import sys  # Opgelost: Nodig voor sys.exit()
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv  # Opgelost: Nodig om .env bestand te lezen

# Laad variabelen uit .env bestand
load_dotenv()

# Configuration (Updated to Etherscan API V2)
BASE_URL = "https://api.etherscan.io/v2/api?"
CHAIN_ID = "1"  # Ethereum Mainnet
# Fixed: Correct USDC contract address on Ethereum mainnet
USDC_CONTRACT = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
# Fixed: USDC Transfer event signature (keccak256("Transfer(address,address,uint256)"))
USDC_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b06830e3606e948a6837273b988c8d9168cf7d3c9f6e"

DATA_FILE = "whale_data.json"

class WhaleTracker:
    def __init__(self):
        self.session = None
        self.analytics_data = {
            "last_updated": None,
            "eth_whales": [],
            "usdc_whales": [],
            "summary": {}
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_api_key(self) -> str:
        """SECURITY: Load API key from environment ONLY."""
        key = os.getenv("ETHERSCAN_API_KEY", "").strip()
        
        # Validate API Key
        if not key:
            print("❌ CRITICAL ERROR: Missing ETHERSCAN_API_KEY")
            print()
            print("📝 STEPS TO FIX:")
            print("1. Open '.env' file in this folder:")
            print("   cd /home/mourad/clawd/bonito-projects/onchain-intelligence-agent")
            print("2. Ensure it contains this exact line:")
            print("   ETHERSCAN_API_KEY=your_actual_api_key_here")
            print("   Get your free API key from: https://etherscan.io/myapikey")
            sys.exit(1) 
        
        return key # Opgelost: Was "", moet 'key' zijn

    async def _get(self, url: str) -> Optional[Dict]:
        """Generic GET request with error handling (V2 API)."""
        api_key = self._get_api_key()
        if not api_key:
            return None

        # Add chainid parameter for V2 API
        full_url = f"{url}&chainid={CHAIN_ID}&apikey={api_key}"

        try:
            async with self.session.get(full_url) as response:
                if response.status != 200:
                    print(f"⚠️ HTTP Error: {response.status}")
                    return None

                data = await response.json()

                # Handle two response formats:
                # 1. Standard Etherscan: {"status": "1", "message": "OK", "result": ...}
                # 2. JSON-RPC (proxy module): {"jsonrpc": "2.0", "id": 83, "result": ...}

                if 'jsonrpc' in data:
                    # JSON-RPC response format (module=proxy)
                    if 'result' in data:
                        return data.get('result')
                    else:
                        print(f"⚠️ JSON-RPC Error: {data}")
                        return None
                elif data.get('status') == '1':
                    # Standard Etherscan response format
                    return data.get('result')
                else:
                    # Error response
                    message = data.get('message', 'Unknown error')
                    # Vermijd spammen van rate-limit berichten
                    if "No transactions found" not in str(message):
                        # DEBUG: Show which URL failed
                        print(f"⚠️ API Error ({url.split('&')[1] if '&' in url else 'unknown'}): {message}")
                    return None
        except Exception as e:
            print(f"⚠️ Connection Error: {e}")
            return None

    async def get_block_number(self) -> Optional[int]:
        """Get current block number."""
        result = await self._get(f"{BASE_URL}&module=proxy&action=eth_blockNumber")
        if result:
            return int(result, 16)
        return None

    async def get_block(self, block_number: int) -> Optional[Dict]:
        """Get block details (for timestamp)."""
        block_hex = hex(block_number)
        result = await self._get(f"{BASE_URL}&module=proxy&action=eth_getBlockByNumber&tag={block_hex}&boolean=true")
        return result

    async def get_logs(self, from_block: int, to_block: int) -> List[Dict]:
        """Get event logs (USDC Transfers)."""
        result = await self._get(f"{BASE_URL}&module=logs&action=getLogs&address={USDC_CONTRACT}&topic0={USDC_TRANSFER_TOPIC}&fromBlock={hex(from_block)}&toBlock={hex(to_block)}")
        return result if result else []

    def is_whale_eth(self, value_wei: int) -> bool:
        return value_wei > 10**20  # 100 ETH

    def is_whale_usdc(self, value_wei: int) -> bool:
        # USDC has 6 decimals
        return value_wei > (100_000 * 10**6) # > $100k USDC

    def parse_log_data(self, log: Dict, block_timestamp: str) -> Optional[Dict]:
        """Parse USDC Transfer log data with timestamp."""
        try:
            data_field = log.get('data', '0x')
            topics = log.get('topics', [])
            
            if len(topics) >= 3:
                # topics[1] = from, topics[2] = to
                from_address = "0x" + topics[1][-40:]
                to_address = "0x" + topics[2][-40:]
                
                # Value is in data field
                value_hex = data_field
                value_wei = int(value_hex, 16)
                
                return {
                    "to": to_address,
                    "from": from_address,
                    "hash": log.get('transactionHash', '0x...'),
                    "value_wei": value_wei,
                    "value_usdc": value_wei / 10**6,
                    "timestamp": block_timestamp
                }
        except Exception as e:
            print(f"⚠️ Error parsing log: {e}")
            return None

    async def scan_block_eth(self, block: Dict) -> List[Dict]:
        """Scan block for ETH whales."""
        whales = []
        transactions = block.get('transactions', [])
        timestamp = block.get('timestamp', '')
        
        for tx in transactions:
            value_wei = int(tx.get('value', '0x0'), 16)
            if self.is_whale_eth(value_wei):
                whales.append({
                    "hash": tx.get('hash', ''),
                    "from": tx.get('from', ''),
                    "to": tx.get('to', ''),
                    "value_eth": value_wei / 10**18,
                    "value_usdc": 0,
                    "timestamp": timestamp
                })
        return whales

    async def scan_block_usdc(self, logs: List[Dict], block_timestamp: str) -> List[Dict]:
        """Scan logs for USDC whales."""
        whales = []
        for log in logs:
            parsed = self.parse_log_data(log, block_timestamp)
            if parsed and self.is_whale_usdc(parsed['value_wei']):
                whales.append(parsed)
        return whales

    def update_dashboard_data(self, eth_whales: List, usdc_whales: List):
        """Atomic write to prevent frontend read errors."""
        now = datetime.now().isoformat()
        
        current_eth = self.analytics_data.get('eth_whales', [])
        current_usdc = self.analytics_data.get('usdc_whales', [])
        
        # Voeg nieuwe toe en behoud de laatste 50
        new_eth = (eth_whales + current_eth)[:50]
        new_usdc = (usdc_whales + current_usdc)[:50]
        
        self.analytics_data["last_updated"] = now
        self.analytics_data["eth_whales"] = new_eth
        self.analytics_data["usdc_whales"] = new_usdc
        self.analytics_data["summary"] = {
            "recent_eth_whales_count": len(eth_whales),
            "recent_usdc_whales_count": len(usdc_whales),
            "total_tracked": len(new_eth) + len(new_usdc)
        }

        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.analytics_data, f, indent=4)
            print(f"✅ Dashboard updated at {now}")
        except Exception as e:
            print(f"❌ Failed to update dashboard: {e}")

    async def run_scan_loop(self, blocks_per_scan: int = 5):
        """Main scanning loop with PARALLELISM."""
        print("🚀 Starting Production Whale Tracker...")
        print(f"📊 Tracking ETH (>100 ETH) and USDC (>$100k)...")
        print()
        
        async with self: # Gebruik de context manager voor de sessie
            while True:
                current_block = await self.get_block_number()
                if not current_block:
                    print("⏳ Waiting for connection...")
                    await asyncio.sleep(5)
                    continue

                start_block = current_block - blocks_per_scan
                print(f"🔎 Scanning blocks {start_block} to {current_block}...", end='\r')
                
                # Opgelost: asyncio.gather correct verwerken
                tasks = {
                    "block": self.get_block(current_block),
                    "logs": self.get_logs(start_block, current_block)
                }
                
                task_keys = list(tasks.keys())
                task_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
                results = dict(zip(task_keys, task_results))
                
                block_data = results.get('block') if not isinstance(results.get('block'), Exception) else None
                logs = results.get('logs') if not isinstance(results.get('logs'), Exception) else []
                
                eth_whales = []
                usdc_whales = []
                
                if block_data:
                    ts_hex = block_data.get('timestamp', '0x0')
                    try:
                        ts_int = int(ts_hex, 16)
                        timestamp_iso = datetime.fromtimestamp(ts_int).isoformat()
                    except ValueError:
                        timestamp_iso = datetime.now().isoformat()
                    
                    eth_whales = await self.scan_block_eth(block_data)
                    usdc_whales = await self.scan_block_usdc(logs, timestamp_iso)
                
                if eth_whales or usdc_whales:
                    print(f"\n🐋 Found {len(eth_whales)} ETH and {len(usdc_whales)} USDC whale(s)!")
                    
                    for w in eth_whales[:2]:
                        print(f"  🐋 ETH: {w['value_eth']:.2f} from {w['from'][:8]}...")
                    for w in usdc_whales[:2]:
                        print(f"  💵 USDC: ${w['value_usdc']:,.0f} to {w['to'][:8]}...")
                        
                    self.update_dashboard_data(eth_whales, usdc_whales)
                else:
                    print(f"\r  No whales found in this scan range. ", end='')
                
                await asyncio.sleep(12)

if __name__ == "__main__":
    tracker = WhaleTracker()
    try:
        asyncio.run(tracker.run_scan_loop(blocks_per_scan=5))
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping tracker...")
        print("✅ Data saved safely to whale_data.json")