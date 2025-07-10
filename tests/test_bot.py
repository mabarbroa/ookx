import pytest
import asyncio
from unittest.mock import Mock, patch
from OKXAutoSwapBot import OKXAutoSwapBot

@pytest.fixture
def mock_config():
    return {
        'private_key': '0x' + '1' * 64,  # Mock private key
        'rpc_url': 'https://arb1.arbitrum.io/rpc',
        'conditions': {
            'buy_when': {'price_below': 0.001},
            'sell_when': {'price_above': 0.01}
        },
        'swap_amount': 0.01,
        'sell_percentage': 100,
        'slippage': 0.5,
        'check_interval': 30
    }

@pytest.fixture
def bot(mock_config):
    with patch('OKXAutoSwapBot.Web3'):
        return OKXAutoSwapBot(mock_config)

def test_bot_initialization(bot, mock_config):
    """Test bot initialization"""
    assert bot.config == mock_config
    assert not bot.is_running
    assert bot.chain_id == 42161
    assert bot.token_address == '0x077574441c4f8763a37a2cfee2ecb444aa60a15e'

def test_logging(bot):
    """Test logging functionality"""
    initial_log_count = len(bot.logs)
    bot.log('Test message')
    assert len(bot.logs) == initial_log_count + 1
    assert 'Test message' in bot.logs[-1]

@pytest.mark.asyncio
async def test_check_price_conditions_buy(bot):
    """Test buy condition checking"""
    result = await bot.check_price_conditions(0.0005)
    assert result is not None
    assert result['action'] == 'buy'
    assert 'below' in result['reason']

@pytest.mark.asyncio
async def test_check_price_conditions_sell(bot):
    """Test sell condition checking"""
    result = await bot.check_price_conditions(0.015)
    assert result is not None
    assert result['action'] == 'sell'
    assert 'above' in result['reason']

@pytest.mark.asyncio
async def test_check_price_conditions_no_action(bot):
    """Test no action when conditions not met"""
    result = await bot.check_price_conditions(0.005)
    assert result is None

def test_get_status(bot):
    """Test status retrieval"""
    status = bot.get_status()
    assert 'is_running' in status
    assert 'wallet_address' in status
    assert 'token_address' in status
    assert 'chain_id' in status
    assert 'logs_count' in status
