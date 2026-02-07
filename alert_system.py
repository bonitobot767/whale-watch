#!/usr/bin/env python3
"""
Alert System for Whale Watch
Generates actionable JSON alerts for critical whale movements.
Supports webhooks for autonomous trading integration and Moltbook posting.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import hmac

class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class AlertType(Enum):
    CRITICAL_MOVEMENT = "critical_movement"  # >500 ETH or >$500K
    PATTERN_SHIFT = "pattern_shift"  # Accumulation vs dump detected
    EXCHANGE_ACTIVITY = "exchange_activity"  # Exchange detected
    LIQUIDITY_DRAIN = "liquidity_drain"  # Sudden withdrawal from pool
    ACCUMULATION = "accumulation"  # Whale buying pattern
    DUMPING = "dumping"  # Whale selling pattern
    WHALE_WAKE_UP = "whale_wake_up"  # Dormant whale becomes active

@dataclass
class Alert:
    """Structured alert event."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    timestamp: str
    whale_address: str
    whale_profile: Optional[Dict[str, str]]  # From WhaleProfiler
    transaction_hash: str
    value_eth: float
    value_usd: float
    direction: str  # "inbound" or "outbound"
    from_address: str
    to_address: str
    affected_pools: List[str]
    price_impact: Optional[Dict[str, float]]  # From PriceImpactAnalyzer
    confidence: float  # 0-1
    action_recommended: str
    metadata: Dict[str, Any]
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), default=str)
    
    def to_webhook_payload(self) -> Dict[str, Any]:
        """Format for webhook delivery."""
        return {
            "event": "whale_alert",
            "id": self.alert_id,
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "whale": {
                "address": self.whale_address,
                "profile": self.whale_profile,
            },
            "transaction": {
                "hash": self.transaction_hash,
                "value_eth": self.value_eth,
                "value_usd": self.value_usd,
                "direction": self.direction,
                "from": self.from_address,
                "to": self.to_address,
            },
            "market_impact": {
                "affected_pools": self.affected_pools,
                "price_impact": self.price_impact,
            },
            "confidence": self.confidence,
            "recommended_action": self.action_recommended,
            "metadata": self.metadata
        }

@dataclass
class AlertConfig:
    """Configuration for alert generation."""
    # Thresholds
    critical_eth_threshold: float = 500
    critical_usdc_threshold: float = 500_000
    high_eth_threshold: float = 250
    high_usdc_threshold: float = 250_000
    
    # Detection
    enable_accumulation_alerts: bool = True
    enable_exchange_alerts: bool = True
    enable_price_impact_alerts: bool = True
    min_confidence_for_alert: float = 0.6
    
    # Webhook
    webhook_url: Optional[str] = None
    webhook_timeout_seconds: int = 30
    webhook_retry_attempts: int = 3
    webhook_signature_secret: Optional[str] = None
    
    # Storage
    alert_history_max_size: int = 10_000
    alert_persistence_file: str = "whale_alerts.jsonl"

class AlertSystem:
    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig()
        self.session = None
        self.alert_history: List[Alert] = []
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.moltbook_integration = False

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback to be called when alerts are generated."""
        self.alert_callbacks.append(callback)

    def _generate_alert_id(self, whale_address: str, tx_hash: str) -> str:
        """Generate unique alert ID."""
        content = f"{whale_address}{tx_hash}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _classify_severity(self, value_eth: float, value_usdc: float, 
                          confidence: float, impact_score: Optional[float] = None) -> AlertSeverity:
        """Classify alert severity based on value and confidence."""
        # Convert to ETH equivalent
        eth_equivalent = value_eth + (value_usdc / 2500)  # Mock price
        
        # Severity based on value
        if eth_equivalent >= self.config.critical_eth_threshold and confidence > 0.8:
            return AlertSeverity.CRITICAL
        elif eth_equivalent >= self.config.high_eth_threshold and confidence > 0.7:
            return AlertSeverity.HIGH
        elif confidence >= 0.8:
            return AlertSeverity.HIGH
        elif confidence >= 0.7:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def _recommend_action(self, alert_type: AlertType, severity: AlertSeverity, 
                         whale_profile: Optional[Dict]) -> str:
        """Generate action recommendation for trading bots."""
        if severity == AlertSeverity.CRITICAL:
            if alert_type == AlertType.DUMPING:
                return "CONSIDER_SHORT | REDUCE_LONG_POSITIONS | SET_SELL_ORDERS"
            elif alert_type == AlertType.ACCUMULATION:
                return "CONSIDER_LONG | INCREASE_BUY_ORDERS | MONITOR_CLOSELY"
            else:
                return "PREPARE_FOR_VOLATILITY | TIGHTEN_STOPS | REDUCE_LEVERAGE"
        elif severity == AlertSeverity.HIGH:
            if alert_type == AlertType.DUMPING:
                return "MONITOR_SELLING | BE_READY_TO_SELL"
            elif alert_type == AlertType.ACCUMULATION:
                return "MONITOR_BUYING | TRACK_ENTRY_POINTS"
            else:
                return "INCREASE_MONITORING | PREPARE_FOR_MOVEMENT"
        else:
            return "INFORMATIONAL | NO_IMMEDIATE_ACTION"

    async def generate_alert(self, whale_tx: Dict, whale_profile: Optional[Dict] = None,
                            price_impact: Optional[Dict] = None,
                            whale_type: Optional[str] = None,
                            activity_pattern: Optional[str] = None) -> Optional[Alert]:
        """Generate alert from whale transaction."""
        try:
            value_eth = whale_tx.get("value_eth", 0)
            value_usdc = whale_tx.get("value_usdc", 0)
            confidence = price_impact.get("confidence", 0.5) if price_impact else 0.5
            
            # Skip low-confidence alerts
            if confidence < self.config.min_confidence_for_alert:
                return None

            # Determine alert type
            alert_type = AlertType.CRITICAL_MOVEMENT
            
            if whale_type == "exchange_cold" or whale_type == "exchange_hot":
                if self.config.enable_exchange_alerts:
                    alert_type = AlertType.EXCHANGE_ACTIVITY
            elif activity_pattern == "dumping":
                alert_type = AlertType.DUMPING
            elif activity_pattern == "accumulating":
                alert_type = AlertType.ACCUMULATION
            
            # Check if meeting thresholds for alerts
            eth_threshold = (self.config.critical_eth_threshold 
                           if alert_type == AlertType.CRITICAL_MOVEMENT 
                           else self.config.high_eth_threshold)
            
            if value_eth < eth_threshold and value_usdc < self.config.critical_usdc_threshold:
                return None

            # Classify severity
            severity = self._classify_severity(value_eth, value_usdc, confidence,
                                             price_impact.get("impact_score") if price_impact else None)

            # Recommendation
            action = self._recommend_action(alert_type, severity, whale_profile)

            # Build metadata
            metadata = {
                "data_source": "whale_tracker",
                "version": "1.0",
                "enriched": whale_profile is not None,
            }
            
            if price_impact:
                metadata["price_change_1h_pct"] = price_impact.get("price_change_1h", 0)
                metadata["volume_surge_pct"] = price_impact.get("volume_surge", 0)

            alert = Alert(
                alert_id=self._generate_alert_id(
                    whale_tx.get("from", whale_tx.get("to", "unknown")),
                    whale_tx.get("hash", "")
                ),
                alert_type=alert_type,
                severity=severity,
                timestamp=whale_tx.get("timestamp", datetime.utcnow().isoformat()),
                whale_address=whale_tx.get("from", whale_tx.get("to", "unknown")),
                whale_profile=whale_profile,
                transaction_hash=whale_tx.get("hash", ""),
                value_eth=value_eth,
                value_usd=value_eth * 2500 + value_usdc,  # Mock conversion
                direction="outbound" if "from" in whale_tx else "inbound",
                from_address=whale_tx.get("from", ""),
                to_address=whale_tx.get("to", ""),
                affected_pools=price_impact.get("affected_pools", ["ETH-USDC"]) if price_impact else [],
                price_impact=price_impact,
                confidence=confidence,
                action_recommended=action,
                metadata=metadata
            )

            self.alert_history.append(alert)
            
            # Trim history
            if len(self.alert_history) > self.config.alert_history_max_size:
                self.alert_history = self.alert_history[-self.config.alert_history_max_size:]

            # Call callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"⚠️ Callback error: {e}")

            return alert

        except Exception as e:
            print(f"⚠️ Alert generation error: {e}")
            return None

    async def send_webhook(self, alert: Alert) -> bool:
        """Send alert to configured webhook."""
        if not self.config.webhook_url or not self.session:
            return False

        try:
            payload = alert.to_webhook_payload()
            headers = {"Content-Type": "application/json"}
            
            # Add signature if secret configured
            if self.config.webhook_signature_secret:
                body = json.dumps(payload)
                signature = hmac.new(
                    self.config.webhook_signature_secret.encode(),
                    body.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = signature

            for attempt in range(self.config.webhook_retry_attempts):
                try:
                    async with self.session.post(
                        self.config.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.webhook_timeout_seconds)
                    ) as response:
                        if response.status in [200, 201, 202]:
                            print(f"✅ Webhook delivered: {alert.alert_id}")
                            return True
                        elif response.status >= 500:
                            # Retry on server errors
                            if attempt < self.config.webhook_retry_attempts - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            print(f"⚠️ Webhook server error: {response.status}")
                            return False
                        else:
                            print(f"⚠️ Webhook error {response.status}: {await response.text()}")
                            return False
                except asyncio.TimeoutError:
                    if attempt < self.config.webhook_retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    print(f"⚠️ Webhook timeout on attempt {attempt + 1}")
                    return False

        except Exception as e:
            print(f"⚠️ Webhook error: {e}")
            return False

    async def post_to_moltbook(self, alert: Alert, moltbook_api_key: Optional[str] = None) -> bool:
        """Post alert to Moltbook for agent network visibility."""
        if not moltbook_api_key or not self.session:
            return False

        try:
            moltbook_url = "https://api.moltbook.io/v1/alerts"
            
            # Format for Moltbook
            moltbook_payload = {
                "source": "whale_watch",
                "alert_id": alert.alert_id,
                "type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": self._format_alert_message(alert),
                "data": alert.to_webhook_payload(),
                "timestamp": alert.timestamp,
                "tags": ["whale", alert.whale_profile.get("whale_type") if alert.whale_profile else "unknown"]
            }

            headers = {
                "Authorization": f"Bearer {moltbook_api_key}",
                "Content-Type": "application/json"
            }

            async with self.session.post(
                moltbook_url,
                json=moltbook_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status in [200, 201]:
                    print(f"🌐 Moltbook posted: {alert.alert_id}")
                    return True
                else:
                    print(f"⚠️ Moltbook error {response.status}")
                    return False

        except Exception as e:
            print(f"⚠️ Moltbook posting error: {e}")
            return False

    def _format_alert_message(self, alert: Alert) -> str:
        """Format human-readable alert message."""
        direction = "→" if alert.direction == "outbound" else "←"
        value_display = f"{alert.value_eth:.2f} ETH" if alert.value_eth > 0 else f"${alert.value_usd:,.0f}"
        
        whale_info = f"({alert.whale_profile.get('whale_type', 'unknown')})" if alert.whale_profile else ""
        
        return (
            f"🐋 {alert.severity.value.upper()} WHALE ALERT {whale_info}\n"
            f"{direction} {value_display}\n"
            f"Type: {alert.alert_type.value}\n"
            f"Action: {alert.action_recommended}"
        )

    def get_alerts_by_severity(self, severity: AlertSeverity, limit: int = 50) -> List[Alert]:
        """Get recent alerts by severity level."""
        alerts = [a for a in self.alert_history if a.severity == severity]
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_alerts_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of alerts in the last N hours."""
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [a for a in self.alert_history 
                 if datetime.fromisoformat(a.timestamp) > cutoff]
        
        severity_counts = {}
        type_counts = {}
        
        for alert in recent:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
            type_counts[alert.alert_type.value] = type_counts.get(alert.alert_type.value, 0) + 1
        
        return {
            "period_hours": hours,
            "total_alerts": len(recent),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "critical_count": severity_counts.get("critical", 0),
            "total_value_eth": sum(a.value_eth for a in recent),
            "total_value_usd": sum(a.value_usd for a in recent),
        }

    def export_alerts_jsonl(self, filepath: str) -> bool:
        """Export alert history to JSONL format."""
        try:
            with open(filepath, 'w') as f:
                for alert in self.alert_history:
                    f.write(alert.to_json() + '\n')
            print(f"✅ Exported {len(self.alert_history)} alerts to {filepath}")
            return True
        except Exception as e:
            print(f"⚠️ Export error: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    async def demo():
        config = AlertConfig(
            webhook_url="http://localhost:8000/webhook",  # Mock webhook
            alert_persistence_file="test_alerts.jsonl"
        )
        
        alert_system = AlertSystem(config)
        async with alert_system:
            # Simulate whale transaction
            whale_tx = {
                "hash": "0xabc123",
                "from": "0xwhaleaddress",
                "to": "0xexchange",
                "value_eth": 750,
                "value_usdc": 0,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Simulate enrichment data
            whale_profile = {
                "whale_type": "private_whale",
                "confidence": "0.85"
            }

            price_impact = {
                "confidence": 0.8,
                "price_change_1h": 2.5,
                "volume_surge": 45.3,
                "affected_pools": ["ETH-USDC-0.3%"],
                "impact_score": 65
            }

            # Generate alert
            alert = await alert_system.generate_alert(
                whale_tx,
                whale_profile=whale_profile,
                price_impact=price_impact,
                activity_pattern="dumping"
            )

            if alert:
                print("\n✅ Alert Generated:")
                print(json.dumps(alert.to_webhook_payload(), indent=2, default=str))
                
                print("\n📊 Alert Summary:")
                summary = alert_system.get_alerts_summary(hours=1)
                print(json.dumps(summary, indent=2))
                
                # Export
                alert_system.export_alerts_jsonl("test_alerts.jsonl")

    asyncio.run(demo())
