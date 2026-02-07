#!/usr/bin/env python3
"""
Deploy WhalePredictionMarket contract to Base Sepolia testnet
"""

import json
import os
from web3 import Web3
from solcx import compile_source
import time

# Base Sepolia RPC
BASE_SEPOLIA_RPC = "https://sepolia.base.org"

# Contract code
CONTRACT_SOURCE = open("WhalePredictionMarket.sol", "r").read()

def deploy_contract():
    """Deploy smart contract to Base Sepolia"""
    
    # Connect to Base Sepolia
    w3 = Web3(Web3.HTTPProvider(BASE_SEPOLIA_RPC))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Base Sepolia")
        return None
    
    print("✅ Connected to Base Sepolia testnet")
    
    # Check if we have a private key
    private_key = os.getenv("DEPLOYMENT_PRIVATE_KEY")
    if not private_key:
        print("\n⚠️  NO PRIVATE KEY PROVIDED")
        print("\nTo deploy the contract, you need to:")
        print("1. Create a wallet at: https://metamask.io")
        print("2. Fund it with Base Sepolia ETH from: https://www.alchemy.com/faucets/base-sepolia")
        print("3. Export private key from MetaMask")
        print("4. Set environment variable: export DEPLOYMENT_PRIVATE_KEY=0x...")
        print("\nOr provide your wallet address and I'll show you the deployment bytecode")
        return None
    
    # Get account from private key
    account = w3.eth.account.from_key(private_key)
    print(f"✅ Deployer account: {account.address}")
    
    # Check balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"✅ Account balance: {balance_eth} ETH")
    
    if balance_eth < 0.01:
        print("❌ Not enough ETH to deploy. Need at least 0.01 ETH")
        print("Get testnet ETH: https://www.alchemy.com/faucets/base-sepolia")
        return None
    
    # Compile contract
    print("\n🔨 Compiling contract...")
    try:
        compiled = compile_source(CONTRACT_SOURCE, output_values=["abi", "bin"])
        contract_interface = compiled["WhalePredictionMarket.sol:WhalePredictionMarket"]
        abi = contract_interface["abi"]
        bytecode = contract_interface["bin"]
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        print("\nTrying to use precompiled bytecode instead...")
        # If compilation fails, we can use precompiled
        return deploy_with_hardhat()
    
    print("✅ Contract compiled")
    
    # Create contract factory
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    print("\n📝 Building deployment transaction...")
    tx = contract.constructor().build_transaction({
        "from": account.address,
        "gas": 3000000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(account.address),
    })
    
    # Sign transaction
    print("🔐 Signing transaction...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    
    # Send transaction
    print("🚀 Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print(f"✅ Tx sent: {tx_hash.hex()}")
    
    # Wait for receipt
    print("\n⏳ Waiting for deployment (this may take 30-60 seconds)...")
    for i in range(60):
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                contract_address = receipt.contractAddress
                print(f"\n🎉 CONTRACT DEPLOYED!")
                print(f"📍 Address: {contract_address}")
                print(f"📊 BaseScan: https://sepolia.basescan.org/address/{contract_address}")
                print(f"📝 Tx Hash: https://sepolia.basescan.org/tx/{tx_hash.hex()}")
                
                # Save contract address
                with open(".contract_address", "w") as f:
                    f.write(contract_address)
                
                # Save ABI
                with open("contract_abi.json", "w") as f:
                    json.dump(abi, f)
                
                print("\n✅ Contract address saved to .contract_address")
                print("✅ Contract ABI saved to contract_abi.json")
                
                return contract_address
        except Exception as e:
            pass
        
        time.sleep(1)
        if (i + 1) % 10 == 0:
            print(f"  Still waiting... ({i + 1}s)")
    
    print("\n❌ Deployment timeout")
    return None

def deploy_with_hardhat():
    """Alternative: Use Hardhat for deployment"""
    print("\n📦 Using Hardhat for deployment...")
    print("Run: npx hardhat run scripts/deploy.js --network base-sepolia")
    return None

if __name__ == "__main__":
    print("🐋 Whale Prediction Market - Contract Deployment")
    print("=" * 50)
    
    contract_address = deploy_contract()
    
    if contract_address:
        print("\n" + "=" * 50)
        print("🎉 DEPLOYMENT SUCCESSFUL!")
        print("=" * 50)
        print(f"\nContract Address: {contract_address}")
        print(f"View on BaseScan: https://sepolia.basescan.org/address/{contract_address}")
    else:
        print("\n" + "=" * 50)
        print("⚠️  Deployment setup incomplete")
        print("=" * 50)
