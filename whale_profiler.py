#!/usr/bin/env python3
"""
Whale Profiler for Whale Watch
Identifies whale address types using on-chain heuristics.
Classifies: Exchange, Institutional, Private Whale, DeFi Protocol, Unknown
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

class WhaleType(Enum):
    EXCHANGE_COLD = "exchange_cold"
    EXCHANGE_HOT = "exchange_hot"
    INSTITUTIONAL = "institutional"
    PRIVATE_WHALE = "private_whale"
    DEFI_PROTOCOL = "defi_protocol"
    SMART_CONTRACT = "smart_contract"
    UNKNOWN = "unknown"

@dataclass
class AddressProfile:
    """On-chain profile of a whale address."""
    address: str
    whale_type: WhaleType
    confidence: float  # 0-1
    balance_eth: float
    total_transactions: int
    unique_counterparties: int
    avg_tx_value: float
    activity_pattern: str  # "accumulating", "dumping", "active_trading", "dormant"
    is_contract: bool
    known_entity: Optional[str]  # Name if known (Binance, Kraken, etc.)
    last_activity: str  # ISO timestamp
    risk_score: float  # 0-100, higher = more volatile
    labels: List[str]
    profile_date: str

# Known exchange addresses (subset - in production, use comprehensive lists)
KNOWN_EXCHANGES = {
    "0x3675da73ede475b0ae3e136726cb3c89d6038f41": "Binance 10",
    "0x28c6c06298d161e1adf123044e835ffac5fdebc8": "Kraken 11",
    "0xa7f1e9a266cd81991c07f81d7c0d9c2999f24a24": "Kraken 11 (alt)",
    "0xda9dfa130df4de4673b89022ee50aa2228f7daaa": "Exchange (generic)",
    "0x742d35cc6634C0532925a3b844Bc9e7595f5bEb3": "Kraken 8",
    "0x2e7dc97b0b55e77e77c90bcd0f7b13b3b9e7c822": "Kraken (alt)",
    "0x5e57b7a6c4aacb48c3d43a7fa1c0d23cc7a14eda": "Kraken Hot Wallet",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Coinbase Hot Wallet",
    "0x503828976d22510aad0201f7e4b2d7daf2de3992": "Coinbase Hot Wallet 2",
    "0xa910f92acdaf488fa6ef02174b80d0480194a969": "Binance Hot",
    "0xdac17f958d2ee523a2206206994597c13d831ec7": "Tether (USDT)",
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
}

KNOWN_PROTOCOLS = {
    "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch Router",
    "0x68b3465833fb72b70c6c7f6cad38ab5d38082ba0": "Uniswap v2/3 Router",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap v2 Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap Swap Router",
    "0x6b175474e89094c44da98b954eedeac495271d0f": "Dai Stablecoin",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "Wrapped BTC",
}

class WhaleProfiler:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.session = None
        self.profile_cache: Dict[str, AddressProfile] = {}
        self.address_labels: Dict[str, str] = {**KNOWN_EXCHANGES, **KNOWN_PROTOCOLS}

    @staticmethod
    def _default_config() -> Dict:
        return {
            "balance_threshold_eth": 10,
            "min_transactions": 5,
            "exchange_detection_threshold": 0.8,
            "cache_duration_hours": 24,
            "etherscan_api_key": "",
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_address_balance_and_txs(self, address: str) -> Tuple[float, int]:
        """Get ETH balance and transaction count for address."""
        if not self.session:
            return 0.0, 0
        
        base_url = "https://api.etherscan.io/api"
        api_key = self.config.get("etherscan_api_key", "")
        
        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": api_key
        }
        
        try:
            async with self.session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        balance_wei = float(data.get("result", 0))
                        balance_eth = balance_wei / 10**18
                        
                        # Get tx count
                        params["action"] = "txlistinternal"
                        async with self.session.get(base_url, params=params) as tx_response:
                            if tx_response.status == 200:
                                tx_data = await tx_response.json()
                                if tx_data.get("status") == "1":
                                    tx_count = len(tx_data.get("result", []))
                                    return balance_eth, tx_count
                        
                        return balance_eth, 0
        except Exception as e:
            print(f"⚠️ Etherscan API error: {e}")
        
        return 0.0, 0

    def _is_contract_address(self, address: str) -> bool:
        """Heuristic: check if address looks like a contract."""
        # Simple check: contracts typically have specific patterns
        # In production, use eth_getCode API call
        addr_lower = address.lower()
        
        # Check against known contracts
        if addr_lower in [k.lower() for k in KNOWN_PROTOCOLS.keys()]:
            return True
        
        # Check hash pattern (simple heuristic)
        # Most contracts start with specific patterns
        return any(addr_lower.startswith(prefix) 
                  for prefix in ["0x1", "0x2", "0x3", "0x4", "0x5", "0x6", "0x7", "0x8"])

    def _analyze_transaction_pattern(self, tx_count: int, balance: float, 
                                     unique_counterparties: int) -> Tuple[str, float]:
        """Analyze transaction history to detect activity pattern."""
        if balance == 0:
            return "dormant", 0.0
        
        if tx_count < self.config["min_transactions"]:
            return "dormant", 0.2
        
        # Ratio analysis
        tx_ratio = tx_count / max(unique_counterparties, 1)
        
        if tx_ratio > 5:  # Few counterparties, many transactions
            return "active_trading", 0.7
        elif unique_counterparties > tx_count * 0.8:  # Many unique counterparties
            return "accumulating", 0.6  # Likely receiving from many sources
        else:
            return "dumping", 0.7  # Sending to many addresses

    def _calculate_risk_score(self, whale_type: WhaleType, balance: float, 
                             tx_pattern: str, tx_count: int) -> float:
        """Calculate risk score (0-100) for volatility."""
        # Base scores by type
        type_risk = {
            WhaleType.EXCHANGE_COLD: 20,  # Very stable
            WhaleType.EXCHANGE_HOT: 40,   # Medium volatility
            WhaleType.INSTITUTIONAL: 25,  # Stable
            WhaleType.PRIVATE_WHALE: 70,  # High volatility
            WhaleType.DEFI_PROTOCOL: 30,  # Medium
            WhaleType.SMART_CONTRACT: 35, # Medium
            WhaleType.UNKNOWN: 50,        # Uncertain
        }
        
        base = type_risk.get(whale_type, 50)
        
        # Adjust based on activity
        pattern_adjust = {
            "dormant": -15,
            "accumulating": 10,
            "active_trading": 15,
            "dumping": 25,
        }
        
        adjusted = base + pattern_adjust.get(tx_pattern, 0)
        
        # Adjust for balance size (whales with huge balance = more impact)
        size_factor = min(balance / 1000, 20)  # Max +20 for very large whales
        adjusted += size_factor
        
        return max(0, min(100, adjusted))

    def _detect_whale_type(self, address: str, balance: float, is_contract: bool,
                          unique_counterparties: int, tx_count: int) -> Tuple[WhaleType, float]:
        """Detect whale type using heuristics."""
        address_lower = address.lower()
        
        # Check known addresses first
        if address_lower in [k.lower() for k in KNOWN_EXCHANGES.keys()]:
            return WhaleType.EXCHANGE_COLD, 0.95
        
        if address_lower in [k.lower() for k in KNOWN_PROTOCOLS.keys()]:
            return WhaleType.DEFI_PROTOCOL, 0.9
        
        # Check if it's a contract
        if is_contract:
            return WhaleType.SMART_CONTRACT, 0.7
        
        # Heuristic: Exchange hot wallets have high transaction throughput
        if tx_count > 1000 and unique_counterparties > 100:
            return WhaleType.EXCHANGE_HOT, 0.75
        
        # Institutional patterns: large balance, selective counterparties
        if balance > 5000 and unique_counterparties < 20 and tx_count > 50:
            return WhaleType.INSTITUTIONAL, 0.7
        
        # Private whale: large balance, varied activity
        if balance > 100:
            return WhaleType.PRIVATE_WHALE, 0.8
        
        return WhaleType.UNKNOWN, 0.3

    async def profile_address(self, address: str) -> Optional[AddressProfile]:
        """Generate comprehensive profile for an address."""
        try:
            # Check cache
            cache_key = address.lower()
            if cache_key in self.profile_cache:
                cached = self.profile_cache[cache_key]
                cache_age = (datetime.fromisoformat(cached.profile_date) - datetime.utcnow()).total_seconds()
                if abs(cache_age) < self.config["cache_duration_hours"] * 3600:
                    return cached

            # Get balance and tx count
            balance, tx_count = await self.get_address_balance_and_txs(address)
            
            if balance < self.config["balance_threshold_eth"]:
                return None  # Not a whale

            # Mock unique counterparties (in production, parse all transactions)
            unique_counterparties = min(max(tx_count // 3, 1), 500)
            
            # Analyze pattern
            pattern, pattern_confidence = self._analyze_transaction_pattern(
                tx_count, balance, unique_counterparties
            )
            
            # Detect type
            is_contract = self._is_contract_address(address)
            whale_type, type_confidence = self._detect_whale_type(
                address, balance, is_contract, unique_counterparties, tx_count
            )
            
            # Calculate scores
            avg_tx_value = balance / max(tx_count, 1)
            risk_score = self._calculate_risk_score(whale_type, balance, pattern, tx_count)
            
            # Generate labels
            labels = [whale_type.value, pattern]
            if is_contract:
                labels.append("contract")
            if address_lower := address.lower() in [k.lower() for k in self.address_labels.keys()]:
                labels.append("known_entity")
            
            profile = AddressProfile(
                address=address,
                whale_type=whale_type,
                confidence=min(type_confidence + pattern_confidence) / 2,
                balance_eth=balance,
                total_transactions=tx_count,
                unique_counterparties=unique_counterparties,
                avg_tx_value=avg_tx_value,
                activity_pattern=pattern,
                is_contract=is_contract,
                known_entity=self.address_labels.get(address.lower()),
                last_activity=datetime.utcnow().isoformat(),
                risk_score=risk_score,
                labels=labels,
                profile_date=datetime.utcnow().isoformat()
            )
            
            self.profile_cache[cache_key] = profile
            return profile

        except Exception as e:
            print(f"⚠️ Profiling error for {address}: {e}")
            return None

    def compare_addresses(self, addresses: List[str]) -> Dict[str, Any]:
        """Compare multiple whale addresses."""
        return {
            "comparison": "Not yet implemented - future feature",
            "addresses_count": len(addresses),
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_profile_summary(self, address: str, profile: AddressProfile) -> Dict[str, Any]:
        """Generate human-readable summary of a whale profile."""
        return {
            "address": address,
            "whale_type": profile.whale_type.value,
            "confidence_pct": f"{profile.confidence * 100:.1f}%",
            "balance_eth": f"{profile.balance_eth:.2f} ETH",
            "balance_usd": f"${profile.balance_eth * 2500:.0f}",  # Mock price
            "transaction_count": profile.total_transactions,
            "unique_interactions": profile.unique_counterparties,
            "activity": profile.activity_pattern,
            "risk_level": (
                "🟢 Low" if profile.risk_score < 30 else
                "🟡 Medium" if profile.risk_score < 60 else
                "🔴 High"
            ),
            "risk_score": f"{profile.risk_score:.1f}/100",
            "is_contract": profile.is_contract,
            "known_as": profile.known_entity or "Unknown entity",
            "labels": ", ".join(profile.labels),
            "profile_age_hours": round((datetime.utcnow() - datetime.fromisoformat(profile.profile_date)).total_seconds() / 3600, 1)
        }


if __name__ == "__main__":
    # Example usage
    async def demo():
        config = {"etherscan_api_key": ""}  # Use real key in production
        profiler = WhaleProfiler(config)
        async with profiler:
            # Profile example addresses
            test_addresses = [
                "0x3675da73ede475b0ae3e136726cb3c89d6038f41",  # Known exchange
                "0x0000000000000000000000000000000000000001",  # Regular address
            ]
            
            for addr in test_addresses:
                profile = await profiler.profile_address(addr)
                if profile:
                    summary = profiler.get_profile_summary(addr, profile)
                    print(f"\n📊 Profile for {addr[:10]}...")
                    print(json.dumps(summary, indent=2, default=str))

    asyncio.run(demo())
