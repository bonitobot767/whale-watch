#!/usr/bin/env python3
"""
Whale Watch Configuration
Central configuration for all Whale Watch features.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import os

@dataclass
class WhaleWatchConfig:
    """Master configuration for Whale Watch system."""
    
    # Core Tracking
    tracking_enabled: bool = True
    whale_threshold_eth: float = 100
    whale_threshold_usdc: float = 100_000
    scan_interval_seconds: int = 12
    blocks_per_scan: int = 5
    
    # Price Impact Analyzer
    price_impact_enabled: bool = True
    price_check_intervals: list = None  # [60, 300, 3600] in seconds
    price_history_hours: int = 24
    min_volume_surge_pct: float = 5.0
    correlation_window_seconds: int = 3600
    
    # Whale Profiler
    profiler_enabled: bool = True
    balance_threshold_eth: float = 10
    min_transactions_for_profile: int = 5
    profile_cache_duration_hours: int = 24
    
    # Alert System
    alert_system_enabled: bool = True
    critical_eth_threshold: float = 500
    critical_usdc_threshold: float = 500_000
    high_eth_threshold: float = 250
    high_usdc_threshold: float = 250_000
    min_alert_confidence: float = 0.6
    
    # Webhooks
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    webhook_timeout_seconds: int = 30
    webhook_retry_attempts: int = 3
    webhook_signature_secret: Optional[str] = None
    
    # Moltbook Integration
    moltbook_enabled: bool = False
    moltbook_api_key: Optional[str] = None
    moltbook_post_critical_only: bool = True
    
    # Data Persistence
    data_file: str = "whale_data.json"
    alert_file: str = "whale_alerts.jsonl"
    profile_cache_file: str = "whale_profiles.json"
    
    # API Keys
    etherscan_api_key: Optional[str] = None
    
    # Features
    enable_price_correlation: bool = True
    enable_pattern_detection: bool = True
    enable_whale_profiling: bool = True
    enable_real_time_alerts: bool = True
    
    # Performance
    max_parallel_api_calls: int = 5
    api_rate_limit_per_minute: int = 100
    cache_max_size: int = 10_000

    def __post_init__(self):
        if self.price_check_intervals is None:
            self.price_check_intervals = [60, 300, 3600]

    @classmethod
    def from_env(cls) -> 'WhaleWatchConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Read from .env if present
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    key, value = line.split("=", 1)
                    os.environ[key] = value
        
        # Map env vars to config
        env_mappings = {
            "WHALE_WATCH_TRACKING_ENABLED": ("tracking_enabled", "bool"),
            "WHALE_WATCH_WHALE_THRESHOLD_ETH": ("whale_threshold_eth", "float"),
            "WHALE_WATCH_PRICE_IMPACT_ENABLED": ("price_impact_enabled", "bool"),
            "WHALE_WATCH_PROFILER_ENABLED": ("profiler_enabled", "bool"),
            "WHALE_WATCH_ALERT_SYSTEM_ENABLED": ("alert_system_enabled", "bool"),
            "WHALE_WATCH_WEBHOOK_URL": ("webhook_url", "str"),
            "WHALE_WATCH_MOLTBOOK_API_KEY": ("moltbook_api_key", "str"),
            "WHALE_WATCH_MOLTBOOK_ENABLED": ("moltbook_enabled", "bool"),
            "ETHERSCAN_API_KEY": ("etherscan_api_key", "str"),
        }
        
        for env_key, (attr_name, type_name) in env_mappings.items():
            value = os.getenv(env_key)
            if value:
                if type_name == "bool":
                    setattr(config, attr_name, value.lower() in ["true", "1", "yes"])
                elif type_name == "float":
                    setattr(config, attr_name, float(value))
                elif type_name == "int":
                    setattr(config, attr_name, int(value))
                else:
                    setattr(config, attr_name, value)
        
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "core": {
                "tracking_enabled": self.tracking_enabled,
                "whale_threshold_eth": self.whale_threshold_eth,
                "whale_threshold_usdc": self.whale_threshold_usdc,
                "scan_interval_seconds": self.scan_interval_seconds,
            },
            "price_impact": {
                "enabled": self.price_impact_enabled,
                "check_intervals": self.price_check_intervals,
                "history_hours": self.price_history_hours,
                "min_volume_surge_pct": self.min_volume_surge_pct,
            },
            "profiler": {
                "enabled": self.profiler_enabled,
                "balance_threshold_eth": self.balance_threshold_eth,
                "cache_duration_hours": self.profile_cache_duration_hours,
            },
            "alerts": {
                "enabled": self.alert_system_enabled,
                "critical_eth_threshold": self.critical_eth_threshold,
                "critical_usdc_threshold": self.critical_usdc_threshold,
                "min_confidence": self.min_alert_confidence,
            },
            "webhooks": {
                "enabled": self.webhook_enabled,
                "url": self.webhook_url,
                "timeout_seconds": self.webhook_timeout_seconds,
                "retry_attempts": self.webhook_retry_attempts,
            },
            "moltbook": {
                "enabled": self.moltbook_enabled,
                "post_critical_only": self.moltbook_post_critical_only,
            },
            "features": {
                "price_correlation": self.enable_price_correlation,
                "pattern_detection": self.enable_pattern_detection,
                "whale_profiling": self.enable_whale_profiling,
                "real_time_alerts": self.enable_real_time_alerts,
            }
        }

    def save_to_file(self, filepath: str = "whale_watch_config.json") -> bool:
        """Save configuration to file."""
        try:
            with open(filepath, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            print(f"✅ Config saved to {filepath}")
            return True
        except Exception as e:
            print(f"❌ Config save error: {e}")
            return False


# Default configuration singleton
_default_config: Optional[WhaleWatchConfig] = None

def get_config() -> WhaleWatchConfig:
    """Get or create default configuration."""
    global _default_config
    if _default_config is None:
        _default_config = WhaleWatchConfig.from_env()
    return _default_config


if __name__ == "__main__":
    config = get_config()
    print("\n📋 Whale Watch Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    config.save_to_file()
