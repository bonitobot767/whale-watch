// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title WhalePredictionMarket
 * @dev Autonomous agents predict whale movements and compete for USDC rewards
 */
contract WhalePredictionMarket is Ownable {
    
    // USDC token on Base Sepolia
    address public constant USDC = 0x036CbD53842c5426634e7929541eC2318f3dCF7e;
    
    // Prediction structure
    struct Prediction {
        address agent;
        string whaleId;
        string prediction;
        uint256 usdcStaked;
        uint256 timestamp;
        bool settled;
        bool wasCorrect;
    }
    
    // Storage
    uint256 public predictionCount = 0;
    mapping(uint256 => Prediction) public predictions;
    mapping(address => uint256) public agentWinnings;
    
    // Events
    event PredictionMade(
        uint256 indexed predictionId,
        address indexed agent,
        string whaleId,
        uint256 usdcAmount,
        uint256 timestamp
    );
    
    event PredictionSettled(
        uint256 indexed predictionId,
        bool wasCorrect,
        uint256 payout
    );
    
    event RewardClaimed(
        address indexed agent,
        uint256 amount
    );
    
    /**
     * @dev Agent submits a prediction
     * @param whaleId Identifier of the whale movement
     * @param predictionText Description of the prediction
     * @param usdcAmount Amount of USDC to stake
     */
    function makePrediction(
        string memory whaleId,
        string memory predictionText,
        uint256 usdcAmount
    ) public returns (uint256) {
        require(usdcAmount > 0, "Stake must be greater than 0");
        
        // Transfer USDC from agent to contract
        IERC20(USDC).transferFrom(msg.sender, address(this), usdcAmount);
        
        // Create prediction
        uint256 predictionId = predictionCount;
        predictions[predictionId] = Prediction({
            agent: msg.sender,
            whaleId: whaleId,
            prediction: predictionText,
            usdcStaked: usdcAmount,
            timestamp: block.timestamp,
            settled: false,
            wasCorrect: false
        });
        
        predictionCount++;
        
        emit PredictionMade(predictionId, msg.sender, whaleId, usdcAmount, block.timestamp);
        return predictionId;
    }
    
    /**
     * @dev Owner settles a prediction
     * @param predictionId ID of prediction to settle
     * @param wasCorrect Whether the prediction was correct
     */
    function settlePrediction(
        uint256 predictionId,
        bool wasCorrect
    ) public onlyOwner {
        require(predictionId < predictionCount, "Invalid prediction ID");
        Prediction storage pred = predictions[predictionId];
        require(!pred.settled, "Prediction already settled");
        
        pred.settled = true;
        pred.wasCorrect = wasCorrect;
        
        // If correct, double the stake (payout = stake + winnings)
        uint256 payout = 0;
        if (wasCorrect) {
            payout = pred.usdcStaked * 2; // 2x return for correct prediction
            agentWinnings[pred.agent] += payout;
        }
        
        emit PredictionSettled(predictionId, wasCorrect, payout);
    }
    
    /**
     * @dev Agent claims their winnings
     */
    function claimReward() public {
        uint256 amount = agentWinnings[msg.sender];
        require(amount > 0, "No winnings to claim");
        
        agentWinnings[msg.sender] = 0;
        IERC20(USDC).transfer(msg.sender, amount);
        
        emit RewardClaimed(msg.sender, amount);
    }
    
    /**
     * @dev Get prediction details
     */
    function getPrediction(uint256 predictionId) 
        public 
        view 
        returns (
            address agent,
            string memory whaleId,
            string memory predictionText,
            uint256 usdcStaked,
            uint256 timestamp,
            bool settled,
            bool wasCorrect
        ) 
    {
        require(predictionId < predictionCount, "Invalid prediction ID");
        Prediction storage pred = predictions[predictionId];
        return (
            pred.agent,
            pred.whaleId,
            pred.prediction,
            pred.usdcStaked,
            pred.timestamp,
            pred.settled,
            pred.wasCorrect
        );
    }
    
    /**
     * @dev Get agent's current winnings
     */
    function getWinnings(address agent) public view returns (uint256) {
        return agentWinnings[agent];
    }
    
    /**
     * @dev Withdraw stuck USDC (emergency only)
     */
    function withdrawUSDA(uint256 amount) public onlyOwner {
        IERC20(USDC).transfer(owner(), amount);
    }
}
