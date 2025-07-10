const OKXAutoSwapBot = require('./OKXAutoSwapBot');
const config = require('./config');

console.log('=== OKX Auto Swap Bot for Arbitrum One ===');
console.log('Token Address:', config.tokenAddress);
console.log('Check Interval:', config.checkInterval, 'ms');
console.log('==========================================');

// Create and start bot
const bot = new OKXAutoSwapBot(config);

// Graceful shutdown handlers
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

process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    bot.stop();
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    bot.stop();
    process.exit(1);
});

// Start the bot
bot.start();
