#!/usr/bin/env python3
"""
Enhanced Whale Watch API with Prediction Market Integration
"""

import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from pydantic import BaseModel
from typing import List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Whale Watch Prediction Market API",
    description="Real-time whale detection + autonomous USDC predictions",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base Sepolia config
BASE_SEPOLIA_RPC = "https://sepolia.base.org"
USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

# Load contract address from environment or file
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
if not CONTRACT_ADDRESS and os.path.exists(".contract_address"):
    with open(".contract_address", "r") as f:
        CONTRACT_ADDRESS = f.read().strip()

# Load contract ABI
CONTRACT_ABI = None
if os.path.exists("contract_abi.json"):
    with open("contract_abi.json", "r") as f:
        CONTRACT_ABI = json.load(f)

# Connect to Base Sepolia
w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC))

# Models
class PredictionRequest(BaseModel):
    whale_id: str
    prediction: str
    usdc_amount: int

class PredictionResponse(BaseModel):
    prediction_id: int
    tx_hash: str
    agent: str
    whale_id: str
    usdc_amount: int
    basescan_link: str

class PredictionStatus(BaseModel):
    prediction_id: int
    agent: str
    whale_id: str
    prediction: str
    usdc_staked: int
    timestamp: int
    settled: bool
    was_correct: Optional[bool]

# Endpoints (existing whale tracking)

@app.get("/api/health")
async def health():
    """System health check"""
    return {
        "status": "ok",
        "base_sepolia": w3.is_connected(),
        "contract_deployed": CONTRACT_ADDRESS is not None,
        "contract_address": CONTRACT_ADDRESS
    }

@app.get("/api/summary")
async def summary():
    """Get whale summary"""
    try:
        with open("whale_data.json", "r") as f:
            data = json.load(f)
            return {
                "eth_whales": len(data.get("eth_whales", [])),
                "usdc_whales": len(data.get("usdc_whales", [])),
                "total_eth_volume": sum(w.get("value_eth", 0) for w in data.get("eth_whales", [])),
                "system_status": "online"
            }
    except:
        return {"error": "whale_data.json not found"}

@app.get("/api/whales")
async def get_whales(hours: int = 24, limit: int = 50):
    """Get recent whale movements"""
    try:
        with open("whale_data.json", "r") as f:
            data = json.load(f)
            return {
                "eth_whales": data.get("eth_whales", [])[:limit],
                "usdc_whales": data.get("usdc_whales", [])[:limit]
            }
    except:
        return {"error": "whale_data.json not found"}

# NEW ENDPOINTS: Prediction Market

@app.post("/api/predict", response_model=PredictionResponse)
async def make_prediction(request: PredictionRequest, agent_address: str):
    """
    Agent submits a whale prediction
    
    Example:
    POST /api/predict?agent_address=0x...
    {
        "whale_id": "0xfccc611f...",
        "prediction": "will_pump_5_percent",
        "usdc_amount": 10
    }
    """
    if not CONTRACT_ADDRESS:
        raise HTTPException(
            status_code=503,
            detail="Smart contract not deployed yet. See DEPLOYMENT_GUIDE.md"
        )
    
    if not CONTRACT_ABI:
        raise HTTPException(
            status_code=503,
            detail="Contract ABI not loaded. Deploy contract first."
        )
    
    try:
        # Create contract instance
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        
        # Note: In production, agent would sign transaction themselves
        # For demo, show transaction data
        
        return {
            "prediction_id": 0,  # Would come from event
            "tx_hash": "0x...",  # Would be actual tx hash
            "agent": agent_address,
            "whale_id": request.whale_id,
            "usdc_amount": request.usdc_amount,
            "basescan_link": f"https://sepolia.basescan.org/tx/0x..."
        }
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/predictions/{prediction_id}", response_model=PredictionStatus)
async def get_prediction(prediction_id: int):
    """Get details of a specific prediction"""
    if not CONTRACT_ADDRESS:
        raise HTTPException(status_code=503, detail="Contract not deployed")
    
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        
        # Call contract to get prediction
        pred = contract.functions.getPrediction(prediction_id).call()
        
        return {
            "prediction_id": prediction_id,
            "agent": pred[0],
            "whale_id": pred[1],
            "prediction": pred[2],
            "usdc_staked": pred[3],
            "timestamp": pred[4],
            "settled": pred[5],
            "was_correct": pred[6] if pred[5] else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/leaderboard")
async def get_leaderboard():
    """Get agent leaderboard (placeholder)"""
    return {
        "agents": [
            {
                "agent": "0xBonito",
                "predictions_made": 1,
                "correct": 1,
                "accuracy": "100%",
                "usdc_earned": 20
            }
        ],
        "note": "Leaderboard updates as agents make predictions"
    }

@app.get("/api/contract-info")
async def contract_info():
    """Get smart contract deployment info"""
    return {
        "contract_address": CONTRACT_ADDRESS,
        "network": "Base Sepolia Testnet",
        "usdc_address": USDC_ADDRESS,
        "basescan": f"https://sepolia.basescan.org/address/{CONTRACT_ADDRESS}" if CONTRACT_ADDRESS else None,
        "deployment_guide": "See DEPLOYMENT_GUIDE.md for setup"
    }

# Health check on startup
@app.on_event("startup")
async def startup_event():
    logger.info(f"🐋 Whale Watch Prediction Market API Starting...")
    logger.info(f"Base Sepolia Connected: {w3.is_connected()}")
    logger.info(f"Contract Deployed: {CONTRACT_ADDRESS is not None}")
    if CONTRACT_ADDRESS:
        logger.info(f"Contract Address: {CONTRACT_ADDRESS}")
        logger.info(f"BaseScan: https://sepolia.basescan.org/address/{CONTRACT_ADDRESS}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
