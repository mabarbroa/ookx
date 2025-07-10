import asyncio
import signal
import sys
from OKXAutoSwapBot import OKXAutoSwapBot
from config import config

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f'\nReceived signal {signum}, stopping bot...')
    if 'bot' in globals():
        bot.stop()
    sys.exit(0)

def main():
    print('=== OKX Auto Swap Bot for Arbitrum One ===')
    print(f'Token Address: {config["token_address"]}')
    print(f'Check Interval: {config["check_interval"]}s')
    print('==========================================')
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start bot
    global bot
    bot = OKXAutoSwapBot(config)
    
    try:
        bot.start()
    except KeyboardInterrupt:
        print('\nKeyboard interrupt received, stopping bot...')
        bot.stop()
    except Exception as e:
        print(f'Error: {str(e)}')
        bot.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
