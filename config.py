import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

config = {
    # Required: Private key from environment variable
    'private_key': os.getenv('PRIVATE_KEY', ''),
    
    # Arbitrum One RPC URL
    'rpc_url': os.getenv('RPC_URL', 'https://arb1.arbitrum.io/rpc'),
    
    # Token address
    'token_address': os.getenv('TOKEN_ADDRESS', '0x077574441c4f8763a37a2cfee2ecb444aa60a15e'),
    
    # Swap conditions
    'conditions': {
        'buy_when': {
            'price_below': float(os.getenv('BUY_PRICE_BELOW', '0.001')),
        },
        'sell_when': {
            'price_above': float(os.getenv('SELL_PRICE_ABOVE', '0.01')),
        }
    },
    
    # Swap settings
    'swap_amount': float(os.getenv('SWAP_AMOUNT_ETH', '0.01')),
    'sell_percentage': int(os.getenv('SELL_PERCENTAGE', '100')),
    'slippage': float(os.getenv('SLIPPAGE', '0.5')),
    
    # Monitoring settings
    'check_interval': int(os.getenv('CHECK_INTERVAL', '30')),
}

# Validation
if not config['private_key']:
    print('ERROR: PRIVATE_KEY environment variable is required!')
    exit(1)
