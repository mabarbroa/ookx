require('dotenv').config();

const config = {
    // Private key from environment variable
    privateKey: process.env.PRIVATE_KEY || '',
    
    // Arbitrum One RPC URL
    rpcUrl: process.env.RPC_URL || 'https://arb1.arbitrum.io/rpc',
    
    // Token address
    tokenAddress: process.env.TOKEN_ADDRESS || '0x077574441c4f8763a37a2cfee2ecb444aa60a15e',
    
    // Swap conditions
    conditions: {
        buyWhen: {
            priceBelow: parseFloat(process.env.BUY_PRICE_BELOW) || 0.001,
        },
        sellWhen: {
            priceAbove: parseFloat(process.env.SELL_PRICE_ABOVE) || 0.01,
        }
    },
    
    // Swap settings
    swapAmount: parseFloat(process.env.SWAP_AMOUNT_ETH) || 0.01,
    sellPercentage: parseInt(process.env.SELL_PERCENTAGE) || 100,
    slippage: parseFloat(process.env.SLIPPAGE) || 0.5,
    
    // Monitoring settings
    checkInterval: parseInt(process.env.CHECK_INTERVAL) || 30000,
};

// Validation
if (!config.privateKey) {
    console.error('ERROR: PRIVATE_KEY environment variable is required!');
    process.exit(1);
}

module.exports = config;
