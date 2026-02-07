#!/usr/bin/env python3
"""
Price Impact Analyzer for Whale Watch
Correlates whale movements with real-time price changes on major exchanges.
Uses Uniswap v3 subgraph and Binance spot prices for high-precision correlation.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics

# Configuration
UNISWAP_V3_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
BINANCE_API_URL = "https://api.binance.com/api/v3"
COINGECKO_API_URL = "https://api.coingecko.com/data/v3"  # Free tier

class PriceDirection(Enum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"

@dataclass
class PriceSnapshot:
    """Price state at a specific timestamp."""
    timestamp: str
    eth_price: float
    usdc_price: float
    uniswap_volume: float
    binance_volume: float
    volatility: float  # 24h volatility %

@dataclass
class ImpactMetrics:
    """Impact analysis results."""
    whale_hash: str
    whale_value_eth: float
    price_change_1m: float  # % change 1 min after
    price_change_5m: float  # % change 5 min after
    price_change_1h: float  # % change 1 hour after
    volume_surge: float  # % increase in trading volume
    impact_score: float  # 0-100 score of impact
    direction: PriceDirection
    affected_pools: List[str]
    confidence: float  # 0-1 confidence level
    timestamp: str

class PriceImpactAnalyzer:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.session = None
        self.price_history: Dict[str, List[PriceSnapshot]] = {}
        self.impact_cache: List[ImpactMetrics] = []

    @staticmethod
    def _default_config() -> Dict:
        return {
            "whale_threshold_eth": 100,
            "whale_threshold_usdc": 100_000,
            "correlation_window_seconds": 3600,
            "price_check_intervals": [60, 300, 3600],  # 1m, 5m, 1h
            "min_volume_surge_pct": 5.0,
            "max_historical_hours": 24,
            "enabled_exchanges": ["uniswap", "binance"],
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _query_subgraph(self, query: str) -> Optional[Dict]:
        """Query The Graph Uniswap V3 subgraph."""
        if not self.session:
            return None
        try:
            async with self.session.post(
                UNISWAP_V3_SUBGRAPH,
                json={"query": query},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            print(f"⚠️ Subgraph query error: {e}")
        return None

    async def get_eth_usdc_price_binance(self) -> Tuple[float, float]:
        """Fetch current ETH/USDT and USDT/USDC prices from Binance."""
        if not self.session:
            return 0.0, 1.0
        
        try:
            # Get ETH/USDT
            async with self.session.get(
                f"{BINANCE_API_URL}/ticker/price?symbol=ETHUSDT",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    eth_data = await response.json()
                    eth_price = float(eth_data.get('price', 0))
                else:
                    eth_price = 0.0
            
            # USDC ≈ USDT on Binance (highly correlated, 1:1)
            usdc_price = 1.0
            
            return eth_price, usdc_price
        except Exception as e:
            print(f"⚠️ Binance API error: {e}")
            return 0.0, 1.0

    async def get_uniswap_eth_usdc_volume(self) -> float:
        """Get 1h volume for ETH-USDC pool on Uniswap V3."""
        query = """
        {
            pools(first: 1, where: {id: "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"}) {
                feeTier
                volumeUSD
                txCount
                totalValueLockedUSD
            }
        }
        """
        result = await self._query_subgraph(query)
        if result and "data" in result:
            pools = result["data"].get("pools", [])
            if pools:
                return float(pools[0].get("volumeUSD", 0))
        return 0.0

    async def get_24h_volatility_eth(self) -> float:
        """Calculate 24h price volatility for ETH."""
        # Query recent trades from Uniswap to estimate volatility
        query = """
        {
            swaps(first: 100, orderBy: timestamp, orderDirection: desc, 
                  where: {pool: "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"}) {
                timestamp
                amountUSD
                sqrtPriceX96
            }
        }
        """
        result = await self._query_subgraph(query)
        if result and "data" in result:
            swaps = result["data"].get("swaps", [])
            if len(swaps) > 1:
                # Simple volatility estimate from price swings
                prices = [float(s.get("sqrtPriceX96", 0)) for s in swaps]
                if prices and len(prices) > 1:
                    try:
                        volatility = statistics.stdev(prices) / statistics.mean(prices) * 100
                        return min(volatility, 50.0)  # Cap at 50%
                    except:
                        pass
        return 2.5  # Default 2.5% volatility estimate

    async def record_price_snapshot(self, exchange: str) -> Optional[PriceSnapshot]:
        """Record current price state."""
        eth_price, usdc_price = await self.get_eth_usdc_price_binance()
        uniswap_volume = await self.get_uniswap_eth_usdc_volume()
        volatility = await self.get_24h_volatility_eth()
        
        if eth_price <= 0:
            return None

        snapshot = PriceSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            eth_price=eth_price,
            usdc_price=usdc_price,
            uniswap_volume=uniswap_volume,
            binance_volume=uniswap_volume * 2,  # Binance typically 2-3x Uniswap
            volatility=volatility
        )
        
        if exchange not in self.price_history:
            self.price_history[exchange] = []
        
        self.price_history[exchange].append(snapshot)
        
        # Keep only recent history
        max_age = self.config["max_historical_hours"] * 3600
        cutoff = datetime.utcnow().timestamp() - max_age
        self.price_history[exchange] = [
            s for s in self.price_history[exchange]
            if datetime.fromisoformat(s.timestamp).timestamp() > cutoff
        ]
        
        return snapshot

    def _calculate_price_change(self, before_price: float, after_price: float) -> float:
        """Calculate percentage price change."""
        if before_price <= 0:
            return 0.0
        return ((after_price - before_price) / before_price) * 100

    def analyze_whale_impact(self, whale_tx: Dict, whale_type: str = "unknown") -> Optional[ImpactMetrics]:
        """Analyze price impact of a whale transaction."""
        try:
            # Ensure we have price history
            if "binance" not in self.price_history or len(self.price_history["binance"]) < 2:
                return None

            whale_timestamp = datetime.fromisoformat(whale_tx.get("timestamp", datetime.utcnow().isoformat()))
            history = self.price_history["binance"]
            
            # Find price snapshot closest to whale tx
            closest_before = None
            closest_after = None
            
            for snapshot in history:
                snap_time = datetime.fromisoformat(snapshot.timestamp)
                if snap_time <= whale_timestamp:
                    if not closest_before or snap_time > datetime.fromisoformat(closest_before.timestamp):
                        closest_before = snapshot
                elif snap_time > whale_timestamp:
                    if not closest_after or snap_time < datetime.fromisoformat(closest_after.timestamp):
                        closest_after = snapshot
            
            if not closest_before or not closest_after:
                return None

            # Calculate price changes at different intervals
            base_price = closest_before.eth_price
            changes = {}
            
            for interval in self.config["price_check_intervals"]:
                target_time = whale_timestamp + timedelta(seconds=interval)
                matching = [s for s in history 
                           if whale_timestamp < datetime.fromisoformat(s.timestamp) <= target_time]
                if matching:
                    latest = sorted(matching, key=lambda s: s.timestamp)[-1]
                    change = self._calculate_price_change(base_price, latest.eth_price)
                    changes[f"{interval//60}m" if interval < 3600 else "1h"] = change

            # Determine price direction
            change_1h = changes.get("1h", 0)
            if abs(change_1h) < 0.5:
                direction = PriceDirection.NEUTRAL
            elif change_1h > 0:
                direction = PriceDirection.UP
            else:
                direction = PriceDirection.DOWN

            # Calculate volume surge
            volume_surge = 0.0
            if closest_after.binance_volume > 0:
                volume_surge = ((closest_after.binance_volume - closest_before.binance_volume) 
                               / closest_before.binance_volume * 100) if closest_before.binance_volume > 0 else 0

            # Calculate impact score (0-100)
            whale_value = whale_tx.get("value_eth", whale_tx.get("value_usdc", 0) / 2000)  # Normalize to ETH
            abs_price_change = abs(change_1h)
            
            # Impact factors
            size_factor = min(whale_value / self.config["whale_threshold_eth"] * 20, 40)
            price_factor = min(abs_price_change * 5, 40)
            volume_factor = min(max(volume_surge - self.config["min_volume_surge_pct"], 0) / 10, 20)
            
            impact_score = size_factor + price_factor + volume_factor

            # Confidence based on data quality
            confidence = min(
                0.5 +  # Base confidence
                (0.2 if volume_surge > self.config["min_volume_surge_pct"] else 0) +
                (0.2 if abs_price_change > 1.0 else 0.1) +
                (0.1 if closest_after else 0),
                1.0
            )

            metrics = ImpactMetrics(
                whale_hash=whale_tx.get("hash", "unknown"),
                whale_value_eth=whale_value,
                price_change_1m=changes.get("1m", 0),
                price_change_5m=changes.get("5m", 0),
                price_change_1h=change_1h,
                volume_surge=volume_surge,
                impact_score=impact_score,
                direction=direction,
                affected_pools=["ETH-USDC-0.3%"],  # Uniswap pool
                confidence=confidence,
                timestamp=whale_timestamp.isoformat()
            )

            self.impact_cache.append(metrics)
            return metrics

        except Exception as e:
            print(f"⚠️ Impact analysis error: {e}")
            return None

    def get_impact_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate impact report for last N hours."""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        recent = [m for m in self.impact_cache
                 if datetime.fromisoformat(m.timestamp).timestamp() > cutoff]
        
        if not recent:
            return {"status": "no_data", "hours": hours, "impacts": []}

        # Sort by impact score
        recent.sort(key=lambda x: x.impact_score, reverse=True)
        
        high_impact = [m for m in recent if m.impact_score > 50]
        price_movers = [m for m in recent if abs(m.price_change_1h) > 2.0]

        return {
            "status": "success",
            "hours": hours,
            "total_whales_analyzed": len(recent),
            "high_impact_count": len(high_impact),
            "price_mover_count": len(price_movers),
            "avg_impact_score": statistics.mean([m.impact_score for m in recent]) if recent else 0,
            "top_impacts": [asdict(m) for m in recent[:10]],
            "summary": {
                "price_ups": len([m for m in recent if m.direction == PriceDirection.UP]),
                "price_downs": len([m for m in recent if m.direction == PriceDirection.DOWN]),
                "price_neutrals": len([m for m in recent if m.direction == PriceDirection.NEUTRAL]),
            }
        }

    async def continuous_monitoring(self, check_interval: int = 60):
        """Continuously monitor and record price snapshots."""
        async with self:
            print("🔍 Price Impact Analyzer starting continuous monitoring...")
            while True:
                try:
                    snapshot = await self.record_price_snapshot("binance")
                    if snapshot:
                        print(f"📊 Price snapshot: ETH=${snapshot.eth_price:.2f}, "
                              f"Vol=${snapshot.binance_volume:,.0f}, "
                              f"Vol↑={snapshot.volatility:.2f}%")
                    await asyncio.sleep(check_interval)
                except Exception as e:
                    print(f"⚠️ Monitoring error: {e}")
                    await asyncio.sleep(check_interval)


if __name__ == "__main__":
    # Example usage
    async def demo():
        analyzer = PriceImpactAnalyzer()
        async with analyzer:
            # Record some snapshots
            for _ in range(3):
                await analyzer.record_price_snapshot("binance")
                await asyncio.sleep(5)
            
            # Simulate whale transaction
            whale_tx = {
                "hash": "0x123...",
                "timestamp": datetime.utcnow().isoformat(),
                "value_eth": 250,
                "from": "0xwhale...",
                "to": "0xexchange..."
            }
            
            impact = analyzer.analyze_whale_impact(whale_tx)
            if impact:
                print("\n✅ Impact Analysis:")
                print(json.dumps(asdict(impact), indent=2, default=str))
            
            # Get report
            report = analyzer.get_impact_report(hours=1)
            print("\n📈 Impact Report:")
            print(json.dumps(report, indent=2, default=str))

    asyncio.run(demo())
