import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Any
from web3 import Web3
from eth_account import Account
import time

class OKXAutoSwapBot:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config['rpc_url']))
        self.account = Account.from_key(config['private_key'])
        self.wallet_address = self.account.address
        self.is_running = False
        self.logs = []
        
        # Token details
        self.token_address = '0x077574441c4f8763a37a2cfee2ecb444aa60a15e'
        self.chain_id = 42161  # Arbitrum One
        
        # API endpoints
        self.base_url = 'https://web3.okx.com/api/v5/dex'
        
        # Setup logging
        self.setup_logging()
        self.log('Bot initialized successfully')
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('swap_logs.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.logs.append(log_entry)
        self.logger.info(message)
        
        # Save logs to file
        self.save_logs()
    
    def save_logs(self):
        """Save logs to file"""
        try:
            with open('swap_logs.txt', 'w') as f:
                f.write('\n'.join(self.logs))
        except Exception as e:
            print(f"Error saving logs: {e}")
    
    async def get_token_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get token price from OKX API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'chainId': self.chain_id,
                    'tokenContractAddress': token_address
                }
                
                async with session.get(f"{self.base_url}/aggregator/tokens", params=params) as response:
                    data = await response.json()
                    
                    if data.get('code') == '0' and data.get('data'):
                        return data['data']
                    
                    raise Exception('Failed to fetch token price')
                    
        except Exception as e:
            self.log(f"Error fetching token price: {str(e)}")
            return None
    
    async def get_swap_quote(self, from_token: str, to_token: str, amount: str) -> Optional[Dict[str, Any]]:
        """Get swap quote from OKX API"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'chainId': self.chain_id,
                    'fromTokenAddress': from_token,
                    'toTokenAddress': to_token,
                    'amount': amount,
                    'slippage': self.config.get('slippage', 0.5),
                    'userWalletAddress': self.wallet_address
                }
                
                async with session.get(f"{self.base_url}/aggregator/quote", params=params) as response:
                    data = await response.json()
                    
                    if data.get('code') == '0' and data.get('data'):
                        return data['data']
                    
                    raise Exception('Failed to get swap quote')
                    
        except Exception as e:
            self.log(f"Error getting swap quote: {str(e)}")
            return None
    
    async def execute_swap(self, swap_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swap transaction"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'chainId': self.chain_id,
                    'fromTokenAddress': swap_data['from_token'],
                    'toTokenAddress': swap_data['to_token'],
                    'amount': swap_data['amount'],
                    'slippage': self.config.get('slippage', 0.5),
                    'userWalletAddress': self.wallet_address,
                    'sort': 1,  # Sort by best price
                    'feePercent': 0
                }
                
                async with session.post(f"{self.base_url}/aggregator/swap", json=payload) as response:
                    data = await response.json()
                    
                    if data.get('code') == '0' and data.get('data'):
                        tx_data = data['data'][0]
                        
                        # Prepare transaction
                        transaction = {
                            'to': tx_data['to'],
                            'data': tx_data['data'],
                            'value': int(tx_data.get('value', '0')),
                            'gas': int(tx_data.get('gasLimit', '500000')),
                            'gasPrice': self.w3.to_wei('1', 'gwei'),
                            'nonce': self.w3.eth.get_transaction_count(self.wallet_address)
                        }
                        
                        # Sign and send transaction
                        signed_txn = self.account.sign_transaction(transaction)
                        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                        
                        self.log(f"Swap executed! TX Hash: {tx_hash.hex()}")
                        
                        # Wait for confirmation
                        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                        self.log(f"Swap confirmed! Block: {receipt.blockNumber}")
                        
                        return {
                            'success': True,
                            'tx_hash': tx_hash.hex(),
                            'receipt': dict(receipt)
                        }
                    
                    raise Exception('Failed to execute swap')
                    
        except Exception as e:
            self.log(f"Error executing swap: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def check_price_conditions(self, current_price: float) -> Optional[Dict[str, str]]:
        """Check if price conditions are met"""
        conditions = self.config['conditions']
        
        # Check buy conditions
        if 'buy_when' in conditions:
            buy_conditions = conditions['buy_when']
            if 'price_below' in buy_conditions and current_price <= buy_conditions['price_below']:
                return {'action': 'buy', 'reason': f'Price below {buy_conditions["price_below"]}'}
        
        # Check sell conditions
        if 'sell_when' in conditions:
            sell_conditions = conditions['sell_when']
            if 'price_above' in sell_conditions and current_price >= sell_conditions['price_above']:
                return {'action': 'sell', 'reason': f'Price above {sell_conditions["price_above"]}'}
        
        return None
    
    async def get_wallet_balance(self, token_address: str) -> str:
        """Get wallet balance for ETH or token"""
        try:
            if token_address == 'ETH' or token_address == '0x0000000000000000000000000000000000000000':
                balance = self.w3.eth.get_balance(self.wallet_address)
                return str(self.w3.from_wei(balance, 'ether'))
            else:
                # Token balance using contract call
                contract_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function"
                    },
                    {
                        "constant": True,
                        "inputs": [],
                        "name": "decimals",
                        "outputs": [{"name": "", "type": "uint8"}],
                        "type": "function"
                    }
                ]
                
                contract = self.w3.eth.contract(address=token_address, abi=contract_abi)
                balance = contract.functions.balanceOf(self.wallet_address).call()
                decimals = contract.functions.decimals().call()
                
                return str(balance / (10 ** decimals))
                
        except Exception as e:
            self.log(f"Error getting wallet balance: {str(e)}")
            return '0'
    
    async def monitor_and_swap(self):
        """Main monitoring loop"""
        self.log('Starting price monitoring...')
        
        while self.is_running:
            try:
                # Get current token price
                token_data = await self.get_token_price(self.token_address)
                
                if not token_data:
                    await asyncio.sleep(self.config.get('check_interval', 30))
                    continue
                
                current_price = float(token_data['price'])
                self.log(f"Current token price: ${current_price}")
                
                # Check if conditions are met
                condition = await self.check_price_conditions(current_price)
                
                if condition:
                    self.log(f"Condition met: {condition['reason']} - Action: {condition['action']}")
                    
                    # Get wallet balances
                    eth_balance = await self.get_wallet_balance('ETH')
                    token_balance = await self.get_wallet_balance(self.token_address)
                    
                    self.log(f"ETH Balance: {eth_balance}, Token Balance: {token_balance}")
                    
                    # Execute swap based on condition
                    if condition['action'] == 'buy':
                        swap_amount = str(int(self.w3.to_wei(self.config['swap_amount'], 'ether')))
                        
                        quote = await self.get_swap_quote(
                            '0x0000000000000000000000000000000000000000',  # ETH
                            self.token_address,
                            swap_amount
                        )
                        
                        if quote:
                            result = await self.execute_swap({
                                'from_token': '0x0000000000000000000000000000000000000000',
                                'to_token': self.token_address,
                                'amount': swap_amount
                            })
                            
                            if result['success']:
                                self.log('Buy order executed successfully!')
                    
                    elif condition['action'] == 'sell':
                        token_balance_wei = int(float(token_balance) * (10 ** 18))
                        swap_amount = str(int(token_balance_wei * self.config.get('sell_percentage', 100) / 100))
                        
                        quote = await self.get_swap_quote(
                            self.token_address,
                            '0x0000000000000000000000000000000000000000',  # ETH
                            swap_amount
                        )
                        
                        if quote:
                            result = await self.execute_swap({
                                'from_token': self.token_address,
                                'to_token': '0x0000000000000000000000000000000000000000',
                                'amount': swap_amount
                            })
                            
                            if result['success']:
                                self.log('Sell order executed successfully!')
                
                # Wait before next check
                await asyncio.sleep(self.config.get('check_interval', 30))
                
            except Exception as e:
                self.log(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(5)
    
    def start(self):
        """Start the bot"""
        if self.is_running:
            self.log('Bot is already running')
            return
        
        self.is_running = True
        self.log('Starting OKX Auto Swap Bot...')
        asyncio.run(self.monitor_and_swap())
    
    def stop(self):
        """Stop the bot"""
        if not self.is_running:
            self.log('Bot is not running')
            return
        
        self.is_running = False
        self.log('Stopping OKX Auto Swap Bot...')
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status"""
        return {
            'is_running': self.is_running,
            'wallet_address': self.wallet_address,
            'token_address': self.token_address,
            'chain_id': self.chain_id,
            'logs_count': len(self.logs)
        }

if __name__ == "__main__":
    # This will be imported from config.py in production
    pass
