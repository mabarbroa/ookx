const axios = require('axios');
const { ethers } = require('ethers');
const fs = require('fs');
const path = require('path');

class OKXAutoSwapBot {
    constructor(config) {
        this.config = config;
        this.provider = new ethers.providers.JsonRpcProvider(config.rpcUrl);
        this.wallet = new ethers.Wallet(config.privateKey, this.provider);
        this.isRunning = false;
        this.logs = [];
        
        // Token details
        this.tokenAddress = '0x077574441c4f8763a37a2cfee2ecb444aa60a15e';
        this.chainId = 42161; // Arbitrum One
        
        // API endpoints
        this.baseURL = 'https://web3.okx.com/api/v5/dex';
        
        this.log('Bot initialized successfully');
    }

    log(message) {
        const timestamp = new Date().toISOString();
        const logEntry = `[${timestamp}] ${message}`;
        console.log(logEntry);
        this.logs.push(logEntry);
        
        // Save logs to file
        this.saveLogs();
    }

    saveLogs() {
        const logsPath = path.join(__dirname, 'swap_logs.txt');
        fs.writeFileSync(logsPath, this.logs.join('\n'));
    }

    async getTokenPrice(tokenAddress) {
        try {
            const response = await axios.get(`${this.baseURL}/aggregator/tokens`, {
                params: {
                    chainId: this.chainId,
                    tokenContractAddress: tokenAddress
                }
            });
            
            if (response.data.code === '0' && response.data.data) {
                return response.data.data;
            }
            
            throw new Error('Failed to fetch token price');
        } catch (error) {
            this.log(`Error fetching token price: ${error.message}`);
            return null;
        }
    }

    async getSwapQuote(fromToken, toToken, amount) {
        try {
            const response = await axios.get(`${this.baseURL}/aggregator/quote`, {
                params: {
                    chainId: this.chainId,
                    fromTokenAddress: fromToken,
                    toTokenAddress: toToken,
                    amount: amount,
                    slippage: this.config.slippage || 0.5,
                    userWalletAddress: this.wallet.address
                }
            });
            
            if (response.data.code === '0' && response.data.data) {
                return response.data.data;
            }
            
            throw new Error('Failed to get swap quote');
        } catch (error) {
            this.log(`Error getting swap quote: ${error.message}`);
            return null;
        }
    }

    async executeSwap(swapData) {
        try {
            const response = await axios.post(`${this.baseURL}/aggregator/swap`, {
                chainId: this.chainId,
                fromTokenAddress: swapData.fromToken,
                toTokenAddress: swapData.toToken,
                amount: swapData.amount,
                slippage: this.config.slippage || 0.5,
                userWalletAddress: this.wallet.address,
                sort: 1, // Sort by best price
                feePercent: 0
            });
            
            if (response.data.code === '0' && response.data.data) {
                const txData = response.data.data[0];
                
                // Execute the transaction
                const tx = {
                    to: txData.to,
                    data: txData.data,
                    value: txData.value || '0',
                    gasLimit: txData.gasLimit || '500000',
                    gasPrice: ethers.utils.parseUnits('1', 'gwei')
                };
                
                const transaction = await this.wallet.sendTransaction(tx);
                this.log(`Swap executed! TX Hash: ${transaction.hash}`);
                
                // Wait for confirmation
                const receipt = await transaction.wait();
                this.log(`Swap confirmed! Block: ${receipt.blockNumber}`);
                
                return {
                    success: true,
                    txHash: transaction.hash,
                    receipt: receipt
                };
            }
            
            throw new Error('Failed to execute swap');
        } catch (error) {
            this.log(`Error executing swap: ${error.message}`);
            return {
                success: false,
                error: error.message
            };
        }
    }

    async checkPriceConditions(currentPrice) {
        const conditions = this.config.conditions;
        
        // Check buy conditions
        if (conditions.buyWhen) {
            if (conditions.buyWhen.priceBelow && currentPrice <= conditions.buyWhen.priceBelow) {
                return { action: 'buy', reason: `Price below ${conditions.buyWhen.priceBelow}` };
            }
            
            if (conditions.buyWhen.priceIncrease) {
                // Check for price increase percentage
                const increasePercent = conditions.buyWhen.priceIncrease;
                // This would need historical price tracking
            }
        }
        
        // Check sell conditions
        if (conditions.sellWhen) {
            if (conditions.sellWhen.priceAbove && currentPrice >= conditions.sellWhen.priceAbove) {
                return { action: 'sell', reason: `Price above ${conditions.sellWhen.priceAbove}` };
            }
            
            if (conditions.sellWhen.priceDecrease) {
                // Check for price decrease percentage
                const decreasePercent = conditions.sellWhen.priceDecrease;
                // This would need historical price tracking
            }
        }
        
        return null;
    }

    async getWalletBalance(tokenAddress) {
        try {
            if (tokenAddress === 'ETH' || tokenAddress === ethers.constants.AddressZero) {
                const balance = await this.wallet.getBalance();
                return ethers.utils.formatEther(balance);
            } else {
                const tokenContract = new ethers.Contract(
                    tokenAddress,
                    ['function balanceOf(address) view returns (uint256)', 'function decimals() view returns (uint8)'],
                    this.provider
                );
                
                const balance = await tokenContract.balanceOf(this.wallet.address);
                const decimals = await tokenContract.decimals();
                
                return ethers.utils.formatUnits(balance, decimals);
            }
        } catch (error) {
            this.log(`Error getting wallet balance: ${error.message}`);
            return '0';
        }
    }

    async monitorAndSwap() {
        this.log('Starting price monitoring...');
        
        while (this.isRunning) {
            try {
                // Get current token price
                const tokenData = await this.getTokenPrice(this.tokenAddress);
                
                if (!tokenData) {
                    await this.sleep(this.config.checkInterval || 30000);
                    continue;
                }
                
                const currentPrice = parseFloat(tokenData.price);
                this.log(`Current token price: $${currentPrice}`);
                
                // Check if conditions are met
                const condition = await this.checkPriceConditions(currentPrice);
                
                if (condition) {
                    this.log(`Condition met: ${condition.reason} - Action: ${condition.action}`);
                    
                    // Get wallet balances
                    const ethBalance = await this.getWalletBalance('ETH');
                    const tokenBalance = await this.getWalletBalance(this.tokenAddress);
                    
                    this.log(`ETH Balance: ${ethBalance}, Token Balance: ${tokenBalance}`);
                    
                    // Execute swap based on condition
                    if (condition.action === 'buy') {
                        const swapAmount = ethers.utils.parseEther(this.config.swapAmount.toString());
                        
                        const quote = await this.getSwapQuote(
                            ethers.constants.AddressZero, // ETH
                            this.tokenAddress,
                            swapAmount.toString()
                        );
                        
                        if (quote) {
                            const result = await this.executeSwap({
                                fromToken: ethers.constants.AddressZero,
                                toToken: this.tokenAddress,
                                amount: swapAmount.toString()
                            });
                            
                            if (result.success) {
                                this.log(`Buy order executed successfully!`);
                            }
                        }
                    } else if (condition.action === 'sell') {
                        const tokenBalanceWei = ethers.utils.parseUnits(tokenBalance, 18);
                        const swapAmount = tokenBalanceWei.mul(this.config.sellPercentage || 100).div(100);
                        
                        const quote = await this.getSwapQuote(
                            this.tokenAddress,
                            ethers.constants.AddressZero, // ETH
                            swapAmount.toString()
                        );
                        
                        if (quote) {
                            const result = await this.executeSwap({
                                fromToken: this.tokenAddress,
                                toToken: ethers.constants.AddressZero,
                                amount: swapAmount.toString()
                            });
                            
                            if (result.success) {
                                this.log(`Sell order executed successfully!`);
                            }
                        }
                    }
                }
                
                // Wait before next check
                await this.sleep(this.config.checkInterval || 30000);
                
            } catch (error) {
                this.log(`Error in monitoring loop: ${error.message}`);
                await this.sleep(5000);
            }
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    start() {
        if (this.isRunning) {
            this.log('Bot is already running');
            return;
        }
        
        this.isRunning = true;
        this.log('Starting OKX Auto Swap Bot...');
        this.monitorAndSwap();
    }

    stop() {
        if (!this.isRunning) {
            this.log('Bot is not running');
            return;
        }
        
        this.isRunning = false;
        this.log('Stopping OKX Auto Swap Bot...');
    }

    getStatus() {
        return {
            isRunning: this.isRunning,
            walletAddress: this.wallet.address,
            tokenAddress: this.tokenAddress,
            chainId: this.chainId,
            logsCount: this.logs.length
        };
    }
}

// Configuration example
const config = {
    // Required: Your private key (KEEP THIS SECURE!)
    privateKey: 'YOUR_PRIVATE_KEY_HERE',
    
    // Required: Arbitrum One RPC URL
    rpcUrl: 'https://arb1.arbitrum.io/rpc',
    
    // Swap conditions
    conditions: {
        buyWhen: {
            priceBelow: 0.001, // Buy when price drops below this value
            // priceIncrease: 5 // Buy when price increases by this percentage
        },
        sellWhen: {
            priceAbove: 0.01, // Sell when price goes above this value
            // priceDecrease: 10 // Sell when price decreases by this percentage
        }
    },
    
    // Swap settings
    swapAmount: 0.01, // Amount of ETH to swap when buying
    sellPercentage: 100, // Percentage of tokens to sell (100 = all tokens)
    slippage: 0.5, // Slippage tolerance in percentage
    
    // Monitoring settings
    checkInterval: 30000, // Check price every 30 seconds
};

// Usage example
const bot = new OKXAutoSwapBot(config);

// Event handlers
process.on('SIGINT', () => {
    console.log('\nReceived SIGINT, stopping bot...');
    bot.stop();
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\nReceived SIGTERM, stopping bot...');
    bot.stop();
    process.exit(0);
});

// Export for use as module
module.exports = OKXAutoSwapBot;

// If running directly
if (require.main === module) {
    console.log('=== OKX Auto Swap Bot for Arbitrum One ===');
    console.log('Token Address:', config.tokenAddress);
    console.log('Wallet Address:', bot.wallet.address);
    console.log('=========================================');
    
    // Start the bot
    bot.start();
}
