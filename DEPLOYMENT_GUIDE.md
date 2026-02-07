# 🚀 Deploy WhalePredictionMarket Contract

Deploy the smart contract to Base Sepolia testnet in **5 minutes**.

---

## ✅ What You Need

- MetaMask wallet (https://metamask.io)
- Base Sepolia testnet configured in MetaMask
- 0.01 Base Sepolia ETH (from faucet - FREE)

---

## 🔧 Step 1: Configure MetaMask for Base Sepolia

1. Open MetaMask
2. Click network selector (top left)
3. Click "Add Network"
4. Enter:
   - Network Name: `Base Sepolia`
   - RPC URL: `https://sepolia.base.org`
   - Chain ID: `84532`
   - Currency: `ETH`
   - Block Explorer: `https://sepolia.basescan.org`
5. Click "Save"

---

## 💰 Step 2: Get Testnet ETH (FREE)

Go to: https://www.alchemy.com/faucets/base-sepolia

1. Connect your MetaMask wallet
2. Click "Send Me ETH"
3. Wait 30 seconds
4. You'll receive ~0.1 Base Sepolia ETH

✅ Now you have ETH for gas fees (completely free!)

---

## 📝 Step 3: Deploy Contract on Remix

**Easy method (no coding required):**

1. Go to: https://remix.ethereum.org

2. Create new file: `WhalePredictionMarket.sol`

3. Copy the contract code from:
   ```
   /home/mourad/clawd/bonito-projects/onchain-intelligence-agent/WhalePredictionMarket.sol
   ```

4. In Remix:
   - Click "Solidity Compiler" (left sidebar)
   - Compiler version: Select `0.8.0` or higher
   - Click "Compile WhalePredictionMarket.sol"

5. Click "Deploy & Run Transactions" (left sidebar)

6. In "Environment" dropdown, select: "Injected Web3"
   - MetaMask will pop up asking to connect
   - Click "Connect"

7. Click "Deploy" button
   - MetaMask pops up with transaction
   - Click "Confirm"

8. ⏳ Wait 30-60 seconds for confirmation

9. 🎉 Contract deployed! You'll see:
   - **Contract Address** (copy this!)
   - View on BaseScan link

---

## ✅ Step 4: Save Contract Address

Copy the contract address and save it:

```
CONTRACT_ADDRESS=0x...  # Your deployed contract address
```

Update the file:
```
/home/mourad/clawd/bonito-projects/onchain-intelligence-agent/.env
```

Add:
```
CONTRACT_ADDRESS=0x...
USDC_TESTNET_ADDRESS=0x036CbD53842c5426634e7929541eC2318f3dCF7e
```

---

## 📊 Step 5: Verify on BaseScan

Go to: `https://sepolia.basescan.org/address/YOUR_CONTRACT_ADDRESS`

You should see:
- Contract code ✅
- Functions (makePrediction, settlePrediction, etc.) ✅
- Transaction history ✅

**Screenshot this for GitHub/Moltbook proof!**

---

## 🔗 Step 6: Update GitHub

1. Add contract address to `README.md`:
   ```
   Smart Contract (Base Sepolia):
   https://sepolia.basescan.org/address/0x...
   ```

2. Commit and push:
   ```bash
   git add .
   git commit -m "Add WhalePredictionMarket smart contract deployment"
   git push
   ```

---

## ✨ You're Done!

The contract is now:
- ✅ Deployed on Base Sepolia testnet
- ✅ Visible on BaseScan
- ✅ Ready for agent predictions
- ✅ Proof of on-chain USDC integration

---

## 🐛 Troubleshooting

**"Insufficient gas"**
- You need more testnet ETH
- Get more from faucet: https://www.alchemy.com/faucets/base-sepolia

**"Network error"**
- Make sure MetaMask is set to Base Sepolia
- Check network switcher shows "Base Sepolia"

**"Contract address not showing"**
- Wait 60+ seconds for confirmation
- Check MetaMask activity tab for status

---

## 📸 Next Steps

Once contract is deployed:
1. Take screenshot of BaseScan showing contract
2. Update Moltbook post with contract address
3. Update GitHub README with deployment proof
4. Ready to make predictions!

---

**Total time: 5-10 minutes** ⚡
